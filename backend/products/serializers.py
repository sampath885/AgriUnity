# backend/products/serializers.py
from rest_framework import serializers
from .models import ProductListing, CropProfile

class CropProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropProfile
        fields = '__all__'

class ProductListingSerializer(serializers.ModelSerializer):
    # Make crop a write-only field that accepts the crop name
    crop_name = serializers.CharField(write_only=True)
    # Remove image requirement; allow manual grade selection via dropdown
    grade = serializers.ChoiceField(choices=[
        ('FAQ', 'FAQ'),
        ('Medium', 'Medium'),
        ('Large', 'Large'),
        ('Local', 'Local'),
        ('Non-FAQ', 'Non-FAQ'),
        ('Ref grade-1', 'Ref grade-1'),
        ('Ref grade-2', 'Ref grade-2')
    ])
    
    class Meta:
        model = ProductListing
        fields = ['id', 'crop', 'grade', 'quantity_kg', 'status', 'created_at', 'crop_name', 'grading_status', 'grade_confidence']
        # crop and status are set programmatically
        read_only_fields = ['crop', 'status', 'grading_status', 'grade_confidence']

    def create(self, validated_data):
        crop_name = validated_data.pop('crop_name')
        try:
            crop_profile = CropProfile.objects.get(name__iexact=crop_name)
        except CropProfile.DoesNotExist:
            raise serializers.ValidationError(f"Crop '{crop_name}' is not supported.")
        
        # Get the farmer from the request context
        farmer = self.context['request'].user

        # Create listing with farmer-selected grade; mark as AVAILABLE immediately
        listing = ProductListing.objects.create(
            farmer=farmer,
            crop=crop_profile,
            status=ProductListing.StatusChoices.AVAILABLE,
            grading_status=ProductListing.GradingStatusChoices.COMPLETED,
            grade_confidence=None,
            **validated_data
        )

        return listing