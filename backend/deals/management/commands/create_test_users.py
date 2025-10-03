from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from products.models import CropProfile, ProductListing
from deals.models import DealGroup
from datetime import datetime, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = "Create test users and sample data for testing the enhanced ML system"

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of test farmers to create (default: 5)',
        )

    def handle(self, *args, **options):
        farmer_count = options['count']
        
        self.stdout.write(f"👥 Creating {farmer_count} test farmers...")
        
        try:
            # Check if crops exist
            crops = CropProfile.objects.all()
            if not crops.exists():
                self.stdout.write(
                    self.style.ERROR("❌ No crops found. Run 'python manage.py seed_crops' first.")
                )
                return
            
            # Create test farmers
            farmers = []
            for i in range(farmer_count):
                # Create user without primary_crops first
                farmer = User.objects.create_user(
                    username=f'farmer{i+1}',
                    email=f'farmer{i+1}@test.com',
                    password='testpass123',
                    first_name=f'Test',
                    last_name=f'Farmer{i+1}',
                    role='FARMER',
                    pincode='500001',
                    latitude=17.3850 + (i * 0.01),  # Hyderabad area
                    longitude=78.4867 + (i * 0.01),
                )
                
                # Set primary_crops using the proper method
                farmer.primary_crops.set(crops[:2])  # First 2 crops
                farmers.append(farmer)
                self.stdout.write(f"  ✅ Created farmer: {farmer.username}")
            
            # Create additional farmers with same crop to trigger group formation
            self.stdout.write("\n🌾 Creating additional farmers with same crop for group formation...")
            
            # Create 3 more farmers with Tomato (same crop, same grade)
            tomato_crop = crops.filter(name='Tomato').first()
            if tomato_crop:
                for i in range(3):
                    additional_farmer = User.objects.create_user(
                        username=f'tomato_farmer{i+1}',
                        email=f'tomato_farmer{i+1}@test.com',
                        password='testpass123',
                        first_name=f'Tomato',
                        last_name=f'Farmer{i+1}',
                        role='FARMER',
                        pincode='500001',
                        latitude=17.3850 + (i * 0.02),
                        longitude=78.4867 + (i * 0.02),
                    )
                    additional_farmer.primary_crops.set([tomato_crop])
                    farmers.append(additional_farmer)
                    self.stdout.write(f"  ✅ Created tomato farmer: {additional_farmer.username}")
            
            # Create test buyer
            buyer = User.objects.create_user(
                username='testbuyer',
                email='buyer@test.com',
                password='testpass123',
                first_name='Test',
                last_name='Buyer',
                role='BUYER',
                pincode='500002',
                latitude=17.3850,
                longitude=78.4867
            )
            self.stdout.write(f"  ✅ Created buyer: {buyer.username}")
            
            # Create sample product listings
            self.stdout.write("\n🌾 Creating sample product listings...")
            
            for i, farmer in enumerate(farmers):
                # Create listing for first crop
                crop = crops[i % len(crops)]
                listing = ProductListing.objects.create(
                    farmer=farmer,
                    crop=crop,
                    grade='A',
                    quantity_kg=10000 + (i * 1000),
                    status='AVAILABLE',
                    grading_status='COMPLETED'  # Fix: Set grading status to COMPLETED
                )
                self.stdout.write(f"  ✅ Created listing: {listing.crop.name} - {listing.quantity_kg}kg")
            
            # Create additional Tomato listings to trigger group formation
            if tomato_crop:
                self.stdout.write("\n🍅 Creating additional Tomato listings for group formation...")
                tomato_farmers = [f for f in farmers if 'tomato' in f.username]
                
                for i, farmer in enumerate(tomato_farmers):
                    # Each farmer gets 15,000kg to meet the 20,000kg minimum requirement
                    listing = ProductListing.objects.create(
                        farmer=farmer,
                        crop=tomato_crop,
                        grade='A',
                        quantity_kg=15000,
                        status='AVAILABLE',
                        grading_status='COMPLETED'
                    )
                    self.stdout.write(f"  ✅ Created Tomato listing: {listing.quantity_kg}kg by {farmer.username}")
            
            # Show summary
            self.stdout.write("\n📊 TEST DATA SUMMARY:")
            self.stdout.write("=" * 40)
            self.stdout.write(f"  Farmers: {User.objects.filter(role='FARMER').count()}")
            self.stdout.write(f"  Buyers: {User.objects.filter(role='BUYER').count()}")
            self.stdout.write(f"  Product Listings: {ProductListing.objects.count()}")
            self.stdout.write(f"  Deal Groups: {DealGroup.objects.count()}")
            
            self.stdout.write("\n🎯 READY FOR TESTING:")
            self.stdout.write("  1. Login as testbuyer")
            self.stdout.write("  2. View available listings")
            self.stdout.write("  3. Submit offers to test enhanced ML system")
            self.stdout.write("  4. Verify ML analysis returns real prices (not ₹0.00/kg)")
            
            self.stdout.write("\n🔑 TEST CREDENTIALS:")
            self.stdout.write("  Buyer: testbuyer / testpass123")
            for i, farmer in enumerate(farmers):
                self.stdout.write(f"  {farmer.username}: {farmer.username} / testpass123")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error creating test users: {e}")
            )
            import traceback
            traceback.print_exc()
