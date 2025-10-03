# backend/deals/serializers.py
from rest_framework import serializers
import json
from .models import DealGroup, Poll, Vote, NegotiationMessage, GroupMessage
import logging

logger = logging.getLogger(__name__)

class DealGroupSerializer(serializers.ModelSerializer):
    """Serializer for DealGroup with enhanced data extraction"""
    crop_name = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    collection_hub = serializers.SerializerMethodField()
    buyer_info = serializers.SerializerMethodField()
    deal_summary = serializers.SerializerMethodField()

    class Meta:
        model = DealGroup
        fields = ['id', 'group_id', 'total_quantity_kg', 'status', 'created_at', 
                  'crop_name', 'grade', 'region', 'products', 'collection_hub', 'buyer_info', 'deal_summary']

    def _first_listing(self, obj):
        """Get the first product listing for a deal group"""
        try:
            if hasattr(obj, 'products') and obj.products.exists():
                listing = obj.products.first()
                print(f"🔍 Serializer: Found listing {listing.id} for group {obj.group_id}")
                print(f"🔍 Serializer: Listing crop: {listing.crop.name if listing.crop else 'None'}")
                print(f"🔍 Serializer: Listing grade: {listing.grade}")
                print(f"🔍 Serializer: Listing farmer: {listing.farmer.username if listing.farmer else 'None'}")
                return listing
            else:
                print(f"🔍 Serializer: No products found for group {obj.group_id}")
                return None
        except Exception as e:
            print(f"🔍 Serializer: Error in _first_listing: {e}")
            return None

    def get_crop_name(self, obj):
        """Extract crop name from listing or group_id"""
        try:
            listing = self._first_listing(obj)
            if listing and hasattr(listing, 'crop') and listing.crop:
                return listing.crop.name
            # Fallback: try to extract from group_id
            if obj.group_id:
                group_parts = obj.group_id.split('-')
                if len(group_parts) >= 1:
                    return group_parts[0].replace('_', ' ').title()
            return None
        except Exception as e:
            print(f"Error getting crop_name: {e}")
            # Fallback: try to extract from group_id
            if obj.group_id:
                group_parts = obj.group_id.split('-')
                if len(group_parts) >= 1:
                    return group_parts[0].replace('_', ' ').title()
            return None

    def get_grade(self, obj):
        """Extract grade from listing or group_id"""
        try:
            listing = self._first_listing(obj)
            if listing and hasattr(listing, 'grade'):
                return listing.grade
            # Fallback: try to extract from group_id
            if obj.group_id:
                group_parts = obj.group_id.split('-')
                if len(group_parts) >= 2:
                    return group_parts[1].replace('_', ' ').title()
            return None
        except Exception as e:
            print(f"Error getting grade: {e}")
            # Fallback: try to extract from group_id
            if obj.group_id:
                group_parts = obj.group_id.split('-')
                if len(group_parts) >= 2:
                    return group_parts[1].replace('_', ' ').title()
            return None

    def get_region(self, obj):
        """Extract region from farmer location or group_id"""
        try:
            listing = self._first_listing(obj)
            if listing and hasattr(listing, 'farmer') and listing.farmer:
                if hasattr(listing.farmer, 'region') and listing.farmer.region:
                    return listing.farmer.region
                # Fallback: try to get from pincode
                if hasattr(listing.farmer, 'pincode') and listing.farmer.pincode:
                    pincode = listing.farmer.pincode
                    if pincode.startswith('50'):
                        return "Telangana"
                    elif pincode.startswith('51'):
                        return "Andhra Pradesh"
                    elif pincode.startswith('60'):
                        return "Tamil Nadu"
                    elif pincode.startswith('11'):
                        return "Delhi"
                    else:
                        return "Central India"
            # Fallback: try to extract from group_id (old format)
            if obj.group_id:
                group_parts = obj.group_id.split('-')
                if len(group_parts) >= 3:  # Old format had region
                    return group_parts[0].replace('_', ' ').title()
            return "Central India"  # Default fallback
        except Exception as e:
            print(f"Error getting region: {e}")
            return "Central India"  # Default fallback

    def get_collection_hub(self, obj):
        """Get collection hub information with city and state"""
        if obj.recommended_collection_point:
            hub = obj.recommended_collection_point
            return {
                'id': hub.id,
                'name': hub.name,
                'address': hub.address,
                'city': hub.name.split(',')[0] if hub.name and ',' in hub.name else hub.name,
                'state': hub.name.split(',')[1].strip() if hub.name and ',' in hub.name else 'Central Region',
                'coordinates': {
                    'latitude': hub.latitude,
                    'longitude': hub.longitude
                }
            }
        return None

    def get_buyer_info(self, obj):
        """Get buyer information for the deal group"""
        try:
            # Get the most recent price offer poll
            price_poll = obj.polls.filter(
                poll_type='price_offer'
            ).order_by('-created_at').first()
            
            if price_poll and price_poll.offering_buyer:
                buyer = price_poll.offering_buyer
                return {
                    'buyer_id': buyer.id,
                    'buyer_username': buyer.username,
                    'buyer_name': f"{getattr(buyer, 'first_name', '')} {getattr(buyer, 'last_name', '')}".strip(),
                    'offer_price': price_poll.buyer_offer_price,
                    'offer_date': price_poll.created_at,
                    'poll_result': price_poll.result
                }
            return None
        except Exception as e:
            print(f"Error getting buyer_info: {e}")
            return None

    def get_deal_summary(self, obj):
        """Get deal summary information"""
        try:
            # Get the most recent price offer poll
            price_poll = obj.polls.filter(
                poll_type='price_offer'
            ).order_by('-created_at').first()
            
            if price_poll:
                # Calculate total value
                total_value = price_poll.buyer_offer_price * obj.total_quantity_kg if price_poll.buyer_offer_price else 0
                
                # Get location poll if exists
                location_poll = obj.polls.filter(
                    poll_type='location_confirmation'
                ).order_by('-created_at').first()
                
                return {
                    'total_quantity_kg': obj.total_quantity_kg,
                    'offer_price_per_kg': price_poll.buyer_offer_price,
                    'total_value': total_value,
                    'deal_status': obj.status,
                    'location_confirmed': location_poll.result == 'ACCEPTED' if location_poll else False,
                    'created_date': obj.created_at,
                    'last_updated': obj.updated_at if hasattr(obj, 'updated_at') else obj.created_at
                }
            return None
        except Exception as e:
            print(f"Error getting deal_summary: {e}")
            return None

    def get_products(self, obj):
        """Get products count and basic info for the frontend"""
        products = getattr(obj, 'products', [])
        if hasattr(products, 'count'):
            return {
                'count': products.count(),
                'listings': products.values('id', 'farmer__id', 'farmer__username', 'quantity_kg', 'grade')
            }
        return {'count': 0, 'listings': []}

