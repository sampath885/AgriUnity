# backend/users/serializers.py

import re
from rest_framework import serializers
from .models import CustomUser, BuyerProfile, OTPCode
from django.utils import timezone
from datetime import timedelta
from deals.models import Deal

# UserSerializer can remain the same
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'name', 'role')

class BuyerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyerProfile
        fields = ('business_name', 'gst_number')


class RegisterSerializer(serializers.ModelSerializer):
    # Nest the profile serializer. Make it optional.
    buyer_profile = BuyerProfileSerializer(required=False)
    
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    # Optional: allow farmers to pick primary crops at sign-up to auto-enroll in hubs
    primary_crops = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    
    class Meta:
        model = CustomUser
        # Add 'buyer_profile' and 'primary_crops' to the fields list
        fields = ('username', 'password', 'name', 'role', 'phone_number', 'pincode', 'region', 'buyer_profile', 'primary_crops')

    def validate(self, attrs):
        # Debug logging
        print(f"🔍 Validating registration data: {attrs}")
        
        # Validate phone_number: exactly 10 digits
        phone_number = attrs.get('phone_number')
        if phone_number and not re.fullmatch(r'^\d{10}$', phone_number):
            print(f"❌ Phone validation failed: {phone_number}")
            raise serializers.ValidationError({
                'phone_number': 'Phone number must be exactly 10 digits with numbers only.'
            })

        role = attrs.get('role')
        buyer_profile_data = attrs.get('buyer_profile')
        # PIN validation: if supplied, must be 6 digits
        pin = attrs.get('pincode')
        if pin and not re.fullmatch(r'^\d{6}$', pin):
            print(f"❌ Pincode validation failed: {pin}")
            raise serializers.ValidationError({'pincode': 'PIN must be 6 digits.'})

        print(f"✅ Validation passed for role: {role}")
        
        # Enforce that buyer-specific fields are required if the role is BUYER
        if role == 'BUYER' and not buyer_profile_data:
            raise serializers.ValidationError({"buyer_profile": "Business name and GST number are required for buyers."})
        
        if role == 'BUYER' and buyer_profile_data:
            if not buyer_profile_data.get('business_name'):
                raise serializers.ValidationError({"business_name": "This field is required for buyers."})
            if not buyer_profile_data.get('gst_number'):
                raise serializers.ValidationError({"gst_number": "This field is required for buyers."})
            
            # Validate GST number format
            gst_number = buyer_profile_data.get('gst_number', '')
            gst_regex = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
            if not re.fullmatch(gst_regex, gst_number):
                raise serializers.ValidationError({
                    'gst_number': 'Invalid GSTIN format. Please enter a valid 15-character GSTIN (uppercase letters and digits).'
                })
        
        return attrs

    def create(self, validated_data):
        buyer_profile_data = validated_data.pop('buyer_profile', None)
        primary_crops_data = validated_data.pop('primary_crops', [])
        
        user = CustomUser.objects.create_user(**validated_data)
        
        # If buyer profile data was provided, update the auto-created profile
        if user.role == 'BUYER' and buyer_profile_data:
            BuyerProfile.objects.filter(user=user).update(**buyer_profile_data)

        # Handle primary_crops for farmers after user creation
        if primary_crops_data and user.role == 'FARMER':
            try:
                from products.models import CropProfile
                crops = list(CropProfile.objects.filter(name__in=primary_crops_data))
                if crops:
                    user.primary_crops.set(crops)
            except Exception:
                pass

        return user


class PublicUserSerializer(serializers.ModelSerializer):
    primary_crops = serializers.SerializerMethodField()
    successful_deals_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('id', 'name', 'role', 'region', 'trust_score', 'primary_crops', 'successful_deals_count')
        read_only_fields = fields

    def get_primary_crops(self, obj: CustomUser):
        return list(obj.primary_crops.values_list('name', flat=True))

    def get_successful_deals_count(self, obj: CustomUser):
        try:
            return Deal.objects.filter(group__products__farmer=obj).distinct().count()
        except Exception:
            return 0


class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.RegexField(regex=r'^\d{10}$')

    def create(self, validated_data):
        phone_number = validated_data['phone_number']
        # Create or find a user for this phone number (farmer by default)
        user, _ = CustomUser.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                'username': f"farmer_{phone_number}",
                'role': CustomUser.Role.FARMER,
            },
        )
        # Generate a simple 6-digit code (in production: use a secure service)
        import random
        code = f"{random.randint(100000, 999999)}"
        otp = OTPCode.objects.create(
            user=user,
            phone_number=phone_number,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        # TODO: integrate SMS provider here; for now, return code only in DEBUG
        return otp


class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.RegexField(regex=r'^\d{10}$')
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        phone = attrs['phone_number']
        code = attrs['code']
        try:
            otp = OTPCode.objects.filter(phone_number=phone).order_by('-created_at').first()
        except OTPCode.DoesNotExist:
            raise serializers.ValidationError({'code': 'OTP not found. Please request a new code.'})
        if not otp or otp.code != code or not otp.is_valid():
            raise serializers.ValidationError({'code': 'Invalid or expired OTP code.'})
        attrs['otp'] = otp
        return attrs

    def create(self, validated_data):
        otp: OTPCode = validated_data['otp']
        otp.mark_used()
        return otp.user