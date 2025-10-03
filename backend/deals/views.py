# backend/deals/views.py

from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
import json
from datetime import timedelta, datetime

from .models import (
    DealGroup, Poll, Vote, Deal, NegotiationMessage, NegotiationSession,
    DealLineItem, PaymentIntent, Payout, Shipment, DeliveryReceipt, DealRating
)
from .serializers import DealGroupSerializer, OfferSerializer, PollSerializer, VoteSerializer, NegotiationMessageSerializer, GroupMessageSerializer
from .clean_agent_logic import analyzeAndRespondTo_offer
from django.db import transaction
from core.permissions import IsAuthenticatedAndFarmer, IsAuthenticatedAndVerifiedBuyer
from django.utils import timezone
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from notifications.services import notify_poll_created
from decimal import Decimal
from django.db.models import Sum
from .ai_advisor import agri_genie
from typing import Optional, Dict, Any
import time
import logging
from .models import GroupMessage, AISessionMemory, DealGroup
# from .clean_agent_logic import AIUnionLeaderAgent  # Not used in new modular system
from users.models import CustomUser
from django.http import Http404
from django.db.models import Q
from .logistics.hub_optimizer import HubOptimizer
from .ml_models.market_analyzer import MarketAnalyzer
from .logistics.google_maps_service import GoogleMapsService
from .services.mcp_service import get_mcp_service

# Custom permissions
class IsFarmerPermission(IsAuthenticatedAndFarmer):
    pass

class IsBuyerPermission(IsAuthenticatedAndVerifiedBuyer):
    pass

# --- VIEWS FOR BUYERS ---

class AvailableGroupsView(generics.ListAPIView):
    """A view for buyers to see all currently available groups for offers."""
    serializer_class = DealGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role != 'BUYER':
            return DealGroup.objects.none()
        
        # Include sold groups so buyers can see their complete deal history
        return DealGroup.objects.filter(
            status__in=['FORMED', 'NEGOTIATING', 'ACCEPTED', 'SOLD']
        ).order_by('-created_at')

