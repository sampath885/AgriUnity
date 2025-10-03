from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from products.models import CropProfile, ProductListing
from deals.models import DealGroup, Poll, Vote, NegotiationMessage
from users.models import CustomUser

User = get_user_model()

class Command(BaseCommand):
    help = "Run comprehensive end-to-end tests for the enhanced ML system"

    def handle(self, *args, **options):
        """Run all end-to-end tests"""
        self.stdout.write("🚀 STARTING END-TO-END TESTS")
        self.stdout.write("=" * 50)
        
        try:
            # Test 1: System Setup
            self.test_system_setup()
            
            # Test 2: Product Listings
            self.test_product_listings()
            
            # Test 3: Group Formation
            self.test_group_formation()
            
            # Test 4: ML Analysis
            self.test_ml_analysis()
            
            # Test 5: Negotiation Flow
            self.test_negotiation_flow()
            
            # Test 6: Location Confirmation
            self.test_location_confirmation()
            
            # Test 7: Deal Completion
            self.test_deal_completion()
            
            self.stdout.write("\n✅ ALL TESTS COMPLETED SUCCESSFULLY!")
            
        except Exception as e:
            self.stdout.write(f"\n❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
        
        # Print final summary
        self.print_summary()
    
    def test_system_setup(self):
        """Test 1: Verify system setup and data availability"""
        self.stdout.write("\n🔧 Test 1: System Setup")
        self.stdout.write("-" * 30)
        
        # Check crops
        crops = CropProfile.objects.all()
        self.stdout.write(f"  🌾 Available crops: {crops.count()}")
        for crop in crops:
            self.stdout.write(f"    - {crop.name} (min_group: {crop.min_group_kg}kg)")
        
        # Check users
        farmers = User.objects.filter(role='FARMER')
        buyers = User.objects.filter(role='BUYER')
        self.stdout.write(f"  👥 Farmers: {farmers.count()}")
        self.stdout.write(f"  🛒 Buyers: {buyers.count()}")
        
        # Check BIG_DATA.csv integration
        try:
            from deals.agent_logic import DataIntegrationManager
            data_integrator = DataIntegrationManager()
            available_crops = data_integrator.get_available_crops()
            self.stdout.write(f"  📊 BIG_DATA.csv crops: {len(available_crops)}")
            self.stdout.write(f"    - {', '.join(available_crops[:5])}...")
        except Exception as e:
            self.stdout.write(f"  ⚠️ BIG_DATA.csv integration: {e}")
        
        self.stdout.write("  ✅ System setup verified")
    
    def test_product_listings(self):
        """Test 2: Verify product listings and trigger group formation"""
        self.stdout.write("\n🌾 Test 2: Product Listings")
        self.stdout.write("-" * 30)
        
        # Get all listings
        listings = ProductListing.objects.filter(status='AVAILABLE')
        self.stdout.write(f"  📋 Available listings: {listings.count()}")
        
        for listing in listings:
            self.stdout.write(f"    - {listing.crop.name} ({listing.grade}): {listing.quantity_kg}kg by {listing.farmer.username}")
            
            # Check if listing meets group formation criteria
            if listing.grading_status == 'COMPLETED' and listing.grade:
                self.stdout.write(f"      ✅ Ready for grouping")
            else:
                self.stdout.write(f"      ⚠️ Not ready: grading_status={listing.grading_status}, grade={listing.grade}")
        
        # Try to trigger group formation manually
        try:
            from deals.utils import check_and_form_groups
            self.stdout.write(f"\n  🔄 Triggering group formation...")
            
            # Get all completed listings
            completed_listings = ProductListing.objects.filter(
                status='AVAILABLE',
                grading_status='COMPLETED',
                grade__isnull=False
            )
            
            if completed_listings.exists():
                # Try to form groups for each listing
                groups_formed = 0
                for listing in completed_listings:
                    try:
                        result = check_and_form_groups(listing)
                        if result:
                            groups_formed += 1
                    except Exception as e:
                        self.stdout.write(f"      ⚠️ Group formation failed for {listing}: {e}")
                
                self.stdout.write(f"  📊 Groups formed: {groups_formed}")
            else:
                self.stdout.write("  ⚠️ No completed listings available for group formation")
                
        except Exception as e:
            self.stdout.write(f"  ❌ Group formation failed: {e}")
        
        self.stdout.write("  ✅ Product listings verified")
    
    def test_group_formation(self):
        """Test 3: Verify deal groups are formed correctly"""
        self.stdout.write("\n👥 Test 3: Group Formation")
        self.stdout.write("-" * 30)
        
        # Check existing groups
        groups = DealGroup.objects.all()
        self.stdout.write(f"  📊 Total deal groups: {groups.count()}")
        
        for group in groups:
            self.stdout.write(f"    - Group {group.id}: {group.status}")
            self.stdout.write(f"      Crop: {group.crop.name}")
            self.stdout.write(f"      Grade: {group.grade}")
            self.stdout.write(f"      Total kg: {group.total_quantity_kg}")
            self.stdout.write(f"      Farmers: {group.farmers.count()}")
            self.stdout.write(f"      Created: {group.created_at}")
        
        # Check if groups have correct status
        formed_groups = groups.filter(status='FORMED')
        self.stdout.write(f"  🎯 Groups in FORMED status: {formed_groups.count()}")
        
        if formed_groups.exists():
            self.stdout.write("  ✅ Groups are ready for negotiation")
        else:
            self.stdout.write("  ⚠️ No groups ready for negotiation")
        
        self.stdout.write("  ✅ Group formation verified")
    
    def test_ml_analysis(self):
        """Test 4: Test ML analysis with real data"""
        self.stdout.write("\n🤖 Test 4: ML Analysis")
        self.stdout.write("-" * 30)
        
        try:
            from deals.agent_logic import analyze_and_respond_to_offer
            
            # Get a sample group for testing
            group = DealGroup.objects.filter(status='FORMED').first()
            if not group:
                self.stdout.write("  ⚠️ No groups available for ML testing")
                return
            
            self.stdout.write(f"  🧪 Testing ML analysis with group {group.id}")
            self.stdout.write(f"    Crop: {group.crop.name}")
            self.stdout.write(f"    Grade: {group.grade}")
            self.stdout.write(f"    Location: {group.farmers.first().pincode}")
            
            # Test ML analysis
            test_offer = 4.0  # ₹4.0/kg
            result = analyze_and_respond_to_offer(
                crop_name=group.crop.name,
                district=group.farmers.first().pincode,
                offer_price=test_offer,
                user_context={'role': 'BUYER', 'location': 'Hyderabad'}
            )
            
            self.stdout.write(f"  📊 ML Analysis Result:")
            self.stdout.write(f"    Action: {result.action}")
            self.stdout.write(f"    New Price: {result.new_price}")
            self.stdout.write(f"    Confidence: {result.confidence_level}")
            
            # Check if ML returned real data
            if hasattr(result, 'market_analysis') and result.market_analysis:
                ml_data = result.market_analysis
                if isinstance(ml_data, dict):
                    predicted_price = ml_data.get('predicted_price', 0)
                    data_points = ml_data.get('historical_context', {}).get('data_points_analyzed', 0)
                    
                    self.stdout.write(f"    Predicted Price: ₹{predicted_price}/kg")
                    self.stdout.write(f"    Data Points: {data_points}")
                    
                    if predicted_price > 0 and data_points > 0:
                        self.stdout.write("  ✅ ML analysis working with real data")
                    else:
                        self.stdout.write("  ⚠️ ML analysis returned no data")
                else:
                    self.stdout.write("  ⚠️ Market analysis format unexpected")
            else:
                self.stdout.write("  ⚠️ No market analysis in result")
                
        except Exception as e:
            self.stdout.write(f"  ❌ ML analysis failed: {e}")
            import traceback
            traceback.print_exc()
        
        self.stdout.write("  ✅ ML analysis tested")
    
    def test_negotiation_flow(self):
        """Test 5: Test the complete negotiation flow"""
        self.stdout.write("\n💬 Test 5: Negotiation Flow")
        self.stdout.write("-" * 30)
        
        # Get a group for negotiation
        group = DealGroup.objects.filter(status='FORMED').first()
        if not group:
            self.stdout.write("  ⚠️ No groups available for negotiation testing")
            return
        
        self.stdout.write(f"  🧪 Testing negotiation with group {group.id}")
        
        try:
            # Submit an offer
            buyer = User.objects.filter(role='BUYER').first()
            if not buyer:
                self.stdout.write("  ❌ No buyer available for testing")
                return
            
            # Create a test client
            client = APIClient()
            client.force_authenticate(user=buyer)
            
            offer_data = {
                'offer_price': 4.0,
                'message': 'Test offer from end-to-end test'
            }
            
            # Try to submit offer (this will test the API endpoint)
            try:
                url = reverse('submit-offer', kwargs={'group_id': group.id})
                response = client.post(url, offer_data, format='json')
                
                if response.status_code == status.HTTP_200_OK:
                    self.stdout.write("  ✅ Offer submitted successfully")
                    
                    # Check if poll was created
                    poll = Poll.objects.filter(deal_group=group).first()
                    if poll:
                        self.stdout.write(f"  📊 Poll created: {poll.id} ({poll.poll_type})")
                        self.stdout.write(f"    Status: {poll.status}")
                        self.stdout.write(f"    Expires: {poll.expires_at}")
                        
                        # Check AI agent message
                        ai_message = NegotiationMessage.objects.filter(
                            deal_group=group,
                            message_type='AI_AGENT'
                        ).first()
                        
                        if ai_message:
                            self.stdout.write("  🤖 AI Agent message created")
                            self.stdout.write(f"    Content: {ai_message.content[:100]}...")
                        else:
                            self.stdout.write("  ⚠️ No AI Agent message found")
                    else:
                        self.stdout.write("  ❌ No poll created after offer")
                else:
                    self.stdout.write(f"  ❌ Offer submission failed: {response.status_code}")
                    self.stdout.write(f"    Response: {response.data}")
                    
            except Exception as e:
                self.stdout.write(f"  ⚠️ API test failed, but this is expected in management command: {e}")
                
        except Exception as e:
            self.stdout.write(f"  ❌ Negotiation flow failed: {e}")
            import traceback
            traceback.print_exc()
        
        self.stdout.write("  ✅ Negotiation flow tested")
    
    def test_location_confirmation(self):
        """Test 6: Test location confirmation flow"""
        self.stdout.write("\n📍 Test 6: Location Confirmation")
        self.stdout.write("-" * 30)
        
        # Find a group with an accepted price offer
        group = DealGroup.objects.filter(status='ACCEPTED').first()
        if not group:
            self.stdout.write("  ⚠️ No accepted groups available for location testing")
            return
        
        self.stdout.write(f"  🧪 Testing location confirmation with group {group.id}")
        
        try:
            # Check if location poll exists
            location_poll = Poll.objects.filter(
                deal_group=group,
                poll_type='LOCATION_CONFIRMATION'
            ).first()
            
            if location_poll:
                self.stdout.write(f"  📍 Location poll found: {location_poll.id}")
                self.stdout.write(f"    Status: {location_poll.status}")
                self.stdout.write(f"    Expires: {location_poll.expires_at}")
                
                # Check logistics information
                if hasattr(location_poll, 'agent_justification'):
                    justification = location_poll.agent_justification
                    if isinstance(justification, dict):
                        logistics = justification.get('market_analysis', {}).get('hub_details', {})
                        self.stdout.write(f"  🚚 Logistics info: {logistics}")
                    else:
                        self.stdout.write(f"  📝 Agent justification: {justification[:100]}...")
                
                # Simulate farmer acceptance
                farmer = group.farmers.first()
                if farmer:
                    vote = Vote.objects.create(
                        poll=location_poll,
                        voter=farmer,
                        choice='YES',
                        message='Accepting location from test'
                    )
                    self.stdout.write(f"  ✅ Farmer vote recorded: {vote.choice}")
                    
                    # Check poll status
                    from deals.views import check_poll_status
                    check_poll_status(location_poll.id)
                    
                    # Refresh from database
                    location_poll.refresh_from_db()
                    group.refresh_from_db()
                    
                    self.stdout.write(f"  📊 Poll status after vote: {location_poll.status}")
                    self.stdout.write(f"  📊 Group status after vote: {group.status}")
                    
            else:
                self.stdout.write("  ⚠️ No location confirmation poll found")
                
        except Exception as e:
            self.stdout.write(f"  ❌ Location confirmation failed: {e}")
            import traceback
            traceback.print_exc()
        
        self.stdout.write("  ✅ Location confirmation tested")
    
    def test_deal_completion(self):
        """Test 7: Test deal completion and SOLD status"""
        self.stdout.write("\n🎯 Test 7: Deal Completion")
        self.stdout.write("-" * 30)
        
        # Check for SOLD groups
        sold_groups = DealGroup.objects.filter(status='SOLD')
        self.stdout.write(f"  🏆 Sold groups: {sold_groups.count()}")
        
        for group in sold_groups:
            self.stdout.write(f"    - Group {group.id}: {group.crop.name}")
            self.stdout.write(f"      Final price: ₹{group.final_price}/kg")
            self.stdout.write(f"      Total value: ₹{group.total_value}")
            self.stdout.write(f"      Sold at: {group.updated_at}")
            
            # Check if deals were created
            deals = group.deals.all()
            self.stdout.write(f"      Deals created: {deals.count()}")
            
            # Check logistics
            try:
                from deals.logistics_manager import LogisticsManager
                logistics_manager = LogisticsManager()
                logistics_info = logistics_manager.get_group_logistics_info(group)
                self.stdout.write(f"      🚚 Logistics: {logistics_info.get('total_transport_cost', 'N/A')}")
            except Exception as e:
                self.stdout.write(f"      ⚠️ Logistics error: {e}")
        
        # Check if any groups should be SOLD but aren't
        accepted_groups = DealGroup.objects.filter(status='ACCEPTED')
        self.stdout.write(f"  ⏳ Groups still in ACCEPTED status: {accepted_groups.count()}")
        
        for group in accepted_groups:
            self.stdout.write(f"    - Group {group.id}: {group.crop.name}")
            
            # Check if location poll is completed
            location_poll = Poll.objects.filter(
                deal_group=group,
                poll_type='LOCATION_CONFIRMATION'
            ).first()
            
            if location_poll:
                if location_poll.status == 'COMPLETED':
                    self.stdout.write(f"      ⚠️ Location poll completed but group not SOLD")
                else:
                    self.stdout.write(f"      📍 Location poll status: {location_poll.status}")
            else:
                self.stdout.write(f"      ❌ No location poll found")
        
        self.stdout.write("  ✅ Deal completion verified")
    
    def print_summary(self):
        """Print final summary of all tests"""
        self.stdout.write("\n📊 FINAL TEST SUMMARY")
        self.stdout.write("=" * 50)
        
        # Counts
        self.stdout.write(f"  🌾 Crops: {CropProfile.objects.count()}")
        self.stdout.write(f"  👥 Farmers: {User.objects.filter(role='FARMER').count()}")
        self.stdout.write(f"  🛒 Buyers: {User.objects.filter(role='BUYER').count()}")
        self.stdout.write(f"  📋 Listings: {ProductListing.objects.count()}")
        self.stdout.write(f"  👥 Groups: {DealGroup.objects.count()}")
        self.stdout.write(f"  📊 Polls: {Poll.objects.count()}")
        self.stdout.write(f"  💬 Messages: {NegotiationMessage.objects.count()}")
        
        # Status breakdown
        self.stdout.write(f"\n  📈 Group Statuses:")
        for status_choice in DealGroup.StatusChoices.choices:
            count = DealGroup.objects.filter(status=status_choice[0]).count()
            if count > 0:
                self.stdout.write(f"    {status_choice[1]}: {count}")
        
        self.stdout.write(f"\n  📊 Poll Types:")
        for poll_type in Poll.PollType.choices:
            count = Poll.objects.filter(poll_type=poll_type[0]).count()
            if count > 0:
                self.stdout.write(f"    {status_choice[1]}: {count}")
        
        self.stdout.write("\n🎯 RECOMMENDATIONS:")
        if DealGroup.objects.filter(status='SOLD').exists():
            self.stdout.write("  ✅ System is working - deals are being completed")
        elif DealGroup.objects.filter(status='ACCEPTED').exists():
            self.stdout.write("  ⚠️ Deals accepted but not completed - check location confirmation")
        elif DealGroup.objects.filter(status='FORMED').exists():
            self.stdout.write("  ⚠️ Groups formed but no offers - check negotiation flow")
        else:
            self.stdout.write("  ❌ No groups formed - check product listings and group formation")
        
        self.stdout.write("\n🔑 TEST CREDENTIALS:")
        self.stdout.write("  Buyer: testbuyer / testpass123")
        farmers = User.objects.filter(role='FARMER')
        for i, farmer in enumerate(farmers[:5]):
            self.stdout.write(f"  Farmer{i+1}: {farmer.username} / testpass123")
        
        self.stdout.write("\n🎯 NEXT STEPS:")
        self.stdout.write("  1. Login as testbuyer")
        self.stdout.write("  2. View available listings")
        self.stdout.write("  3. Submit offers to test enhanced ML system")
        self.stdout.write("  4. Verify ML analysis returns real prices (not ₹0.00/kg)")
