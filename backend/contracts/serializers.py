from rest_framework import serializers
from .models import ForwardContract, ContractCommitment, AdvancePayment


class ForwardContractSerializer(serializers.ModelSerializer):
    crop_name = serializers.CharField(write_only=True)
    total_committed_qty = serializers.ReadOnlyField()
    remaining_qty = serializers.ReadOnlyField()

    class Meta:
        model = ForwardContract
        fields = [
            'id', 'buyer', 'crop', 'crop_name', 'region', 'grade', 'delivery_window_start', 
            'delivery_window_end', 'price_per_kg', 'min_qty_kg', 'max_qty_kg', 'advance_pct',
            'terms', 'status', 'created_at', 'updated_at', 'total_committed_qty', 'remaining_qty'
        ]
        read_only_fields = ['buyer', 'crop', 'created_at', 'updated_at', 'total_committed_qty', 'remaining_qty']

    def create(self, validated_data):
        from products.models import CropProfile
        crop_name = validated_data.pop('crop_name')
        try:
            crop = CropProfile.objects.get(name__iexact=crop_name)
        except CropProfile.DoesNotExist:
            raise serializers.ValidationError({ 'crop_name': 'Unknown crop' })
        buyer = self.context['request'].user
        return ForwardContract.objects.create(buyer=buyer, crop=crop, **validated_data)


class ContractCommitmentSerializer(serializers.ModelSerializer):
    contract_details = ForwardContractSerializer(source='contract', read_only=True)

    class Meta:
        model = ContractCommitment
        fields = ['id', 'contract', 'contract_details', 'farmer', 'committed_qty_kg', 'status', 'created_at', 'approved_at']
        read_only_fields = ['farmer', 'created_at', 'approved_at']

    def create(self, validated_data):
        validated_data['farmer'] = self.context['request'].user
        return super().create(validated_data)


class AdvancePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvancePayment
        fields = ['id', 'contract', 'farmer', 'amount', 'status', 'external_ref', 'created_at', 'processed_at']
        read_only_fields = ['farmer', 'created_at', 'processed_at']