class OfferSerializer(serializers.Serializer):
    """Serializer for buyer offers"""
    price_per_kg = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    quantity_kg = serializers.IntegerField(min_value=1, required=False)  # Optional for backward compatibility

class PollSerializer(serializers.ModelSerializer):
    """Enhanced serializer for polls with AI agent justification"""
    agent_justification = serializers.SerializerMethodField()
    deal_group_info = serializers.SerializerMethodField()
    collection_location = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = '__all__'

    def get_collection_location(self, obj):
        """Get collection location from deal group's recommended collection point"""
        try:
            if obj.deal_group and obj.deal_group.recommended_collection_point:
                hub = obj.deal_group.recommended_collection_point
                # Parse city and state from hub name (assuming format: "City, State")
                hub_parts = hub.name.split(',') if hub.name and ',' in hub.name else [hub.name, 'Central Region']
                city = hub_parts[0].strip() if hub_parts[0] else 'Central Location'
                state = hub_parts[1].strip() if len(hub_parts) > 1 and hub_parts[1] else 'Central Region'
                
                return {
                    'hub_name': hub.name,
                    'city': city,
                    'state': state,
                    'address': hub.address,
                    'coordinates': {
                        'latitude': hub.latitude,
                        'longitude': hub.longitude
                    },
                    'display_name': f"{city}, {state}"
                }
            return None
        except Exception as e:
            print(f"Error getting collection location: {e}")
            return None

    def get_deal_group_info(self, obj):
        """Get enhanced deal group information including location"""
        try:
            if obj.deal_group:
                group_data = {
                    'id': obj.deal_group.id,
                    'group_id': obj.deal_group.group_id,
                    'status': obj.deal_group.status,
                    'total_quantity_kg': obj.deal_group.total_quantity_kg,
                    'created_at': obj.deal_group.created_at,
                }
                
                # Add collection hub information
                if obj.deal_group.recommended_collection_point:
                    hub = obj.deal_group.recommended_collection_point
                    hub_parts = hub.name.split(',') if hub.name and ',' in hub.name else [hub.name, 'Central Region']
                    group_data['collection_hub'] = {
                        'id': hub.id,
                        'name': hub.name,
                        'city': hub_parts[0].strip() if hub_parts[0] else 'Central Location',
                        'state': hub_parts[1].strip() if len(hub_parts) > 1 and hub_parts[1] else 'Central Region',
                        'address': hub.address,
                        'coordinates': {
                            'latitude': hub.latitude,
                            'longitude': hub.longitude
                        }
                    }
                
                return group_data
            return None
        except Exception as e:
            print(f"Error getting deal group info: {e}")
            return None

    def get_agent_justification(self, obj):
        """Enhanced agent justification with real location data and advanced bargaining"""
        try:
            if not obj.agent_justification:
                return None
            
            # Parse the JSON string
            if isinstance(obj.agent_justification, str):
                try:
                    data = json.loads(obj.agent_justification)
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error in agent_justification: {e}")
                    print(f"❌ Raw data: {obj.agent_justification}")
                    return None
            else:
                data = obj.agent_justification
            
            # Ensure data is a dictionary
            if not isinstance(data, dict):
                print(f"❌ agent_justification data is not a dict: {type(data)}")
                return None
            
            # Debug: Print the actual data structure
            print(f"🔍 DEBUG: agent_justification data structure: {data.keys()}")
            print(f"🔍 DEBUG: real_location_info: {data.get('real_location_info', {})}")
            print(f"🔍 DEBUG: logistics_details: {data.get('logistics_details', {})}")
            print(f"🔍 DEBUG: market_insights: {data.get('market_insights', {})}")
            print(f"🔍 DEBUG: agent_analysis: {data.get('agent_analysis', {})}")
            
            # Return the parsed data directly - frontend will handle different poll types
            return data
            
        except Exception as e:
            print(f"❌ Error in get_agent_justification: {e}")
            return None

    def _create_explanation_components(self, data, city_name, state_name, total_distance, travel_time):
        """Create explanation components with real location data"""
        try:
            components = []
            
            # Market analysis component
            market_insights = data.get('market_insights', {})
            if market_insights and market_insights.get('crop_name'):
                components.append({
                    'title': 'Market Analysis',
                    'content': f"Current market conditions for {market_insights.get('crop_name', 'your crop')}",
                    'details': f"Market rate: ₹{market_insights.get('current_market_price', 'N/A')}/kg",
                    'icon': '📊'
                })
            
            # Location component - always show for location polls
            components.append({
                'title': 'Collection Hub Location',
                'content': f"Optimal collection point in {city_name}, {state_name}",
                'details': f"Location: {city_name}, {state_name}",
                'icon': '📍'
            })
            
            # Distance component - always show for location polls
            components.append({
                'title': 'Transport Optimization',
                'content': f"Total distance: {total_distance} km",
                'details': f"Estimated travel time: {travel_time} minutes",
                'icon': '🚚'
            })
            
            # Logistics efficiency component
            logistics_details = data.get('logistics_details', {})
            if logistics_details:
                components.append({
                    'title': 'Logistics Efficiency',
                    'content': logistics_details.get('logistics_efficiency', 'Good efficiency'),
                    'details': f"Reduces transport costs by optimizing collection routes",
                    'icon': '⚡'
                })
            
            return components
        except Exception as e:
            print(f"❌ Error in _create_explanation_components: {e}")
            return []

    def _create_reference_prices(self, data):
        """Create reference prices with real market data"""
        try:
            market_insights = data.get('market_insights', {})
            agent_analysis = data.get('agent_analysis', {})
            
            reference_prices = {}
            
            # Current market rate
            if market_insights and market_insights.get('current_market_price'):
                reference_prices['current_market_rate'] = f"₹{market_insights.get('current_market_price')} per kg"
            
            # Buyer offer price
            if data.get('buyer_offer_price'):
                reference_prices['buyer_offer_price'] = f"₹{data['buyer_offer_price']} per kg"
            
            # Quality premium
            if market_insights and market_insights.get('quality_premium'):
                reference_prices['quality_premium'] = market_insights.get('quality_premium')
            
            # Logistics savings
            logistics_details = data.get('logistics_details', {})
            if logistics_details and logistics_details.get('estimated_transport_cost'):
                reference_prices['logistics_savings'] = logistics_details.get('estimated_transport_cost')
            
            # Add crop information if available
            if market_insights and market_insights.get('crop_name'):
                reference_prices['crop_name'] = market_insights.get('crop_name')
            
            return reference_prices
        except Exception as e:
            print(f"❌ Error in _create_reference_prices: {e}")
            return {}

    def _create_advanced_bargain_script(self, data, city_name, state_name, total_distance, travel_time, distance_api):
        """Create advanced bargain script with price analysis, market insights, and AI recommendations"""
        try:
            market_insights = data.get('market_insights', {})
            agent_analysis = data.get('agent_analysis', {})
            
            script_parts = []
            
            # Advanced price analysis section
            script_parts.append(f"💰 **Advanced Price Analysis & Market Intelligence**")
            script_parts.append(f"")
            
            if market_insights:
                current_market_price = market_insights.get('current_market_price', 0)
                buyer_offer = data.get('buyer_offer_price', 0)
                crop_name = market_insights.get('crop_name', 'your crop')
                
                script_parts.append(f"📊 **Market Intelligence for {crop_name}:**")
                script_parts.append(f"• Current market rate: ₹{current_market_price}/kg")
                script_parts.append(f"• Buyer's offer: ₹{buyer_offer}/kg")
                
                if current_market_price and buyer_offer:
                    price_diff = current_market_price - buyer_offer
                    if price_diff > 0:
                        script_parts.append(f"• Price difference: ₹{price_diff}/kg below market")
                        script_parts.append(f"• Market position: Below market rate")
                        script_parts.append(f"• Negotiation leverage: High - you can demand more")
                    elif price_diff < 0:
                        script_parts.append(f"• Price difference: ₹{abs(price_diff)}/kg above market")
                        script_parts.append(f"• Market position: Above market rate")
                        script_parts.append(f"• Negotiation leverage: Low - consider accepting")
                    else:
                        script_parts.append(f"• Price difference: At market rate")
                        script_parts.append(f"• Market position: Competitive offer")
                        script_parts.append(f"• Negotiation leverage: Moderate - room for discussion")
                
                # Quality analysis
                if market_insights.get('quality_premium'):
                    script_parts.append(f"• Quality premium: {market_insights.get('quality_premium')}")
                
                # Seasonal factors
                if market_insights.get('seasonal_factors'):
                    script_parts.append(f"• Seasonal factors: {market_insights.get('seasonal_factors')}")
                
                # Market trends
                if market_insights.get('market_trend'):
                    script_parts.append(f"• Market trend: {market_insights.get('market_trend')}")
            
            # Advanced logistics analysis
            script_parts.append(f"")
            script_parts.append(f"🚚 **Advanced Logistics & Transport Analysis:**")
            script_parts.append(f"📍 **Collection Hub:** {city_name}, {state_name}")
            script_parts.append(f"📏 **Distance:** {total_distance} km")
            script_parts.append(f"⏱️ **Travel Time:** {travel_time} minutes")
            script_parts.append(f"🔧 **API Used:** {distance_api}")
            
            # Transport cost analysis
            logistics_details = data.get('logistics_details', {})
            if logistics_details:
                transport_cost = logistics_details.get('estimated_transport_cost', 'Calculating...')
                script_parts.append(f"💰 **Transport Cost:** {transport_cost}")
                
                if logistics_details.get('logistics_efficiency'):
                    script_parts.append(f"⚡ **Efficiency:** {logistics_details.get('logistics_efficiency')}")
            
            # AI Agent Advanced Recommendations
            script_parts.append(f"")
            script_parts.append(f"🤖 **AI Agent Advanced Recommendations:**")
            if agent_analysis:
                action = agent_analysis.get('action', 'Analyzing offer...')
                script_parts.append(f"• **Recommended Action:** {action}")
                
                if agent_analysis.get('new_price'):
                    script_parts.append(f"• **Suggested Price:** ₹{agent_analysis.get('new_price')}/kg")
                
                if agent_analysis.get('confidence_level'):
                    script_parts.append(f"• **Confidence Level:** {agent_analysis.get('confidence_level')}")
                
                if agent_analysis.get('justification_for_farmers'):
                    script_parts.append(f"• **Detailed Justification:** {agent_analysis.get('justification_for_farmers')}")
                
                # Negotiation strategy
                if action == 'ACCEPT':
                    script_parts.append(f"• **Strategy:** Accept quickly - this is a good deal!")
                elif action == 'REJECT':
                    script_parts.append(f"• **Strategy:** Hold firm - market supports higher pricing")
                elif action == 'NEGOTIATE':
                    script_parts.append(f"• **Strategy:** Negotiate for better terms - you have leverage")
            else:
                script_parts.append(f"• **Status:** Analyzing market conditions and buyer offer...")
                script_parts.append(f"• **Next Step:** Wait for AI analysis to complete")
            
            # Profit analysis
            script_parts.append(f"")
            script_parts.append(f"💵 **Profit Analysis:**")
            if market_insights and data.get('buyer_offer_price'):
                current_price = float(data['buyer_offer_price'])
                
                # Calculate potential profit margins
                if current_market_price:
                    market_price = float(current_market_price)
                    profit_margin = ((market_price - current_price) / market_price) * 100
                    
                    if profit_margin > 0:
                        script_parts.append(f"• **Market Opportunity:** ₹{market_price - current_price}/kg potential profit")
                        script_parts.append(f"• **Profit Margin:** {profit_margin:.1f}% below market rate")
                        script_parts.append(f"• **Recommendation:** Consider negotiating for higher price")
                    else:
                        script_parts.append(f"• **Market Position:** ₹{abs(market_price - current_price)}/kg above market")
                        script_parts.append(f"• **Profit Margin:** {abs(profit_margin):.1f}% above market rate")
                        script_parts.append(f"• **Recommendation:** This is a competitive offer")
            
            return "\n".join(script_parts)
        except Exception as e:
            print(f"❌ Error in _create_advanced_bargain_script: {e}")
            return "AI analysis in progress..."