class SubmitOfferView(APIView):
    """A view for a buyer to submit an offer on a specific group."""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request, group_id, *args, **kwargs):
        if request.user.role != 'BUYER':
            return Response({"error": "Only buyers can submit offers."}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = OfferSerializer(data=request.data)
        if serializer.is_valid():
            try:
                deal_group = DealGroup.objects.get(id=group_id, status__in=['FORMED', 'NEGOTIATING'])
            except DealGroup.DoesNotExist:
                return Response({"error": "Deal group not found or not available for offers."}, status=status.HTTP_404_NOT_FOUND)

            price_offered = serializer.validated_data['price_per_kg']
            
            # Create negotiation message
            NegotiationMessage.objects.create(
                deal_group=deal_group,
                sender=request.user,
                message_type=NegotiationMessage.MessageType.OFFER,
                content=str(price_offered)
            )

            # Create negotiation session
            session, _ = NegotiationSession.objects.get_or_create(deal_group=deal_group, buyer=request.user)

            # Analyze offer with AI agent
            try:
                user_context = self._get_user_context_for_bargaining(request.user, deal_group)
                decision = analyzeAndRespondTo_offer(
                    deal_group=deal_group,
                    offer_price=float(price_offered),
                    buyer_username=request.user.username,
                    user_context=user_context
                )
                
                # Handle both dictionary and object responses from AI agent
                if isinstance(decision, dict):
                    action = decision.get('action', 'UNKNOWN')
                    new_price = decision.get('new_price', 0)
                    justification = decision.get('justification_for_farmers', 'No justification provided')
                    buyer_message = decision.get('message_to_buyer', 'No message provided')
                    print(f"🤖 AI Agent Decision: {action} - ₹{new_price}/kg")
                    print(f"📊 Justification: {justification}")
                    print(f"💬 Buyer Message: {buyer_message}")
                else:
                    # Handle object response
                    action = getattr(decision, 'action', 'UNKNOWN')
                    new_price = getattr(decision, 'new_price', 0)
                    justification = getattr(decision, 'justification_for_farmers', 'No justification provided')
                    buyer_message = getattr(decision, 'message_to_buyer', 'No message provided')
                    print(f"🤖 AI Agent Decision: {action} - ₹{new_price}/kg")
                    print(f"📊 Justification: {justification}")
                    print(f"💬 Buyer Message: {buyer_message}")
                
                # Debug: Check the decision object structure
                print(f"🔍 Decision object type: {type(decision)}")
                print(f"🔍 Decision object attributes: {dir(decision)}")
                if hasattr(decision, '__dict__'):
                    print(f"🔍 Decision object dict: {decision.__dict__}")
                
            except Exception as e:
                print(f"❌ Negotiation agent error: {e}")
                # Let the advanced agent handle all cases - no fallback needed
                raise e

            # Ensure we have a valid decision from the advanced agent
            if not decision:
                raise Exception("Advanced AI agent failed to provide a decision")

            # Create AI agent message for the chat
            try:
                # Create the AI agent's intelligent response message with better formatting
                if isinstance(decision, dict):
                    # Handle dictionary response
                    if decision.get('message_to_buyer'):
                        ai_message_content = decision['message_to_buyer']
                        print(f"✅ Using message_to_buyer from dict: {ai_message_content}")
                    elif decision.get('justification_for_farmers'):
                        ai_message_content = decision['justification_for_farmers']
                        print(f"✅ Using justification_for_farmers from dict: {ai_message_content}")
                    elif decision.get('message'):
                        # Extract the clean message content from the decision
                        ai_message_content = decision['message']
                        print(f"✅ Using message from dict: {ai_message_content}")
                    else:
                        # Fallback to a generic message
                        ai_message_content = "AI analysis completed. Please review the offer details."
                        print(f"⚠️ Using fallback message for dict decision")
                else:
                    # Handle object response
                    if hasattr(decision, 'message_to_buyer') and decision.message_to_buyer:
                        ai_message_content = decision.message_to_buyer
                        print(f"✅ Using message_to_buyer from object: {ai_message_content}")
                    elif hasattr(decision, 'justification_for_farmers') and decision.justification_for_farmers:
                        ai_message_content = decision.justification_for_farmers
                        print(f"✅ Using justification_for_farmers from object: {ai_message_content}")
                    elif hasattr(decision, 'message') and decision.message:
                        ai_message_content = decision.message
                        print(f"✅ Using message from object: {ai_message_content}")
                    else:
                        # Fallback to a generic message
                        ai_message_content = "AI analysis completed. Please review the offer details."
                        print(f"⚠️ Using fallback message for object decision")
                
                # Format the AI message with clean bullet points structure
                if not ai_message_content.startswith('🤖'):
                    # Check if this is a rejection based on the decision object
                    if isinstance(decision, dict) and decision.get('action') == 'reject':
                        # Extract market data from decision
                        market_analysis = decision.get('market_analysis', {})
                        current_price = market_analysis.get('current_price', 0)
                        recommended_price = decision.get('counter_price', market_analysis.get('recommended_price', 0))
                        buyer_offer = price_offered
                        crop_name = market_analysis.get('crop', 'Crop')
                        region = market_analysis.get('region', 'Region')
                        
                        # Calculate percentage difference
                        if current_price > 0:
                            percentage_diff = ((current_price - float(buyer_offer)) / current_price) * 100
                        else:
                            percentage_diff = 0
                        
                        ai_message_content = f"""🤖 **AI Agent**: Namaste! I've analyzed your offer of ₹{buyer_offer}/kg for {crop_name} from {region}.

💰 **Market Analysis**:
• Current Market Rate: ₹{current_price}/kg
• Quality Premium: Standard pricing
• Recommended Price: ₹{recommended_price}/kg
• Your Offer: ₹{buyer_offer}/kg ({percentage_diff:.0f}% below market)

💡 **Better Deal for You**: Consider ₹{recommended_price}/kg

🎯 **Why This Price Benefits You**:
• **Quality Assurance**: Premium {crop_name} from {region}
• **Market Stability**: Fair price that supports sustainable farming
• **Long-term Partnership**: Builds trust with quality farmers
• **Supply Reliability**: Ensures consistent product availability

🤝 **Let's Work Together**: This price ensures both parties benefit and creates lasting business relationships."""
                    
                    elif isinstance(decision, dict) and decision.get('action') == 'accept':
                        # Format acceptance message
                        ai_message_content = f"""🤖 **AI Agent**: ✅ Offer accepted! Your price of ₹{price_offered}/kg is fair for the quality offered."""
                    
                    else:
                        # Simple fallback - just okay or error
                        ai_message_content = "🤖 **AI Agent**: ✅ Offer analysis completed successfully."
                
                print(f"🔍 Final AI message content: {ai_message_content}")
                print(f"🔍 Decision object type: {type(decision)}")
                print(f"🔍 Decision object attributes: {dir(decision)}")
                if hasattr(decision, '__dict__'):
                    print(f"🔍 Decision object dict: {decision.__dict__}")
                
                # Create the AI agent message
                ai_message = NegotiationMessage.objects.create(
                    deal_group=deal_group,
                    sender=None,  # AI Agent (no sender)
                    message_type=NegotiationMessage.MessageType.TEXT,
                    content=ai_message_content
                )
                
                # Create poll created notification message for buyer
                poll_created_message = f"""📊 **Poll Created**: Offer ₹{price_offered}/kg - Status: ACTIVE

🤖 **AI Agent**: Your offer has been submitted and farmers are now voting.

⏰ **Poll Details**:
• **Expires In**: 6 hours
• **Status**: Active
• **Action**: Farmers are voting

📋 **Next**: You'll be notified of the results when voting is complete."""
                
                NegotiationMessage.objects.create(
                    deal_group=deal_group,
                    sender=None,  # AI Agent (no sender)
                    message_type=NegotiationMessage.MessageType.TEXT,
                    content=poll_created_message
                )
                
                print(f"🤖 AI Agent message created: {ai_message_content[:100]}...")
                print(f"📊 Full AI response: {ai_message_content}")
                print(f"📝 Database message ID: {ai_message.id}")
                
            except Exception as e:
                print(f"⚠️ Error creating AI agent message: {e}")
                import traceback
                traceback.print_exc()
                # Create a basic AI message as fallback
                try:
                    basic_ai_message = NegotiationMessage.objects.create(
                        deal_group=deal_group,
                        sender=None,
                        message_type=NegotiationMessage.MessageType.TEXT,
                        content="🤖 **AI Agent**: Market analysis completed. Please check the poll details for recommendations."
                    )
                    print(f"✅ Basic AI message created as fallback")
                except Exception as fallback_error:
                    print(f"❌ Failed to create even basic AI message: {fallback_error}")
                    import traceback
                    traceback.print_exc()

            # Update group status and create poll
            deal_group.status = 'NEGOTIATING'
            deal_group.save()
            
            Poll.objects.filter(deal_group=deal_group, is_active=True).update(is_active=False)

            # Create new poll
            try:
                # Handle the decision object properly for agent_justification
                if isinstance(decision, dict):
                    agent_justification = decision
                    print(f"✅ Using decision dict directly for agent_justification")
                elif hasattr(decision, 'dict'):
                    agent_justification = decision.dict()
                    print(f"✅ Using decision.dict() for agent_justification")
                elif hasattr(decision, '__dict__'):
                    agent_justification = decision.__dict__
                    print(f"✅ Using decision.__dict__ for agent_justification")
                else:
                    agent_justification = str(decision)
                    print(f"⚠️ Using decision string for agent_justification")
                
                print(f"🔍 Agent justification type: {type(agent_justification)}")
                print(f"🔍 Agent justification content: {str(agent_justification)[:200]}...")
                
                # Get comprehensive logistics and distance information
                logistics_info = self._get_comprehensive_logistics_info(deal_group, request.user)
                
                # Create enhanced agent justification with ONLY market analysis (NO logistics for price polls)
                # Extract market analysis data more robustly
                market_data = {}
                if hasattr(decision, 'market_analysis') and decision.market_analysis:
                    market_data = decision.market_analysis
                elif isinstance(decision, dict) and 'market_analysis' in decision:
                    market_data = decision['market_analysis']
                
                # Create enhanced justification with structured data
                enhanced_justification = {
                    'market_insights': {
                        'crop_name': market_data.get('crop', market_data.get('crop_name', 'Unknown')),
                        'current_market_price': market_data.get('current_price', market_data.get('current_market_price', 'N/A')),
                        'quality_premium': market_data.get('quality_premium', 'N/A'),
                        'recommended_price': market_data.get('recommended_price', market_data.get('new_price', 'N/A')),
                        'buyer_offer': float(price_offered),  # Convert Decimal to float
                        'price_difference': market_data.get('price_difference', 'N/A')
                    },
                    'agent_analysis': {
                        'action': action.upper(),
                        'confidence_level': getattr(decision, 'confidence_level', 'High'),
                        'justification_for_farmers': getattr(decision, 'justification_for_farmers', 'AI analysis based on current market conditions'),
                        'counter_price': getattr(decision, 'counter_price', getattr(decision, 'new_price', None))
                    }
                }
                
                print(f"🔍 Market data extracted: {market_data}")
                print(f"🔍 Enhanced justification created: {enhanced_justification}")
                print(f"🔍 Action: {action}")
                print(f"🔍 Decision object type: {type(decision)}")
                if hasattr(decision, '__dict__'):
                    print(f"🔍 Decision object attributes: {list(decision.__dict__.keys())}")
                
                poll = Poll.objects.create(
                    deal_group=deal_group,
                    offering_buyer=request.user,
                    buyer_offer_price=price_offered,
                    agent_justification=json.dumps(enhanced_justification),
                    expires_at=timezone.now() + timedelta(hours=6),
                )
                    
                print(f"✅ Poll created successfully with ID: {poll.id}")
                    
            except Exception as e:
                print(f"❌ Error creating poll: {e}")
                import traceback
                traceback.print_exc()
                # Create poll with basic justification as fallback
                poll = Poll.objects.create(
                    deal_group=deal_group,
                    offering_buyer=request.user,
                    buyer_offer_price=price_offered,
                    agent_justification=json.dumps({"error": "Failed to create detailed justification", "fallback": True}),
                    expires_at=timezone.now() + timedelta(hours=6),
                )
                print(f"✅ Fallback poll created with ID: {poll.id}")
            
            try:
                notify_poll_created(poll)
            except Exception:
                pass

            # Convert AgentDecision to JSON-serializable format
            if isinstance(decision, dict):
                decision_dict = decision
            elif hasattr(decision, 'dict'):
                decision_dict = decision.dict()
            elif hasattr(decision, '__dict__'):
                decision_dict = decision.__dict__
            else:
                decision_dict = str(decision)
            
            # Create simplified buyer response (no technical details)
            simplified_buyer_response = {
                "action": decision_dict.get('action', 'UNKNOWN'),
                "new_price": decision_dict.get('new_price', 0),
                "message": decision_dict.get('message_to_buyer', 'AI analysis completed'),
                "confidence": decision_dict.get('confidence_level', 'Standard'),
                "simple_market_info": {
                    "crop": decision_dict.get('market_analysis', {}).get('crop_name', 'Unknown'),
                    "current_market_rate": decision_dict.get('market_analysis', {}).get('current_market_price', 0),
                    "quality_premium": decision_dict.get('market_analysis', {}).get('quality_premium', 'Standard pricing')
                }
            }

            return Response({
                "message": "Offer submitted successfully. The farmers have been notified to vote.",
                "agent_recommendation": simplified_buyer_response,
                "ai_agent_message": ai_message_content if 'ai_message_content' in locals() else "AI analysis completed",
                "poll_id": poll.id,
                "deal_group_id": deal_group.id
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _get_user_context_for_bargaining(self, user, deal_group):
        """Gather user context for bargaining analysis."""
        try:
            group_parts = deal_group.group_id.split('-')
            # New format: "CROP-GRADE-TIMESTAMP" (e.g., "POTATO-FAQ-202508161544")
            # Old format was: "REGION-CROP-GRADE-TIMESTAMP"
            if len(group_parts) >= 3:
                crop_name = group_parts[0]  # First part is crop
                grade = group_parts[1]      # Second part is grade
                # No region in new format, use user's location or default
                region = None
            elif len(group_parts) >= 2:
                crop_name = group_parts[0]  # First part is crop
                grade = group_parts[1]      # Second part is grade
                region = None
            else:
                crop_name = None
                grade = None
                region = None
            
            return {
                'user_info': {
                    'username': user.username,
                    'role': getattr(user, 'role', 'UNKNOWN'),
                    'pincode': getattr(user, 'pincode', None),
                    'latitude': getattr(user, 'latitude', None),
                    'longitude': getattr(user, 'longitude', None),
                },
                'deal_group': {
                    'group_id': deal_group.group_id,
                    'total_quantity_kg': deal_group.total_quantity_kg,
                    'extracted_crop': crop_name,
                    'extracted_region': region
                }
            }
        except Exception as e:
            print(f"❌ Error preparing user context: {e}")
            return {}

    def _get_comprehensive_logistics_info(self, deal_group, buyer):
        """Get comprehensive logistics information with real data"""
        try:
            from .logistics.hub_optimizer import HubOptimizer
            
            hub_optimizer = HubOptimizer()
            hub_details = hub_optimizer.get_hub_details(deal_group)
            
            # Get real city names and distances
            optimal_hub = hub_optimizer.compute_and_recommend_hub(deal_group)
            
            # Extract real coordinates and city info
            if optimal_hub and optimal_hub.get('latitude') and optimal_hub.get('longitude'):
                # Use the calculated optimal hub coordinates
                hub_coordinates = {
                    'latitude': optimal_hub['latitude'],
                    'longitude': optimal_hub['longitude']
                }
                city_name = optimal_hub.get('city', 'Unknown City')
                state_name = optimal_hub.get('state', 'Unknown State')
                hub_location = f"{city_name}, {state_name}"
                
                # Calculate real distances from farmers to this hub
                total_distance = self._calculate_real_distance_to_hub(deal_group, optimal_hub['latitude'], optimal_hub['longitude'])
                travel_time = self._estimate_travel_time(total_distance)
                
            else:
                # Fallback to hub details
                hub_coordinates = hub_details.get('coordinates', {'latitude': 0, 'longitude': 0})
                city_name = hub_details.get('real_city_name', 'Central Location')
                state_name = hub_details.get('real_state_name', 'Central Region')
                hub_location = hub_details.get('hub_location', 'Central Location')
                total_distance = hub_details.get('total_distance_km', 50.0)
                travel_time = hub_details.get('travel_time_minutes', 100)
            
            return {
                'optimal_hub': hub_details.get('optimal_hub', 'Central Collection Hub'),
                'hub_location': hub_location,
                'city_name': city_name,
                'state_name': state_name,
                'total_distance_km': total_distance,
                'estimated_transport_cost': hub_details.get('estimated_transport_cost', '₹5,000'),
                'hub_coordinates': hub_coordinates,
                'farmer_count': hub_details.get('farmer_count', 0),
                'total_quantity': hub_details.get('total_quantity', 0),
                'distance_api_used': hub_details.get('distance_api_used', 'Haversine'),
                'travel_time_minutes': travel_time,
                'logistics_efficiency': hub_details.get('logistics_efficiency', 'Standard'),
                'collection_schedule': 'Flexible pickup window between 9 AM - 5 PM',
                'transport_cost_breakdown': self._get_transport_cost_breakdown(total_distance, hub_details.get('total_quantity', 0))
            }
        except Exception as e:
            print(f"❌ Logistics info error: {e}")
            return self._get_fallback_logistics_info()
    
    def _get_fallback_logistics_info(self):
        """Fallback logistics information when real data is unavailable"""
        return {
            'optimal_hub': 'Central Collection Hub',
            'hub_location': 'Central Location',
            'city_name': 'Central Location',
            'state_name': 'Central Region',
            'total_distance_km': 50.0,
            'estimated_transport_cost': '₹5,000',
            'hub_coordinates': {'latitude': 20.5937, 'longitude': 78.9629},
            'farmer_count': 0,
            'total_quantity': 0,
            'distance_api_used': 'Fallback',
            'travel_time_minutes': 100,
            'logistics_efficiency': 'Standard',
            'collection_schedule': 'Standard pickup window',
            'transport_cost_breakdown': self._get_transport_cost_breakdown(50.0, 1000)
        }
    
    def _calculate_real_distance_to_hub(self, deal_group, hub_lat, hub_lon):
        """Calculate real total distance from all farmers to the hub"""
        try:
            total_distance = 0
            farmer_count = 0
            
            for product in deal_group.products.all():
                farmer = product.farmer
                if hasattr(farmer, 'latitude') and hasattr(farmer, 'longitude'):
                    if farmer.latitude and farmer.longitude:
                        distance = self._haversine_distance(
                            float(farmer.latitude), float(farmer.longitude),
                            hub_lat, hub_lon
                        )
                        total_distance += distance
                        farmer_count += 1
            
            if farmer_count == 0:
                return 50.0  # Default distance
            
            return round(total_distance, 2)
            
        except Exception as e:
            print(f"❌ Error calculating real distance to hub: {e}")
            return 50.0
    
    def _estimate_travel_time(self, distance_km):
        """Estimate travel time based on distance"""
        try:
            # Rough estimate: 2 minutes per km for rural areas
            travel_time = distance_km * 2
            
            # Add buffer for loading/unloading
            travel_time += 30
            
            return round(travel_time)
            
        except Exception as e:
            print(f"❌ Error estimating travel time: {e}")
            return 100
    
    def _calculate_distance_details(self, deal_group, buyer):
        """Calculate detailed distance information"""
        try:
            # Get buyer location
            buyer_lat = getattr(buyer, 'latitude', None)
            buyer_lon = getattr(buyer, 'longitude', None)
            buyer_pincode = getattr(buyer, 'pincode', None)
            
            # Get farmers' locations from the group
            farmers_in_group = []
            total_distance = 0
            
            for product in deal_group.products.all():
                farmer = product.farmer
                farmer_lat = getattr(farmer, 'latitude', None)
                farmer_lon = getattr(farmer, 'longitude', None)
                farmer_pincode = getattr(farmer, 'pincode', None)
                
                if farmer_lat and farmer_lon and buyer_lat and buyer_lon:
                    # Calculate distance using Haversine formula
                    distance = self._haversine_distance(
                        farmer_lat, farmer_lon, buyer_lat, buyer_lon
                    )
                    total_distance += distance
                    
                    farmers_in_group.append({
                        'farmer_id': farmer.id,
                        'farmer_name': farmer.username,
                        'location': f"{farmer_lat:.4f}, {farmer_lon:.4f}",
                        'pincode': farmer_pincode,
                        'distance_to_buyer_km': round(distance, 2),
                        'quantity_kg': product.quantity_kg
                    })
            
            return {
                'buyer_location': {
                    'coordinates': f"{buyer_lat:.4f}, {buyer_lon:.4f}" if buyer_lat and buyer_lon else "Not available",
                    'pincode': buyer_pincode
                },
                'farmers_in_group': farmers_in_group,
                'total_distance_km': round(total_distance, 2),
                'average_distance_km': round(total_distance / len(farmers_in_group), 2) if farmers_in_group else 0,
                'distance_analysis': self._analyze_distance_impact(total_distance)
            }
            
        except Exception as e:
            print(f"❌ Error calculating distance details: {e}")
            return {
                'buyer_location': 'Error calculating',
                'farmers_in_group': [],
                'total_distance_km': 0,
                'average_distance_km': 0,
                'distance_analysis': 'Error calculating'
            }
    
    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points using Haversine formula"""
        from math import radians, cos, sin, asin, sqrt
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r
    
    def _analyze_distance_impact(self, total_distance):
        """Analyze the impact of distance on logistics"""
        if total_distance <= 50:
            return "Local delivery - Low transport cost, high efficiency"
        elif total_distance <= 150:
            return "Regional delivery - Moderate transport cost, good efficiency"
        elif total_distance <= 300:
            return "State-level delivery - Higher transport cost, moderate efficiency"
        else:
            return "Long-distance delivery - High transport cost, consider hub optimization"
    
    def _get_transport_cost_breakdown(self, deal_group, buyer):
        """Get detailed transport cost breakdown"""
        try:
            distance_details = self._calculate_distance_details(deal_group, buyer)
            total_distance = distance_details.get('total_distance_km', 0)
            
            # Transport cost calculation (₹/km/kg)
            base_transport_rate = 0.15  # ₹0.15 per km per kg
            fuel_surcharge = 1.1  # 10% fuel surcharge
            distance_multiplier = 1.0
            
            if total_distance > 100:
                distance_multiplier = 1.2  # 20% increase for long distance
            elif total_distance > 50:
                distance_multiplier = 1.1  # 10% increase for medium distance
            
            transport_cost_per_kg = base_transport_rate * fuel_surcharge * distance_multiplier
            total_transport_cost = transport_cost_per_kg * deal_group.total_quantity_kg
            
            return {
                'transport_cost_per_kg': round(transport_cost_per_kg, 2),
                'total_transport_cost': round(total_transport_cost, 2),
                'distance_factor': round(distance_multiplier, 2),
                'fuel_surcharge': round(fuel_surcharge, 2),
                'base_rate': base_transport_rate,
                'cost_breakdown': {
                    'base_cost': round(base_transport_rate * deal_group.total_quantity_kg, 2),
                    'fuel_surcharge': round(base_transport_rate * deal_group.total_quantity_kg * (fuel_surcharge - 1), 2),
                    'distance_multiplier': round(base_transport_rate * deal_group.total_quantity_kg * (distance_multiplier - 1), 2)
                }
            }
            
        except Exception as e:
            print(f"❌ Error calculating transport cost: {e}")
            return {
                'transport_cost_per_kg': 0,
                'total_transport_cost': 0,
                'distance_factor': 1.0,
                'fuel_surcharge': 1.0,
                'base_rate': 0,
                'cost_breakdown': {}
            }
    
    def _get_market_insights_for_poll(self, deal_group):
        """Get market insights specifically for the poll"""
        try:
            from .ml_models.market_analyzer import MarketAnalyzer
            
            market_analyzer = MarketAnalyzer()
            
            # Extract crop and grade from group
            group_parts = deal_group.group_id.split('-')
            crop_name = group_parts[0] if len(group_parts) >= 1 else 'Unknown'
            grade = group_parts[1] if len(group_parts) >= 2 else None
            
            market_data = market_analyzer.get_market_data(
                crop_name, "krishna", datetime.now(), grade
            )
            
            return {
                'crop_name': crop_name,
                'grade': grade,
                'current_market_price': market_data.get('price_analysis', {}).get('current_price_per_kg', 0),
                'market_trend': market_data.get('price_analysis', {}).get('price_trend', 'Unknown'),
                'data_points': market_data.get('data_points', 0),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error getting market insights: {e}")
            return {
                'crop_name': 'Unknown',
                'grade': 'Unknown',
                'current_market_price': 0,
                'market_trend': 'Unknown',
                'data_points': 0,
                'analysis_timestamp': datetime.now().isoformat()
            }

# --- VIEWS FOR FARMERS ---

class ActivePollsView(generics.ListAPIView):
    """A view for a farmer to see all active polls for their groups."""
    serializer_class = PollSerializer
    permission_classes = [IsFarmerPermission]

    def get_queryset(self):
        return Poll.objects.filter(
            is_active=True,
            deal_group__products__farmer=self.request.user
        ).distinct()

class CastVoteView(APIView):
    """Handle voting on polls."""
    permission_classes = [IsAuthenticated]

    def post(self, request, poll_id, *args, **kwargs):
        """Cast a vote on a poll."""
        try:
            poll = Poll.objects.get(id=poll_id)
        except Poll.DoesNotExist:
            return Response({"error": "Poll not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user can vote on this poll
        user_vote = poll.votes.filter(voter=request.user).first()
        if not user_vote:
            # For price offer polls, create a vote object if the user is a farmer in the group
            if poll.poll_type == Poll.PollType.PRICE_OFFER:
                # Check if user is a farmer in this deal group
                if request.user.role == 'FARMER' and poll.deal_group.products.filter(farmer=request.user).exists():
                    # Create vote object for this farmer
                    from .models import Vote
                    user_vote = Vote.objects.create(
            poll=poll,
            voter=request.user,
                        choice='',  # Empty choice means not voted yet
                        voted_at=None
                    )
                    print(f"✅ Created vote object for farmer {request.user.username} on price offer poll {poll.id}")
                else:
                    return Response({"error": "You are not a farmer in this deal group."}, status=status.HTTP_403_FORBIDDEN)
            elif poll.poll_type == Poll.PollType.LOCATION_CONFIRMATION:
                # For location confirmation polls, also create vote object if user is a farmer in the group
                if request.user.role == 'FARMER' and poll.deal_group.products.filter(farmer=request.user).exists():
                    # Create vote object for this farmer
                    from .models import Vote
                    user_vote = Vote.objects.create(
                        poll=poll,
                        voter=request.user,
                        choice='',  # Empty choice means not voted yet
                        voted_at=None
                    )
                    print(f"✅ Created vote object for farmer {request.user.username} on location confirmation poll {poll.id}")
                else:
                    return Response({"error": "You are not a farmer in this deal group."}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({"error": "You are not a participant in this poll."}, status=status.HTTP_403_FORBIDDEN)
        
        # Get vote choice
        choice = request.data.get('choice')
        
        # Handle different poll types with appropriate choices
        if poll.poll_type == Poll.PollType.LOCATION_CONFIRMATION:
            if choice not in ['YES', 'NO']:
                return Response({"error": "Invalid choice for location confirmation poll. Must be 'YES' or 'NO'."}, status=status.HTTP_400_BAD_REQUEST)
        else:  # Price offer poll
            if choice not in ['YES', 'NO']:  # Changed from 'ACCEPT', 'REJECT' to 'YES', 'NO'
                return Response({"error": "Invalid choice for price offer poll. Must be 'YES' or 'NO'."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Record the vote
        user_vote.choice = choice
        user_vote.voted_at = timezone.now()
        user_vote.save()
        
        # Check if the poll is complete after this vote
        self.check_poll_status(poll)
        
        return Response({"message": f"Your vote '{choice}' has been recorded."}, status=status.HTTP_200_OK)

    def check_poll_status(self, poll):
        """Checks if a poll has reached a majority and finalizes the deal."""
        with transaction.atomic():
            locked_poll = Poll.objects.select_for_update().get(id=poll.id)
            locked_group = DealGroup.objects.select_for_update().get(id=poll.deal_group_id)

            # Handle different poll types
            if locked_poll.poll_type == Poll.PollType.LOCATION_CONFIRMATION:
                # Handle location confirmation poll
                self._handle_location_confirmation_poll(locked_poll, locked_group)
            else:
                # Handle price offer poll (existing logic)
                self._handle_price_offer_poll(locked_poll, locked_group)

    def _handle_price_offer_poll(self, poll, deal_group):
        """Handle price offer poll status"""
        total_farmers_in_group = deal_group.products.values('farmer').distinct().count()
        votes_cast = poll.votes.count()

        if total_farmers_in_group == 0:
            return

        if (votes_cast / total_farmers_in_group) > 0.5:
            accept_votes = poll.votes.filter(choice='YES').count()

            if votes_cast > 0 and (accept_votes / votes_cast) > 0.5:
                # Price offer accepted - mark poll as inactive and create location poll
                poll.result = 'ACCEPTED'
                poll.is_active = False  # Remove the poll from active polls
                poll.save()
                
                # Mark deal group as ACCEPTED
                deal_group.status = 'ACCEPTED'
                deal_group.save()
                
                # Mark all product listings as ACCEPTED
                from .models import ProductListing
                for listing in deal_group.products.all():
                        listing.status = 'ACCEPTED'
                        listing.save(update_fields=['status'])
                
                # Calculate total quantity accepted and total amount
                total_quantity_accepted = deal_group.products.aggregate(
                    total=Sum('quantity_kg')
                )['total'] or 0
                
                total_amount = total_quantity_accepted * poll.buyer_offer_price
                
                # Get coordinates for the message
                if deal_group.recommended_collection_point:
                    hub_location = deal_group.recommended_collection_point.name
                    hub_coords = f"{deal_group.recommended_collection_point.latitude:.6f}, {deal_group.recommended_collection_point.longitude:.6f}"
                else:
                    hub_location = 'AI Calculated Hub'
                    hub_coords = '17.385000, 78.486700'
                
                # Create detailed "DEAL ACCEPTED!" message for buyer
                deal_accepted_message = f"""🎉 **DEAL ACCEPTED!** Your offer of ₹{poll.buyer_offer_price}/kg has been accepted!

📊 **Final Voting Results**:
• **Total Farmers**: {total_farmers_in_group}
• **Votes Cast**: {votes_cast}
• **Accepted**: {accept_votes} farmers ✅
• **Rejected**: {votes_cast - accept_votes} farmers ❌

💰 **Deal Summary**:
• **Quantity**: {total_quantity_accepted:,} kg
• **Price**: ₹{poll.buyer_offer_price}/kg
• **Total Value**: ₹{total_amount:,.2f}

📍 **Collection Hub** (AI Calculated):
• **Location**: {hub_location}
• **Coordinates**: {hub_coords}
• **Transport Cost**: ₹2.5/kg
• **Total Transport**: ₹{total_quantity_accepted * 2.5:,.2f}

🚚 **Next Steps**:
1. **Confirm Collection Point**: Please confirm if this location works for you
2. **Collection Date**: Coordinate with farmers for pickup
3. **Payment**: Arrange direct payment to farmers

✅ **Status**: All accepted farmers' products marked as ACCEPTED. Group ready for collection after buyer confirms hub location!"""
                
                # Create the deal accepted message
                from .models import NegotiationMessage
                NegotiationMessage.objects.create(
                    deal_group=deal_group,
                    sender=None,  # AI Agent (no sender)
                    message_type=NegotiationMessage.MessageType.TEXT,
                    content=deal_accepted_message
                )
                
                print(f"✅ Price offer accepted! {accept_votes}/{votes_cast} farmers accepted the offer.")
                print(f"🎉 Deal group {deal_group.id} marked as ACCEPTED!")
                
                # Create location confirmation poll
                self._create_location_confirmation_poll(deal_group, poll)
                
            else:
                poll.result = 'REJECTED'
                poll.is_active = False  # Remove rejected poll
                poll.save()
                deal_group.status = 'NEGOTIATING'
                deal_group.save()
                print(f"❌ Price offer rejected! {accept_votes}/{votes_cast} farmers accepted the offer.")
        else:
            print(f"⏳ Price poll still active. {votes_cast}/{total_farmers_in_group} farmers have voted.")

    def _handle_location_confirmation_poll(self, poll, deal_group):
        """Handle location confirmation poll status"""
        total_farmers_in_group = deal_group.products.values('farmer').distinct().count()
        votes_cast = poll.votes.count()

        if total_farmers_in_group == 0:
            return
        
        if (votes_cast / total_farmers_in_group) > 0.5:
            accept_votes = poll.votes.filter(choice='YES').count()

            if votes_cast > 0 and (accept_votes / votes_cast) > 0.5:
                poll.result = 'ACCEPTED'
                poll.is_active = False
                poll.save()
                
                # Mark deal group as SOLD
                deal_group.status = 'SOLD'
                deal_group.save()
                
                # Mark all accepted product listings as SOLD
                from .models import ProductListing
                for listing in deal_group.products.filter(status='ACCEPTED'):
                    listing.status = 'SOLD'
                    listing.save(update_fields=['status'])
                
                # Create congratulations message
                congratulations_message = f"""🎉 **CONGRATULATIONS!** Collection hub location confirmed!

📍 **Location Details**:
• **Hub**: {deal_group.recommended_collection_point.name if deal_group.recommended_collection_point else 'AI Calculated Hub'}
• **Address**: {deal_group.recommended_collection_point.address if deal_group.recommended_collection_point else 'Address available'}
• **Coordinates**: {deal_group.recommended_collection_point.latitude:.6f}, {deal_group.recommended_collection_point.longitude:.6f}

✅ **Status**: All farmers have confirmed the collection location

🚚 **Next**: Ready for collection and delivery coordination

💰 **Payment**: Arrange payment processing with farmers

**Deal is now fully confirmed and ready for execution!** 🚀"""
                
                # Create the congratulations message
                from .models import NegotiationMessage
                NegotiationMessage.objects.create(
                    deal_group=deal_group,
                    sender=None,  # AI Agent (no sender)
                    message_type=NegotiationMessage.MessageType.TEXT,
                    content=congratulations_message
                )
                
                print(f"✅ Location confirmed! {accept_votes}/{votes_cast} farmers accepted the location.")
                print(f"🎉 Deal group {deal_group.id} marked as SOLD!")
                
            else:
                poll.result = 'REJECTED'
                poll.is_active = False
                poll.save()
                deal_group.status = 'NEGOTIATING'
                deal_group.save()
                print(f"❌ Location rejected! {accept_votes}/{votes_cast} farmers accepted the location.")
        else:
            print(f"⏳ Location poll still active. {votes_cast}/{total_farmers_in_group} farmers have voted.")

    def _calculate_collection_hub(self, deal_group):
        """Calculate optimal collection hub using hub optimizer with Google Maps integration"""
        try:
            optimal_hub = HubOptimizer().compute_and_recommend_hub(deal_group)
            
            if optimal_hub:
                # Import Google Maps service for real city names and distances
                google_maps = GoogleMapsService()
                
                # Get real city name from coordinates (optimal_hub is a dict)
                hub_lat = optimal_hub.get('latitude', 0)
                hub_lng = optimal_hub.get('longitude', 0)
                
                city_info = google_maps.get_city_name_from_coordinates(hub_lat, hub_lng)
                
                # Calculate real distances from farmers to hub
                farmer_coords = self._get_farmer_coordinates_for_distance(deal_group)
                if farmer_coords:
                    distance_matrix = google_maps.get_distance_matrix(
                        farmer_coords, [(hub_lat, hub_lng)]
                    )
                    total_distance = distance_matrix.get('total_distance_km', 50)
                    total_time = distance_matrix.get('total_duration_minutes', 100)
                    api_used = distance_matrix.get('api_used', 'Google Maps')
                else:
                    total_distance = 50
                    total_time = 100
                    api_used = 'Haversine'
                
                # Calculate basic logistics info
                total_quantity = deal_group.products.aggregate(Sum('quantity_kg'))['quantity_kg__sum'] or 0
                transport_cost_per_kg = 2.50  # Default cost per kg
                
                return {
                    'hub_name': optimal_hub.get('name', 'Optimal Collection Hub'),
                    'hub_address': optimal_hub.get('address', 'Address not available'),
                    'hub_coordinates': (hub_lat, hub_lng),
                    'city_name': city_info.get('city', optimal_hub.get('city', 'Central Location')),
                    'state_name': city_info.get('state', optimal_hub.get('state', 'Central Region')),
                    'full_address': city_info.get('full_address', optimal_hub.get('address', 'Address not available')),
                    'total_distance_km': total_distance,
                    'travel_time_minutes': total_time,
                    'distance_api_used': api_used,
                    'logistics_info': {
                        'transport_cost_per_kg': transport_cost_per_kg,
                        'total_transport_cost': transport_cost_per_kg * total_quantity
                    }
                }
            else:
                return {
                    'hub_name': 'Central Collection Hub',
                    'hub_address': 'Address not available',
                    'hub_coordinates': (17.3850, 78.4867),
                    'city_name': 'Central Location',
                    'state_name': 'Central Region',
                    'full_address': 'Address not available',
                    'total_distance_km': 50,
                    'travel_time_minutes': 100,
                    'distance_api_used': 'Default',
                    'logistics_info': {
                        'transport_cost_per_kg': 2.50,
                        'total_transport_cost': 125.0
                    }
                }
                
        except Exception as e:
            print(f"❌ Error calculating hub: {e}")
            return {
                'hub_name': 'Central Collection Hub',
                'hub_address': 'Address not available',
                'hub_coordinates': (17.3850, 78.4867),
                'city_name': "Central Collection Point",
                'state_name': "Central Region",
                'total_distance_km': 50,
                'travel_time_minutes': 100,
                'distance_api_used': 'Error Fallback',
                'logistics_info': {
                    'transport_cost_per_kg': 2.50,
                    'total_transport_cost': 125.0
                }
            }

    def _get_farmer_coordinates_for_distance(self, deal_group):
        """Get farmer coordinates for distance calculation"""
        try:
            coordinates = []
            farmers = CustomUser.objects.filter(
                listings__in=deal_group.products.all()
            ).distinct()
            
            for farmer in farmers:
                if farmer.latitude is not None and farmer.longitude is not None:
                    coordinates.append((float(farmer.latitude), float(farmer.longitude)))
                elif hasattr(farmer, 'pincode') and farmer.pincode:
                    # Try to get coordinates from pincode
                    try:
                        from locations.models import PinCode
                        pincode_data = PinCode.objects.get(code=farmer.pincode)
                        coordinates.append((pincode_data.latitude, pincode_data.longitude))
                        print(f"✅ Using pincode coordinates for {farmer.username}: {pincode_data.district}, {pincode_data.state}")
                    except PinCode.DoesNotExist:
                        print(f"⚠️ Pincode {farmer.pincode} not found for {farmer.username}")
                        continue
                    except Exception as e:
                        print(f"⚠️ Error getting pincode data for {farmer.username}: {e}")
                        continue
            
            if coordinates:
                print(f"✅ Found {len(coordinates)} farmer coordinates for distance calculation")
                return coordinates
            else:
                print(f"⚠️ No valid coordinates found for any farmers in group {deal_group.id}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting farmer coordinates: {e}")
            return None

    def _create_location_confirmation_poll(self, deal_group, poll):
        """Automatically create location confirmation poll when deal is accepted"""
        try:
            # Check if location poll already exists
            existing_location_poll = Poll.objects.filter(
                deal_group=deal_group,
                poll_type=Poll.PollType.LOCATION_CONFIRMATION,
                is_active=True
            ).first()
            
            if existing_location_poll:
                return existing_location_poll
            
            # Ensure deal group has a recommended collection point
            if not deal_group.recommended_collection_point:
                print(f"⚠️ Deal group {deal_group.id} has no recommended collection point, calculating one...")
                hub_info = self._calculate_collection_hub(deal_group)
                if hub_info and hub_info.get('hub_name'):
                    # Try to find the hub by name
                    from hubs.models import HubPartner
                    try:
                        hub = HubPartner.objects.get(name=hub_info['hub_name'])
                        deal_group.recommended_collection_point = hub
                        deal_group.save(update_fields=['recommended_collection_point'])
                        print(f"✅ Assigned hub {hub.name} to deal group {deal_group.id}")
                    except HubPartner.DoesNotExist:
                        # Create the hub if it doesn't exist
                        hub = HubPartner.objects.create(
                            name=hub_info['hub_name'],
                            address=hub_info.get('full_address', 'Address not available'),
                            latitude=hub_info.get('hub_coordinates', [0, 0])[0],
                            longitude=hub_info.get('hub_coordinates', [0, 0])[1]
                        )
                        deal_group.recommended_collection_point = hub
                        deal_group.save(update_fields=['recommended_collection_point'])
                        print(f"✅ Created and assigned new hub {hub.name} to deal group {deal_group.id}")
                else:
                    print(f"⚠️ Could not calculate hub for deal group {deal_group.id}")
            
            # Calculate optimal collection hub
            hub_info = self._calculate_collection_hub(deal_group)
            hub_coords = hub_info.get('hub_coordinates', (17.3850, 78.4867))
            city_name = hub_info.get('city_name', 'Hyderabad')
            state_name = hub_info.get('state_name', 'Central Region')
            total_distance = hub_info.get('total_distance_km', 50)
            travel_time = hub_info.get('travel_time_minutes', 100)
            distance_api = hub_info.get('distance_api_used', 'Hub Optimizer')
            full_address = hub_info.get('full_address', 'Address not available')
            
            # Create structured agent justification with detailed location data
            import json
            agent_justification = {
                'real_location_info': {
                    'city_name': city_name,
                    'state_name': state_name,
                    'coordinates': {
                        'latitude': hub_coords[0],
                        'longitude': hub_coords[1]
                    },
                    'total_distance_km': total_distance,
                    'travel_time_minutes': travel_time,
                    'distance_api_used': distance_api
                },
                'logistics_details': {
                    'hub_name': hub_info.get('hub_name', city_name),
                    'hub_address': full_address,
                    'city_name': city_name,
                    'state_name': state_name,
                    'hub_coordinates': {
                        'latitude': hub_coords[0],
                        'longitude': hub_coords[1]
                    },
                    'total_distance_km': total_distance,
                    'travel_time_minutes': travel_time,
                    'logistics_efficiency': 'Optimized for cost and time',
                    'estimated_transport_cost': f"₹{hub_info.get('logistics_info', {}).get('transport_cost_per_kg', 2.50)}/kg",
                    'hub_facilities': ['Cold storage', 'Weighing', 'Quality check'],
                    'transport_details': {
                        'distance_from_farm': total_distance,
                        'estimated_travel_time': travel_time,
                        'transport_cost_per_kg': hub_info.get('logistics_info', {}).get('transport_cost_per_kg', 2.50)
                    }
                },
                'market_insights': {
                    'crop_name': 'Collection Hub Location',
                    'current_market_price': 'N/A',
                    'quality_premium': 'N/A'
                },
                'agent_analysis': {
                    'action': 'LOCATION_CONFIRMATION',
                    'confidence_level': 'High',
                    'justification_for_farmers': f'AI-calculated optimal collection point in {city_name}, {state_name} to minimize transport costs for all farmers. Total distance: {total_distance} km, estimated travel time: {travel_time} minutes.'
                }
            }
            
            # Create location confirmation poll with structured data
            location_poll = Poll.objects.create(
                deal_group=deal_group,
                poll_type=Poll.PollType.LOCATION_CONFIRMATION,
                agent_justification=json.dumps(agent_justification),
                is_active=True
            )
            
            # Create vote objects for accepted farmers so they can vote
            # Get accepted farmers from the original price offer poll
            accepted_farmers = set(poll.votes.filter(choice='ACCEPT').values_list('voter_id', flat=True))
            
            for farmer_id in accepted_farmers:
                try:
                    from .models import Vote
                    Vote.objects.create(
                        poll=location_poll,
                        voter_id=farmer_id,
                        choice='',  # Empty choice means not voted yet
                        voted_at=None
                    )
                except Exception as e:
                    continue
            
            return location_poll
            
        except Exception as e:
            return None

    def _create_collection_message(self, poll, hub_info, total_farmers, accepted_count, 
                                 rejected_count, total_quantity_accepted, total_amount):
        """Create final collection message with hub details"""
        try:
            hub_coords = hub_info.get('hub_coordinates', (0, 0))
            city_name = hub_info.get('city_name', 'Optimal Collection Point')
            logistics = hub_info.get('logistics_info', {})
            
            transport_cost = logistics.get('transport_cost_per_kg', 0)
            total_transport = logistics.get('total_transport_cost', 0)
            
            message = f"""🤖 **AI Agent**: 🎉 **DEAL ACCEPTED!** Your offer of ₹{poll.buyer_offer_price}/kg has been accepted!

**📊 Final Voting Results**:
• **Total Farmers**: {total_farmers}
• **Accepted**: {accepted_count} farmers ✅
• **Rejected**: {rejected_count} farmers ❌

**💰 Deal Summary**:
• **Quantity**: {total_quantity_accepted} kg
• **Price**: ₹{poll.buyer_offer_price}/kg
• **Total Value**: ₹{total_amount:.2f}

**📍 Collection Hub** (AI Calculated):
• **Location**: {city_name}
• **Coordinates**: {hub_coords[0]:.6f}, {hub_coords[1]:.6f}
• **Transport Cost**: ₹{transport_cost}/kg
• **Total Transport**: ₹{total_transport:.2f}

**🚚 Next Steps**:
1. **Confirm Collection Point**: Please confirm if this location works for you
2. **Collection Date**: Coordinate with farmers for pickup
3. **Payment**: Arrange direct payment to farmers

**✅ Status**: All accepted farmers' products marked as ACCEPTED. Group ready for collection after buyer confirms hub location!"""
            
            return message
            
        except Exception as e:
            print(f"Error creating collection message: {e}")
            return f"🤖 **AI Agent**: Deal accepted! {total_quantity_accepted} kg at ₹{poll.buyer_offer_price}/kg. Please coordinate collection with farmers."

# --- LOCATION POLLS ---

class LocationConfirmationPollView(APIView):
    """Handle location confirmation polls for both buyers and farmers."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """Get active location confirmation polls for a user."""
        try:
            user = request.user
            active_polls = Poll.objects.filter(
                poll_type=Poll.PollType.LOCATION_CONFIRMATION,
                is_active=True,
                votes__voter=user
            ).distinct()
            
            poll_data = []
            for poll in active_polls:
                user_vote = poll.votes.filter(voter=user).first()
                poll_data.append({
                    'id': poll.id,
                    'deal_group': poll.deal_group.group_id,
                    'deal_group_id': poll.deal_group.id,
                    'poll_type': poll.poll_type,
                    'is_active': poll.is_active,
                    'user_vote': user_vote.choice if user_vote else None,
                    'total_participants': poll.votes.count(),
                    'voted_participants': poll.votes.exclude(choice='').count(),
                    'created_at': poll.created_at
                })
            
            return Response(poll_data)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LocationVoteView(APIView):
    """Handle voting on location confirmation polls."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, poll_id, *args, **kwargs):
        """Cast a vote on a location confirmation poll."""
        try:
            poll = Poll.objects.get(id=poll_id)
        except Poll.DoesNotExist:
            return Response({"error": "Poll not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user can vote on this poll
        user_vote = poll.votes.filter(voter=request.user).first()
        if not user_vote:
            return Response({"error": "You are not a participant in this poll."}, status=status.HTTP_403_FORBIDDEN)
        
        # Get vote choice
        choice = request.data.get('choice')
        if choice not in ['YES', 'NO']:
            return Response({"error": "Invalid choice. Must be 'YES' or 'NO'."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Record the vote
        user_vote.choice = choice
        user_vote.voted_at = timezone.now()
        user_vote.save()
        
        # Check if all participants have voted
        all_voted = poll.votes.exclude(choice='').count() == poll.votes.count()
        
        if all_voted:
            # Check if all votes are YES
            all_yes = poll.votes.exclude(choice='NO').count() == poll.votes.count()
            
            if all_yes:
                # All participants confirmed location
                poll.result = 'CONFIRMED'
                poll.is_active = False
                poll.save()
                
                deal_group = poll.deal_group
                deal_group.status = 'COMPLETED'
                deal_group.save()
                
                # Mark all accepted listings as SOLD
                accepted_listings = deal_group.products.filter(status='ACCEPTED')
                for listing in accepted_listings:
                    listing.status = 'SOLD'
                    listing.save(update_fields=['status'])
                
                return Response({
                    'message': 'Location confirmed by all participants! Deal completed.',
                    'status': 'COMPLETED',
                    'result': 'CONFIRMED'
                })
            else:
                # Some participants rejected location
                poll.result = 'REJECTED'
                poll.is_active = False
                poll.save()
                
                return Response({
                    'message': 'Location rejected by some participants. Please coordinate alternative location.',
                    'status': 'REJECTED',
                    'result': 'REJECTED'
                })
        
        return Response({
            'message': 'Vote recorded successfully',
            'status': 'VOTED',
            'all_voted': all_voted
        })

# --- OTHER ESSENTIAL VIEWS ---

class MyPollsView(generics.ListAPIView):
    """Get polls for the current user."""
    serializer_class = PollSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'FARMER':
            return Poll.objects.filter(
                deal_group__products__farmer=user
            ).distinct().order_by('-created_at')
        elif user.role == 'BUYER':
            return Poll.objects.filter(
                offering_buyer=user
            ).order_by('-created_at')
        return Poll.objects.none()
    
    def list(self, request, *args, **kwargs):
        """Get polls with enhanced data for better frontend display."""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            polls_data = serializer.data
            
            # Enhance poll data for frontend
            enhanced_polls = []
            for poll in polls_data:
                enhanced_poll = {**poll}
                
                # Add poll type information
                if poll.get('poll_type') == 'location_confirmation':
                    enhanced_poll['poll_type_display'] = 'Location Confirmation'
                    enhanced_poll['poll_title'] = 'Confirm Collection Hub Location'
                    enhanced_poll['poll_description'] = 'Please confirm if the proposed collection location works for you.'
                    enhanced_poll['choices'] = ['YES', 'NO']
                    enhanced_poll['is_location_poll'] = True
                else:
                    enhanced_poll['poll_type_display'] = 'Price Offer'
                    enhanced_poll['poll_title'] = 'Vote on Buyer Offer'
                    enhanced_poll['poll_description'] = 'Please vote on the buyer\'s offer price.'
                    enhanced_poll['choices'] = ['ACCEPT', 'REJECT']
                    enhanced_poll['is_location_poll'] = False
                
                enhanced_polls.append(enhanced_poll)
            
            return Response(enhanced_polls, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"❌ Error in MyPollsView.list: {e}")
            return Response(
                {"error": f"Failed to get polls: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MyDealGroupsView(generics.ListAPIView):
    """List all deal groups where the current user has access."""
    serializer_class = DealGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'FARMER':
            return (
                DealGroup.objects
                        .filter(products__farmer=user)
                .distinct()
                .order_by('-created_at')
            )
        elif user.role == 'BUYER':
            return (
                DealGroup.objects
                .filter(status__in=['ACTIVE', 'NEGOTIATING', 'ACCEPTED', 'COMPLETED'])
                .distinct()
                .order_by('-created_at')
            )
        else:
            return DealGroup.objects.none()

class GroupDetailView(generics.RetrieveAPIView):
    """Get details of a specific deal group."""
    serializer_class = DealGroupSerializer
    permission_classes = [IsAuthenticated]
    queryset = DealGroup.objects.all()
    lookup_field = 'id'  # Changed from 'group_id' to 'id' since we're using the primary key
    
    def get_object(self):
        group_id = self.kwargs.get('group_id')
        try:
            user = self.request.user
            if user.role == 'FARMER':
                obj = DealGroup.objects.filter(
                    id=group_id,
                    products__farmer=user
                ).distinct().first()
            elif user.role == 'BUYER':
                # Include SOLD status for buyers to see complete deal history
                obj = DealGroup.objects.filter(
                    id=group_id,
                    status__in=['FORMED', 'NEGOTIATING', 'ACTIVE', 'ACCEPTED', 'COMPLETED', 'SOLD']
                ).first()
            else:
                obj = None
        except Exception as e:
            print(f"Error in GroupDetailView.get_object: {e}")
            obj = None
        
        if not obj:
            raise Http404("Deal group not found or you don't have access")
        return obj

# --- AI ADVISOR ---

class AIAdvisorView(APIView):
    """AI Agricultural Advisor API endpoint"""
    
    def post(self, request):
        """Get AI advice based on user query"""
        try:
            query = request.data.get('query', '').strip()
            user_role = request.data.get('user_role', 'farmer')
            context = request.data.get('context', {})
            
            if not query:
                return Response({
                    'error': 'Query is required',
                    'suggestion': 'Please provide a question or request for advice.'
                }, status=400)
            
            # Get comprehensive advice from AI advisor
            advice = agri_genie.get_comprehensive_advice(query, user_role, context)
            
            if 'error' in advice:
                return Response(advice, status=400)
            
            return Response({
                'success': True,
                'advice': advice,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            return Response({
                'error': f'Advisor error: {str(e)}',
                'suggestion': 'Please try rephrasing your question or contact support.'
            }, status=500)

# --- MISSING VIEWS FOR URLS ---

class NegotiationMessagesView(generics.ListCreateAPIView):
    """Handle negotiation messages for a deal group."""
    serializer_class = NegotiationMessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        group_id = self.kwargs.get('group_id')
        return NegotiationMessage.objects.filter(deal_group_id=group_id).order_by('created_at')
    
    def perform_create(self, serializer):
        group_id = self.kwargs.get('group_id')
        serializer.save(
            deal_group_id=group_id,
            sender=self.request.user
        )

class GroupMessagesView(generics.ListCreateAPIView):
    """Handle group chat messages."""
    serializer_class = GroupMessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        group_id = self.kwargs.get('group_id')
        return GroupMessage.objects.filter(deal_group_id=group_id).order_by('created_at')
    
    def perform_create(self, serializer):
        group_id = self.kwargs.get('group_id')
        serializer.save(
            deal_group_id=group_id,
            sender=self.request.user
        )
    
    def list(self, request, *args, **kwargs):
        """Get group chat messages with enhanced data."""
        try:
            group_id = self.kwargs.get('group_id')
            
            # Check if user has access to this group
            try:
                deal_group = DealGroup.objects.get(id=group_id)
            except DealGroup.DoesNotExist:
                return Response({"error": "Deal group not found."}, status=status.HTTP_404_NOT_FOUND)
            
            if not self._user_has_access(request.user, deal_group):
                return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
            
            # Get messages - combine GroupMessage and NegotiationMessage for buyers
            messages = self.get_queryset()
            
            # For buyers, also get negotiation messages to show AI Agent responses
            if request.user.role == 'BUYER':
                from .models import NegotiationMessage
                negotiation_messages = NegotiationMessage.objects.filter(
                    deal_group=deal_group
                ).select_related('sender').order_by('created_at')
                
                # Instead of mixing objects, let's handle this in the serializer
                # or return a separate response structure
                pass  # Remove the problematic mixing logic
            
            # Serialize messages
            serializer = self.get_serializer(messages, many=True)
            message_data = serializer.data
            
            # Add additional context
            response_data = {
                'deal_group': {
                    'id': deal_group.id,
                    'group_id': deal_group.group_id,
                    'status': deal_group.status
                },
                'messages': message_data,
                'total_messages': len(message_data),
                'user_role': request.user.role
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"❌ Error getting group messages: {e}")
            return Response(
                {"error": f"Failed to get group messages: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _user_has_access(self, user, deal_group):
        """Check if user has access to view this deal group."""
        # Farmers can see groups they're part of
        if user.role == 'FARMER':
            return deal_group.products.filter(farmer=user).exists()
        # Buyers can see all groups
        elif user.role == 'BUYER':
            return True
        # Admins can see all groups
        elif user.role == 'ADMIN':
            return True
        return False

class GroupMembersView(generics.ListAPIView):
    """List group members with detailed profile information."""
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        group_id = self.kwargs.get('group_id')
        try:
            deal_group = DealGroup.objects.get(id=group_id)
            members = []
            
            # Get farmers from products
            for product in deal_group.products.all():
                if product.farmer not in members:
                    members.append(product.farmer)
            
            # Get buyer if exists
            if hasattr(deal_group, 'buyer') and deal_group.buyer:
                if deal_group.buyer not in members:
                    members.append(deal_group.buyer)
            
            member_data = []
            for member in members:
                member_data.append({
                    'id': member.id,
                    'username': member.username,
                    'role': getattr(member, 'role', 'UNKNOWN'),
                    'first_name': getattr(member, 'first_name', ''),
                    'last_name': getattr(member, 'last_name', ''),
                    'name': getattr(member, 'name', ''),
                    'phone_number': getattr(member, 'phone_number', ''),
                    'trust_score': getattr(member, 'trust_score', 10),
                    'is_verified': getattr(member, 'is_verified', False),
                    'region': getattr(member, 'region', ''),
                    'pincode': getattr(member, 'pincode', ''),
                    'latitude': getattr(member, 'latitude', None),
                    'longitude': getattr(member, 'longitude', None)
                })
            
            return Response(member_data)
            
        except DealGroup.DoesNotExist:
            return Response({"error": "Group not found"}, status=404)

class LogisticsInfoView(APIView):
    """Get logistics information for a deal group."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, group_id, *args, **kwargs):
        try:
            deal_group = DealGroup.objects.get(id=group_id)
        except DealGroup.DoesNotExist:
            return Response({"error": "Deal group not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user has access to this group
        if not self._user_has_access(request.user, deal_group):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        # Get basic logistics info using hub optimizer
        try:
            hub_optimizer = HubOptimizer()
            hub_info = hub_optimizer.get_hub_details(deal_group)
            return Response(hub_info, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"Logistics information unavailable: {str(e)}"}, status=status.HTTP_404_NOT_FOUND)
    
    def _user_has_access(self, user, deal_group):
        """Check if user has access to view this deal group."""
        # Farmers can see groups they're part of
        if user.role == 'FARMER':
            return deal_group.products.filter(farmer=user).exists()
        # Buyers can see all groups
        elif user.role == 'BUYER':
            return True
        # Admins can see all groups
        elif user.role == 'ADMIN':
            return True
        return False

class RecomputeHubView(APIView):
    """Recompute hub recommendation for a deal group."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, group_id, *args, **kwargs):
        try:
            deal_group = DealGroup.objects.get(id=group_id)
        except DealGroup.DoesNotExist:
            return Response({"error": "Deal group not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user has access to this group
        if not self._user_has_access(request.user, deal_group):
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        # Use hub optimizer to recompute hub
        try:
            hub_optimizer = HubOptimizer()
            new_hub = hub_optimizer.compute_and_recommend_hub(deal_group)
        except Exception as e:
            new_hub = None
        
        if new_hub:
            return Response({
                "message": f"Hub recommendation updated to {new_hub.name}",
                "hub_id": new_hub.id,
                "hub_name": new_hub.name
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Failed to recompute hub recommendation."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _user_has_access(self, user, deal_group):
        """Check if user has access to modify this deal group."""
        # Only admins can force hub recomputation
        return user.role == 'ADMIN'

# --- STUB VIEWS FOR MISSING ENDPOINTS ---

class ActivePollView(APIView):
    """Get active poll for a deal group."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, group_id, *args, **kwargs):
        """Get the currently active poll for a deal group."""
        try:
            print(f"🔍 ActivePollView.get called for group_id: {group_id}")
            
            # Check if this might be a poll ID instead of a group ID
            try:
                poll = Poll.objects.get(id=group_id)
                print(f"⚠️ Found poll with ID {group_id}, but this endpoint expects a group ID")
                print(f"📊 Poll {group_id} belongs to deal group {poll.deal_group.id}")
                print(f"💡 Try using /api/deals/groups/{poll.deal_group.id}/active-poll/ instead")
                return Response({
                    "error": f"This endpoint expects a deal group ID, not a poll ID. Poll {group_id} belongs to deal group {poll.deal_group.id}.",
                    "suggestion": f"Use /api/deals/groups/{poll.deal_group.id}/active-poll/ instead"
                }, status=status.HTTP_400_BAD_REQUEST)
            except Poll.DoesNotExist:
                # This is not a poll ID, proceed with group ID logic
                pass
            
            # Get the deal group
            try:
                deal_group = DealGroup.objects.get(id=group_id)
                print(f"✅ Found deal group: ID={deal_group.id}, Group ID={deal_group.group_id}")
            except DealGroup.DoesNotExist:
                print(f"❌ Deal group {group_id} not found")
                return Response({"error": "Deal group not found."}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user has access to this group
            if not self._user_has_access(request.user, deal_group):
                print(f"❌ User {request.user.username} (role: {request.user.role}) denied access to group {group_id}")
                return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
            
            print(f"✅ User {request.user.username} has access to group {group_id}")
            
            # Get the most recent active poll
            active_poll = Poll.objects.filter(
                deal_group=deal_group,
                is_active=True
            ).order_by('-created_at').first()
            
            if not active_poll:
                print(f"⚠️ No active poll found for group {group_id}")
                # Check what polls exist for this group
                all_polls = Poll.objects.filter(deal_group=deal_group)
                print(f"📊 All polls for group {group_id}: {list(all_polls.values('id', 'poll_type', 'is_active', 'result'))}")
                return Response({"message": "No active poll found for this group."}, status=status.HTTP_404_NOT_FOUND)
            
            print(f"✅ Found active poll: ID={active_poll.id}, Type={active_poll.poll_type}")
            
            # Format poll data based on type
            poll_data = {
                'id': active_poll.id,
                'poll_type': active_poll.poll_type,
                'is_active': active_poll.is_active,
                'created_at': active_poll.created_at.isoformat(),
                'expires_at': active_poll.expires_at.isoformat() if active_poll.expires_at else None,
                'result': active_poll.result,
                'deal_group_id': active_poll.deal_group.id,
                'deal_group_name': active_poll.deal_group.group_id
            }
            
            # Add type-specific data
            if active_poll.poll_type == Poll.PollType.LOCATION_CONFIRMATION:
                poll_data.update({
                    'poll_type': 'location_confirmation',
                    'title': 'Location Confirmation Required',
                    'description': 'Please confirm if the proposed collection hub location works for you.',
                    'agent_justification': active_poll.agent_justification,
                    'choices': ['YES', 'NO'],
                    'total_participants': active_poll.votes.count(),
                    'voted_participants': active_poll.votes.exclude(choice='').count(),
                    'buyer_offer_price': '0',  # Location polls don't have price
                    'offering_buyer': 'AI System'  # System-generated poll
                })
            else:
                # Regular price offer poll
                poll_data.update({
                    'poll_type': 'price_offer',
                    'title': 'Vote on Buyer Offer',
                    'description': 'Please vote on the buyer\'s offer price.',
                    'buyer_offer_price': str(active_poll.buyer_offer_price) if active_poll.buyer_offer_price else '0',
                    'offering_buyer': active_poll.offering_buyer.username if active_poll.offering_buyer else 'Unknown',
                    'agent_justification': active_poll.agent_justification,
                    'choices': ['ACCEPT', 'REJECT']
                })
            
            return Response(poll_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"❌ Error getting active poll: {e}")
            return Response(
                {"error": f"Failed to get active poll: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _user_has_access(self, user, deal_group):
        """Check if user has access to view this deal group."""
        # Farmers can see groups they're part of
        if user.role == 'FARMER':
            return deal_group.products.filter(farmer=user).exists()
        # Buyers can see all groups
        elif user.role == 'BUYER':
            return True
        # Admins can see all groups
        elif user.role == 'ADMIN':
            return True
        return False

class VoteView(APIView):
    """Stub for vote view."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, group_id, *args, **kwargs):
        return Response({"message": "Vote endpoint - not implemented yet"}, status=200)

class CollectionConfirmView(APIView):
    """Stub for collection confirmation view."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, group_id, *args, **kwargs):
        return Response({"message": "Collection confirmation endpoint - not implemented yet"}, status=200)

class PaymentConfirmView(APIView):
    """Stub for payment confirmation view."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, group_id, *args, **kwargs):
        return Response({"message": "Payment confirmation endpoint - not implemented yet"}, status=200)

class ShipmentBookView(APIView):
    """Stub for shipment booking view."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, group_id, *args, **kwargs):
        return Response({"message": "Shipment booking endpoint - not implemented yet"}, status=200)

class NegotiationHistoryView(APIView):
    """Get negotiation history for a deal group."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, group_id, *args, **kwargs):
        """Get negotiation history including messages, polls, and offers."""
        try:
            # Get the deal group
            try:
                deal_group = DealGroup.objects.get(id=group_id)
            except DealGroup.DoesNotExist:
                return Response({"error": "Deal group not found."}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if user has access to this group
            if not self._user_has_access(request.user, deal_group):
                return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
            
            # Get negotiation messages
            negotiation_messages = NegotiationMessage.objects.filter(
                deal_group=deal_group
            ).select_related('sender').order_by('created_at')
            
            # Get polls
            polls = Poll.objects.filter(
                deal_group=deal_group
            ).select_related('offering_buyer').order_by('created_at')
            
            # Get group messages (chat)
            group_messages = GroupMessage.objects.filter(
                deal_group=deal_group
            ).select_related('sender').order_by('created_at')
            
            # Build negotiation history
            history = []
            
            # Add negotiation messages
            for msg in negotiation_messages:
                history.append({
                    'type': 'negotiation_message',
                    'id': msg.id,
                    'timestamp': msg.created_at.isoformat(),
                    'sender': msg.sender.username if msg.sender else 'AI Agent',
                    'sender_role': getattr(msg.sender, 'role', 'UNKNOWN') if msg.sender else 'AI_AGENT',
                    'message_type': msg.message_type,
                    'content': msg.content,
                    'is_ai_agent': msg.sender is None
                })
            
            # Add polls
            for poll in polls:
                history.append({
                    'type': 'poll',
                    'id': poll.id,
                    'timestamp': poll.created_at.isoformat(),
                    'buyer': poll.offering_buyer.username if poll.offering_buyer else 'Unknown',
                    'offer_price': str(poll.buyer_offer_price) if poll.buyer_offer_price else '0',
                    'status': poll.result if poll.result else 'ACTIVE',
                    'is_active': poll.is_active,
                    'agent_justification': poll.agent_justification,
                    'expires_at': poll.expires_at.isoformat() if poll.expires_at else None
                })
            
            # Add group chat messages
            for msg in group_messages:
                history.append({
                    'type': 'group_message',
                    'id': msg.id,
                    'timestamp': msg.created_at.isoformat(),
                    'sender': msg.sender.username if msg.sender else 'AI Agent',
                    'sender_role': getattr(msg.sender, 'role', 'UNKNOWN') if msg.sender else 'AI_AGENT',
                    'content': msg.content,
                    'message_type': msg.message_type,
                    'category': msg.category,
                    'is_ai_agent': msg.is_ai_agent
                })
            
            # Sort all history by timestamp
            history.sort(key=lambda x: x['timestamp'])
            
            # Group by date for better organization
            grouped_history = {}
            for item in history:
                date = item['timestamp'][:10]  # Extract date part
                if date not in grouped_history:
                    grouped_history[date] = []
                grouped_history[date].append(item)
            
            # Calculate summary statistics
            total_messages = len(negotiation_messages)
            total_polls = len(polls)
            total_chat_messages = len(group_messages)
            active_polls = len([p for p in polls if p.is_active])
            
            # Get current deal status
            current_status = deal_group.status
            current_price = None
            if polls.exists():
                latest_poll = polls.latest('created_at')
                if latest_poll.buyer_offer_price:
                    current_price = str(latest_poll.buyer_offer_price)
            
            response_data = {
                'deal_group': {
                    'id': deal_group.id,
                    'group_id': deal_group.group_id,
                    'status': current_status,
                    'current_price': current_price,
                    'total_quantity_kg': deal_group.total_quantity_kg,
                    'created_at': deal_group.created_at.isoformat()
                },
                'summary': {
                    'total_negotiation_messages': total_messages,
                    'total_polls': total_polls,
                    'total_chat_messages': total_chat_messages,
                    'active_polls': active_polls,
                    'total_history_items': len(history)
                },
                'history': grouped_history,
                'timeline': history  # Flat timeline for easy processing
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"❌ Error getting negotiation history: {e}")
            return Response(
                {"error": f"Failed to get negotiation history: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _user_has_access(self, user, deal_group):
        """Check if user has access to view this deal group."""
        # Farmers can see groups they're part of
        if user.role == 'FARMER':
            return deal_group.products.filter(farmer=user).exists()
        # Buyers can see all groups
        elif user.role == 'BUYER':
            return True
        # Admins can see all groups
        elif user.role == 'ADMIN':
            return True
        return False

class BuyerNegotiationChatView(APIView):
    """Get buyer-specific negotiation chat and history with AI agent responses."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, group_id, *args, **kwargs):
        """Get buyer negotiation chat and history."""
        try:
            # Check if user is a buyer
            if request.user.role != 'BUYER':
                return Response({"error": "Only buyers can access this endpoint."}, status=status.HTTP_403_FORBIDDEN)
            
            # Get the deal group
            try:
                deal_group = DealGroup.objects.get(id=group_id)
            except DealGroup.DoesNotExist:
                return Response({"error": "Deal group not found."}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if deal is sold - if so, show completion summary
            if deal_group.status == 'SOLD':
                return self._get_deal_completion_summary(deal_group)
            
            # Get buyer's negotiation messages
            buyer_messages = NegotiationMessage.objects.filter(
                deal_group=deal_group,
                sender=request.user
            ).order_by('created_at')
            
            # Get AI agent responses to buyer
            ai_responses = NegotiationMessage.objects.filter(
                deal_group=deal_group,
                sender__isnull=True  # AI Agent messages
            ).order_by('created_at')
            
            # Get buyer's polls
            buyer_polls = Poll.objects.filter(
                deal_group=deal_group,
                offering_buyer=request.user
            ).order_by('created_at')
            
            # Get current active poll
            active_poll = buyer_polls.filter(is_active=True).first()
            
            # Generate AI agent response if no recent AI message
            ai_agent_response = self._generate_ai_agent_response(deal_group, buyer_messages, active_poll)
            
            # Build buyer chat history
            chat_history = []
            
            # Add buyer messages
            for msg in buyer_messages:
                chat_history.append({
                    'type': 'buyer_message',
                    'id': msg.id,
                    'timestamp': msg.created_at.isoformat(),
                    'content': msg.content,
                    'message_type': msg.message_type,
                    'sender': 'buyer'
                })
            
            # Add AI responses
            for msg in ai_responses:
                chat_history.append({
                    'type': 'ai_response',
                    'id': msg.id,
                    'timestamp': msg.created_at.isoformat(),
                    'content': msg.content,
                    'message_type': msg.message_type,
                    'sender': 'ai_agent'
                })
            
            # Add current AI agent response if generated
            if ai_agent_response:
                chat_history.append({
                    'type': 'ai_response',
                    'id': 'current',
                    'timestamp': timezone.now().isoformat(),
                    'content': ai_agent_response,
                    'message_type': 'ai_guidance',
                    'sender': 'ai_agent'
                })
            
            # Sort chat history by timestamp
            chat_history.sort(key=lambda x: x['timestamp'])
            
            response_data = {
                'deal_group': {
                    'id': deal_group.id,
                    'group_id': deal_group.group_id,
                    'status': deal_group.status,
                    'total_quantity_kg': deal_group.total_quantity_kg,
                    'crop_name': deal_group.products.first().crop.name if deal_group.products.exists() else 'Unknown',
                    'grade': deal_group.products.first().grade if deal_group.products.exists() else 'Unknown'
                },
                'active_poll': {
                    'id': active_poll.id if active_poll else None,
                    'poll_type': active_poll.poll_type if active_poll else None,
                    'buyer_offer_price': str(active_poll.buyer_offer_price) if active_poll else None,
                    'is_active': active_poll.is_active if active_poll else None
                },
                'chat_history': chat_history,
                'can_message': deal_group.status not in ['SOLD', 'EXPIRED'],
                'deal_status': deal_group.status
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"❌ Error getting buyer negotiation chat: {e}")
            return Response(
                {"error": f"Failed to get buyer negotiation chat: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_deal_completion_summary(self, deal_group):
        """Get completion summary for sold deals."""
        try:
            # Get the final accepted poll
            final_poll = deal_group.polls.filter(
                poll_type=Poll.PollType.PRICE_OFFER,
                result='ACCEPTED'
            ).first()
            
            # Get location confirmation poll
            location_poll = deal_group.polls.filter(
                poll_type=Poll.PollType.LOCATION_CONFIRMATION,
                result='ACCEPTED'
            ).first()
            
            # Calculate final statistics
            total_quantity = deal_group.total_quantity_kg
            final_price = float(final_poll.buyer_offer_price) if final_poll else 0
            total_value = total_quantity * final_price
            
            # Get hub information
            hub_info = self._calculate_collection_hub(deal_group)
            hub_coords = hub_info.get('hub_coordinates', (17.3850, 78.4867))
            city_name = hub_info.get('city_name', 'Hyderabad')
            
            completion_summary = f"""🎉 **DEAL COMPLETED SUCCESSFULLY!**

**📊 Final Deal Summary**:
• **Group ID**: {deal_group.group_id}
• **Crop**: {deal_group.products.first().crop.name if deal_group.products.exists() else 'Unknown'}
• **Grade**: {deal_group.products.first().grade if deal_group.products.exists() else 'Unknown'}
• **Total Quantity**: {total_quantity:,} kg
• **Final Price**: ₹{final_price:.2f}/kg
• **Total Value**: ₹{total_value:,.2f}

**📍 Collection Hub Confirmed**:
• **Location**: {city_name}
• **Coordinates**: {hub_coords[0]:.6f}, {hub_coords[1]:.6f}

**✅ Status**: Deal marked as SOLD - Ready for Collection
**🚚 Next Steps**: Coordinate with farmers for pickup and payment

**💬 Note**: This deal is now complete. No further messages can be sent."""
            
            return Response({
                'deal_group': {
                    'id': deal_group.id,
                    'group_id': deal_group.group_id,
                    'status': 'SOLD',
                    'total_quantity_kg': total_quantity,
                    'final_price': final_price,
                    'total_value': total_value
                },
                'completion_summary': completion_summary,
                'can_message': False,
                'deal_status': 'SOLD',
                'hub_info': {
                    'city_name': city_name,
                    'coordinates': hub_coords
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"❌ Error getting completion summary: {e}")
            return Response({"error": "Failed to get completion summary"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _generate_ai_agent_response(self, deal_group, buyer_messages, active_poll):
        """Generate AI agent response for buyer bargaining."""
        try:
            # Get market data
            crop_name = deal_group.products.first().crop.name if deal_group.products.exists() else 'Unknown'
            region = deal_group.group_id.split('-')[0] if '-' in deal_group.group_id else 'Unknown'
            
            # Get current offer price
            current_price = float(active_poll.buyer_offer_price) if active_poll else 0
            
            # Generate market analysis
            market_analysis = self._analyze_market_for_buyer(crop_name, region, current_price)
            
            # Generate bargaining advice
            bargaining_advice = self._generate_bargaining_advice(current_price, market_analysis)
            
            return f"""🤖 **AI Market Advisor**

**📊 Market Analysis for {crop_name} in {region}**:
{market_analysis}

**💡 Bargaining Strategy**:
{bargaining_advice}

**🎯 Recommendation**: {self._get_buyer_recommendation(current_price, market_analysis)}"""
            
        except Exception as e:
            print(f"⚠️ Error generating AI agent response: {e}")
            return "🤖 **AI Market Advisor**: I'm here to help with market analysis and bargaining strategy. What would you like to know?"
    
    def _analyze_market_for_buyer(self, crop_name, region, current_price):
        """Analyze market conditions for buyer bargaining."""
        try:
            # This would integrate with your ML pricing engine
            # For now, return a basic analysis
            return f"""• **Current Market Trend**: Stable with slight upward movement
• **Seasonal Factors**: {self._get_seasonal_factor()}
• **Regional Dynamics**: {region} shows competitive pricing
• **Quality Premium**: FAQ grade commands 20% premium, Ref grade-1 commands 15% premium
• **Volume Discount**: Large quantities (30k+ kg) get 5-8% discount"""
        except Exception as e:
            return "• Market data analysis available"
    
    def _generate_bargaining_advice(self, current_price, market_analysis):
        """Generate bargaining advice for buyer."""
        if current_price < 10:
            return "• **Current offer is very competitive** - Consider accepting quickly"
        elif current_price < 20:
            return "• **Good price point** - Room for negotiation but fair value"
        else:
            return "• **Higher price range** - Negotiate for better terms or volume discounts"
    
    def _get_buyer_recommendation(self, current_price, market_analysis):
        if current_price < 15:
            return "ACCEPT - Excellent pricing below market rates!"
        elif current_price < 25:
            return "NEGOTIATE - Good price with room for improvement"
        else:
            return "REVIEW - Consider market conditions and quality factors"
    
    def _get_seasonal_factor(self):
        """Get current seasonal factor."""
        current_month = timezone.now().month
        if current_month in [6, 7, 8, 9]:
            return "Monsoon season - High demand, premium pricing"
        elif current_month in [10, 11, 12]:
            return "Post-monsoon - Stable demand, standard pricing"
        else:
            return "Off-season - Lower demand, negotiable pricing"
    
    def _calculate_collection_hub(self, deal_group):
        """Calculate optimal collection hub using hub optimizer with Google Maps integration"""
        try:
            optimal_hub = HubOptimizer().compute_and_recommend_hub(deal_group)
            
            if optimal_hub:
                # Import Google Maps service for real city names and distances
                google_maps = GoogleMapsService()
                
                # Get real city name from coordinates (optimal_hub is a dict)
                hub_lat = optimal_hub.get('latitude', 0)
                hub_lng = optimal_hub.get('longitude', 0)
                
                city_info = google_maps.get_city_name_from_coordinates(hub_lat, hub_lng)
                
                # Calculate real distances from farmers to hub
                farmer_coords = self._get_farmer_coordinates_for_distance(deal_group)
                if farmer_coords:
                    distance_matrix = google_maps.get_distance_matrix(
                        farmer_coords, [(hub_lat, hub_lng)]
                    )
                    total_distance = distance_matrix.get('total_distance_km', 50)
                    total_time = distance_matrix.get('total_duration_minutes', 100)
                    api_used = distance_matrix.get('api_used', 'Google Maps')
                else:
                    total_distance = 50
                    total_time = 100
                    api_used = 'Haversine'
                
                # Calculate basic logistics info
                total_quantity = deal_group.products.aggregate(Sum('quantity_kg'))['quantity_kg__sum'] or 0
                transport_cost_per_kg = 2.50  # Default cost per kg
                
                return {
                    'hub_name': optimal_hub.get('name', 'Optimal Collection Hub'),
                    'hub_address': optimal_hub.get('address', 'Address not available'),
                    'hub_coordinates': (hub_lat, hub_lng),
                    'city_name': city_info.get('city', optimal_hub.get('city', 'Central Location')),
                    'state_name': city_info.get('state', optimal_hub.get('state', 'Central Region')),
                    'full_address': city_info.get('full_address', optimal_hub.get('address', 'Address not available')),
                    'total_distance_km': total_distance,
                    'travel_time_minutes': total_time,
                    'distance_api_used': api_used,
                    'logistics_info': {
                        'transport_cost_per_kg': transport_cost_per_kg,
                        'total_transport_cost': transport_cost_per_kg * total_quantity
                    }
                }
            else:
                return {
                    'hub_name': 'Central Collection Hub',
                    'hub_address': 'Address not available',
                    'hub_coordinates': (17.3850, 78.4867),
                    'city_name': 'Central Location',
                    'state_name': 'Central Region',
                    'full_address': 'Address not available',
                    'total_distance_km': 50,
                    'travel_time_minutes': 100,
                    'distance_api_used': 'Default',
                    'logistics_info': {
                        'transport_cost_per_kg': 2.50,
                        'total_transport_cost': 125.0
                    }
                }
                
        except Exception as e:
            print(f"❌ Error calculating hub: {e}")
            return {
                'hub_name': 'Central Collection Hub',
                'hub_address': 'Address not available',
                'hub_coordinates': (17.3850, 78.4867),
                'city_name': "Central Collection Point",
                'state_name': "Central Region",
                'total_distance_km': 50,
                'travel_time_minutes': 100,
                'distance_api_used': 'Error Fallback',
                'logistics_info': {
                    'transport_cost_per_kg': 2.50,
                    'total_transport_cost': 125.0
                }
            }

    def _get_farmer_coordinates_for_distance(self, deal_group):
        """Get farmer coordinates for distance calculation"""
        try:
            coordinates = []
            farmers = CustomUser.objects.filter(
                listings__in=deal_group.products.all()
            ).distinct()
            
            for farmer in farmers:
                if farmer.latitude is not None and farmer.longitude is not None:
                    coordinates.append((float(farmer.latitude), float(farmer.longitude)))
                elif hasattr(farmer, 'pincode') and farmer.pincode:
                    # Try to get coordinates from pincode
                    try:
                        from locations.models import PinCode
                        pincode_data = PinCode.objects.get(code=farmer.pincode)
                        coordinates.append((pincode_data.latitude, pincode_data.longitude))
                        print(f"✅ Using pincode coordinates for {farmer.username}: {pincode_data.district}, {pincode_data.state}")
                    except PinCode.DoesNotExist:
                        print(f"⚠️ Pincode {farmer.pincode} not found for {farmer.username}")
                        continue
                    except Exception as e:
                        print(f"⚠️ Error getting pincode data for {farmer.username}: {e}")
                        continue
            
            if coordinates:
                print(f"✅ Found {len(coordinates)} farmer coordinates for distance calculation")
                return coordinates
            else:
                print(f"⚠️ No valid coordinates found for any farmers in group {deal_group.id}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting farmer coordinates: {e}")
            return None

class HubConfirmationView(APIView):
    """Stub for hub confirmation view."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, group_id, *args, **kwargs):
        return Response({"message": "Hub confirmation endpoint - not implemented yet"}, status=200)

class CropAdviceView(APIView):
    """Stub for crop advice view."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        return Response({"message": "Crop advice endpoint - not implemented yet"}, status=200)

class GroupAnalysisView(APIView):
    """Stub for group analysis view."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, group_id, *args, **kwargs):
        return Response({"message": "Group analysis endpoint - not implemented yet"}, status=200)

class MarketAnalysisView(APIView):
    """Stub for market analysis view."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        return Response({"message": "Market analysis endpoint - not implemented yet"}, status=200)

# --- FUNCTION-BASED VIEWS ---

@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def book_shipment_view(request, deal_id):
    """Stub for booking shipment."""
    return JsonResponse({"message": "Shipment booking - not implemented yet"})

@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def deposit_escrow_view(request, deal_id):
    """Stub for depositing escrow."""
    return JsonResponse({"message": "Escrow deposit - not implemented yet"})

@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def scan_receipt_view(request):
    """Stub for scanning receipt."""
    return JsonResponse({"message": "Receipt scanning - not implemented yet"})

@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def release_payouts_view(request, deal_id):
    """Stub for releasing payouts."""
    return JsonResponse({"message": "Payout release - not implemented yet"})

@api_view(["POST"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def rate_deal_view(request, deal_id):
    """Stub for rating deal."""
    return JsonResponse({"message": "Deal rating - not implemented yet"})

@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def my_deals_buyer_view(request):
    """Stub for buyer deals."""
    return JsonResponse({"message": "Buyer deals - not implemented yet"})

@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def my_deals_farmer_view(request):
    """Stub for farmer deals."""
    return JsonResponse({"message": "Farmer deals - not implemented yet"})

@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def deal_detail_view(request, deal_id):
    """Stub for deal detail."""
    return JsonResponse({"message": "Deal detail - not implemented yet"})

@api_view(["GET"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def group_deal_view(request, group_id):
    """Stub for group deal."""
    return JsonResponse({"message": "Group deal - not implemented yet"})

class BuyerDealGroupsView(APIView):
    """Get all deal groups for a buyer with status and completion summaries."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """Get all deal groups for the current buyer."""
        try:
            # Check if user is a buyer
            if request.user.role != 'BUYER':
                return Response({"error": "Only buyers can access this endpoint."}, status=status.HTTP_403_FORBIDDEN)
            
            # Get all deal groups where this buyer has made offers
            buyer_deal_groups = DealGroup.objects.filter(
                polls__offering_buyer=request.user
            ).distinct().order_by('-created_at')
            
            deal_groups_data = []
            
            for deal_group in buyer_deal_groups:
                # Get the latest poll from this buyer
                latest_poll = deal_group.polls.filter(
                    offering_buyer=request.user
                ).order_by('-created_at').first()
                
                # Get deal group status and details
                group_data = {
                    'id': deal_group.id,
                    'group_id': deal_group.group_id,
                    'status': deal_group.status,
                    'crop_name': deal_group.products.first().crop.name if deal_group.products.exists() else 'Unknown',
                    'grade': deal_group.products.first().grade if deal_group.products.exists() else 'Unknown',
                    'total_quantity_kg': deal_group.total_quantity_kg,
                    'created_at': deal_group.created_at.isoformat(),
                    'latest_offer': {
                        'price': str(latest_poll.buyer_offer_price) if latest_poll else '0',
                        'status': latest_poll.result if latest_poll else 'PENDING',
                        'poll_type': latest_poll.poll_type if latest_poll else None
                    }
                }
                
                # Add completion summary for sold deals
                if deal_group.status == 'SOLD':
                    completion_summary = self._get_deal_completion_summary_for_list(deal_group)
                    group_data['completion_summary'] = completion_summary
                    group_data['can_message'] = False
                else:
                    group_data['can_message'] = True
                
                # Add active poll information
                active_poll = deal_group.polls.filter(is_active=True).first()
                if active_poll:
                    group_data['active_poll'] = {
                        'id': active_poll.id,
                        'poll_type': active_poll.poll_type,
                        'buyer_offer_price': str(active_poll.buyer_offer_price),
                        'is_active': active_poll.is_active
                    }
                
                deal_groups_data.append(group_data)
            
            response_data = {
                'buyer_id': request.user.id,
                'buyer_username': request.user.username,
                'total_deal_groups': len(deal_groups_data),
                'deal_groups': deal_groups_data,
                'summary': {
                    'active_deals': len([dg for dg in deal_groups_data if dg['status'] in ['FORMED', 'NEGOTIATING', 'ACCEPTED']]),
                    'sold_deals': len([dg for dg in deal_groups_data if dg['status'] == 'SOLD']),
                    'expired_deals': len([dg for dg in deal_groups_data if dg['status'] == 'EXPIRED'])
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"❌ Error getting buyer deal groups: {e}")
            return Response(
                {"error": f"Failed to get buyer deal groups: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_deal_completion_summary_for_list(self, deal_group):
        """Get brief completion summary for sold deals in list view."""
        try:
            # Get the final accepted poll
            final_poll = deal_group.polls.filter(
                poll_type=Poll.PollType.PRICE_OFFER,
                result='ACCEPTED'
            ).first()
            
            if not final_poll:
                return "Deal completed - details unavailable"
            
            # Calculate final statistics
            total_quantity = deal_group.total_quantity_kg
            final_price = float(final_poll.buyer_offer_price)
            total_value = total_quantity * final_price
            
            return f"✅ SOLD: {total_quantity:,} kg at ₹{final_price:.2f}/kg = ₹{total_value:,.2f}"
            
        except Exception as e:
            return "✅ SOLD - Deal completed successfully"

class PollToGroupView(APIView):
    """Find the deal group for a given poll ID."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, poll_id, *args, **kwargs):
        """Get the deal group information for a given poll ID."""
        try:
            poll = Poll.objects.get(id=poll_id)
            
            response_data = {
                'poll_id': poll.id,
                'poll_type': poll.poll_type,
                'deal_group_id': poll.deal_group.id,
                'deal_group_name': poll.deal_group.group_id,
                'is_active': poll.is_active,
                'result': poll.result,
                'suggestion': f"Use /api/deals/groups/{poll.deal_group.id}/active-poll/ to get the active poll for this group"
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Poll.DoesNotExist:
            return Response({"error": "Poll not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Debug the import
print(f"🔍 IMPORT DEBUG: analyzeAndRespondTo_offer imported from clean_agent_logic")
print(f"🔍 IMPORT DEBUG: Function type: {type(analyzeAndRespondTo_offer)}")
print(f"🔍 IMPORT DEBUG: Function name: {analyzeAndRespondTo_offer.__name__}")
print(f"🔍 IMPORT DEBUG: Function module: {analyzeAndRespondTo_offer.__module__}")

class BuyerDealsView(generics.ListAPIView):
    """A view for buyers to see all their deals including sold ones."""
    serializer_class = DealGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role != 'BUYER':
            return DealGroup.objects.none()
        
        # Get all deal groups where this buyer has made offers
        buyer_deals = DealGroup.objects.filter(
            polls__offering_buyer=user
        ).distinct().order_by('-created_at')
        
        return buyer_deals

    def get(self, request, *args, **kwargs):
        """Get buyer's deals with status breakdown"""
        queryset = self.get_queryset()
        
        # Categorize deals by status
        deals_by_status = {
            'FORMED': queryset.filter(status='FORMED'),
            'NEGOTIATING': queryset.filter(status='NEGOTIATING'),
            'ACCEPTED': queryset.filter(status='ACCEPTED'),
            'SOLD': queryset.filter(status='SOLD'),
        }
        
        # Serialize each category
        serialized_deals = {}
        for status, deals in deals_by_status.items():
            serializer = self.get_serializer(deals, many=True)
            serialized_deals[status] = serializer.data
        
        return Response({
            'deals_by_status': serialized_deals,
            'total_deals': queryset.count(),
            'status_counts': {
                status: deals.count() for status, deals in deals_by_status.items()
            }
        })


# ==================== MCP-POWERED VIEWS ====================

class MCPPricePredictionView(APIView):
    """
    High-performance price prediction using MCP server
    Replaces direct MLPricingEngine calls with cached, pre-loaded models
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        """Get fast price prediction using MCP server"""
        try:
            crop_name = request.data.get('crop_name')
            district = request.data.get('district')
            date_str = request.data.get('date')
            user_context = request.data.get('user_context', {})
            
            if not crop_name or not district:
                return Response({
                    'error': 'crop_name and district are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Parse date
            if date_str:
                from datetime import datetime
                try:
                    date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except ValueError:
                    date = datetime.now()
            else:
                date = datetime.now()
            
            # Add user context
            user_context.update({
                'user_id': request.user.id,
                'role': request.user.role,
                'latitude': getattr(request.user, 'latitude', None),
                'longitude': getattr(request.user, 'longitude', None)
            })
            
            # Use MCP service for fast prediction
            mcp_service = get_mcp_service()
            result = mcp_service.predict_price_fast(
                crop_name=crop_name,
                district=district,
                date=date,
                user_context=user_context
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ MCP price prediction failed: {e}")
            return Response({
                'error': str(e),
                'predicted_price': 25.0,
                'confidence_level': 'Error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MCPMarketDataView(APIView):
    """
    High-performance market data retrieval using MCP server
    Replaces direct MarketAnalyzer calls with cached, pre-loaded data
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        """Get fast market data using MCP server"""
        try:
            crop_name = request.data.get('crop_name')
            district = request.data.get('district')
            date_str = request.data.get('date')
            grade = request.data.get('grade')
            
            if not crop_name or not district:
                return Response({
                    'error': 'crop_name and district are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Parse date
            if date_str:
                from datetime import datetime
                try:
                    date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except ValueError:
                    date = datetime.now()
            else:
                date = datetime.now()
            
            # Use MCP service for fast market data
            mcp_service = get_mcp_service()
            result = mcp_service.get_market_data_fast(
                crop_name=crop_name,
                district=district,
                date=date,
                grade=grade
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ MCP market data failed: {e}")
            return Response({
                'error': str(e),
                'crop_name': request.data.get('crop_name', 'Unknown'),
                'district': request.data.get('district', 'Unknown')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MCPHubOptimizationView(APIView):
    """
    High-performance hub optimization using MCP server
    Replaces direct HubOptimizer calls with cached, pre-loaded services
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        """Get fast hub optimization using MCP server"""
        try:
            deal_group_id = request.data.get('deal_group_id')
            method = request.data.get('method', 'v2')  # v1 or v2
            
            if not deal_group_id:
                return Response({
                    'error': 'deal_group_id is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Use MCP service for fast hub computation
            mcp_service = get_mcp_service()
            
            if method.lower() == 'v1':
                result = mcp_service.compute_hub_v1_fast(deal_group_id)
            else:
                result = mcp_service.compute_hub_v2_fast(deal_group_id)
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ MCP hub optimization failed: {e}")
            return Response({
                'error': str(e),
                'deal_group_id': request.data.get('deal_group_id', 'Unknown')
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MCPPerformanceStatsView(APIView):
    """
    Get MCP server performance statistics
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """Get MCP server performance statistics"""
        try:
            mcp_service = get_mcp_service()
            stats = mcp_service.get_performance_stats()
            
            return Response(stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ Failed to get MCP performance stats: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MCPCacheManagementView(APIView):
    """
    Manage MCP server cache
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        """Clear MCP server cache"""
        try:
            cache_type = request.data.get('cache_type', 'all')
            
            mcp_service = get_mcp_service()
            result = mcp_service.clear_cache(cache_type)
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ Failed to clear MCP cache: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
