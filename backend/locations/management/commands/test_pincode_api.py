# backend/locations/management/commands/test_pincode_api.py

from django.core.management.base import BaseCommand
from django.test import RequestFactory
from locations.views import PincodeDetailView
from locations.models import PinCode
import json

class Command(BaseCommand):
    help = "Test the pincode API endpoint directly"

    def add_arguments(self, parser):
        parser.add_argument('pincode', type=str, help='Pincode to test')

    def handle(self, *args, **options):
        pincode = options['pincode']
        
        self.stdout.write(f"Testing pincode API for: {pincode}")
        
        # Check if pincode exists in database
        try:
            pincode_obj = PinCode.objects.get(code=pincode)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Pincode {pincode} found in database: {pincode_obj.district}, {pincode_obj.state}"
                )
            )
        except PinCode.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"✗ Pincode {pincode} NOT found in database")
            )
            return
        
        # Test the API view directly
        factory = RequestFactory()
        request = factory.get(f'/api/locations/pincode/{pincode}/')
        
        try:
            view = PincodeDetailView()
            response = view.get(request, pincode=pincode)
            
            self.stdout.write(f"API Response Status: {response.status_code}")
            self.stdout.write(f"API Response Data: {response.data}")
            
            if response.status_code == 200:
                self.stdout.write(
                    self.style.SUCCESS("✓ API endpoint working correctly!")
                )
            else:
                self.stdout.write(
                    self.style.ERROR("✗ API endpoint returned error")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ API test failed: {str(e)}")
            )