class VoteSerializer(serializers.Serializer):
    """Serializer for votes"""
    choice = serializers.ChoiceField(choices=Vote.VoteChoice.choices)

class NegotiationMessageSerializer(serializers.ModelSerializer):
    """Serializer for negotiation messages"""
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = NegotiationMessage
        fields = ['id', 'deal_group', 'sender', 'sender_name', 'message_type', 'content', 'created_at']
        read_only_fields = ['id', 'deal_group', 'sender', 'sender_name', 'created_at']

    def get_sender_name(self, obj):
        return obj.sender.username if obj.sender else 'AI Agent'

class GroupMessageSerializer(serializers.ModelSerializer):
    """Enhanced serializer for group messages with AI Union Leader Agent support"""
    sender_name = serializers.SerializerMethodField()
    message_type_display = serializers.CharField(source='get_message_type_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    narrative_story = serializers.CharField(read_only=True)
    market_data_summary = serializers.JSONField(read_only=True)
    hub_details = serializers.JSONField(read_only=True)
    trust_indicators = serializers.JSONField(read_only=True)
    is_pinned = serializers.BooleanField(read_only=True)
    farmer_reactions = serializers.JSONField(read_only=True)
    created_at_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = GroupMessage
        fields = [
            'id', 'deal_group', 'sender', 'sender_name', 'message_type', 'message_type_display',
            'category', 'category_display', 'content', 'is_ai_agent', 'ai_response_to',
            'session_id', 'narrative_story', 'market_data_summary', 'hub_details',
            'trust_indicators', 'is_pinned', 'farmer_reactions', 'created_at', 'created_at_formatted'
        ]
        read_only_fields = ['id', 'created_at', 'sender_name', 'message_type_display', 'category_display']
    
    def get_sender_name(self, obj):
        """Get sender name for display"""
        return obj.sender_name
    
    def get_created_at_formatted(self, obj):
        """Get formatted creation time"""
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    
    def to_representation(self, instance):
        """Custom representation with enhanced data"""
        data = super().to_representation(instance)
        
        # Add AI agent specific formatting
        if instance.is_ai_agent:
            data['ai_agent_info'] = {
                'role': 'Union Leader',
                'expertise': ['Market Analysis', 'Price Negotiation', 'Logistics Planning', 'Trust Building'],
                'response_type': instance.get_category_display()
            }
            
            # Format narrative story for better display
            if instance.narrative_story:
                data['narrative_story_formatted'] = self._format_narrative_story(instance.narrative_story)
            
            # Format hub details for better display
            if instance.hub_details:
                data['hub_details_formatted'] = self._format_hub_details(instance.hub_details)
            
            # Format trust indicators for better display
            if instance.trust_indicators:
                data['trust_indicators_formatted'] = self._format_trust_indicators(instance.trust_indicators)
        
        return data
    
    def _format_narrative_story(self, narrative_story: str) -> str:
        """Format narrative story for better display"""
        # Convert markdown-style formatting to HTML or plain text
        formatted = narrative_story.replace('**', '<strong>').replace('**', '</strong>')
        formatted = formatted.replace('\n\n', '<br><br>')
        formatted = formatted.replace('\n', '<br>')
        return formatted
    
    def _format_hub_details(self, hub_details: dict) -> dict:
        """Format hub details for better display"""
        formatted = {}
        
        if 'available_hubs' in hub_details:
            formatted['hubs'] = []
            for hub in hub_details['available_hubs']:
                formatted['hubs'].append({
                    'name': hub.get('name', 'Unknown Hub'),
                    'location': hub.get('location', 'Unknown Location'),
                    'services': hub.get('services', []),
                    'advantages': hub.get('advantages', 'Standard services')
                })
        
        if 'logistics_advantages' in hub_details:
            formatted['advantages'] = hub_details['logistics_advantages']
        
        if 'cost_savings' in hub_details:
            formatted['cost_savings'] = hub_details['cost_savings']
        
        return formatted
    
    def _format_trust_indicators(self, trust_indicators: dict) -> dict:
        """Format trust indicators for better display"""
        formatted = {}
        
        for key, value in trust_indicators.items():
            if key == 'data_transparency':
                formatted['Data Transparency'] = value
            elif key == 'data_source':
                formatted['Data Source'] = value
            elif key == 'confidence_level':
                formatted['Confidence Level'] = value
            elif key == 'market_coverage':
                formatted['Market Coverage'] = value
            elif key == 'farmer_benefit':
                formatted['Farmer Benefits'] = value
        
        return formatted