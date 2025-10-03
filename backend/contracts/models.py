from django.db import models
from django.conf import settings
from products.models import CropProfile


class ForwardContract(models.Model):
    class StatusChoices(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        FILLED = 'FILLED', 'Filled'
        EXPIRED = 'EXPIRED', 'Expired'
        CANCELLED = 'CANCELLED', 'Cancelled'

    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='forward_contracts')
    crop = models.ForeignKey(CropProfile, on_delete=models.CASCADE)
    region = models.CharField(max_length=100)
    grade = models.CharField(max_length=20)
    delivery_window_start = models.DateField()
    delivery_window_end = models.DateField()
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    min_qty_kg = models.PositiveIntegerField()
    max_qty_kg = models.PositiveIntegerField()
    advance_pct = models.DecimalField(max_digits=5, decimal_places=2, help_text="Advance payment percentage")
    terms = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.crop.name} - {self.region} - {self.delivery_window_start} to {self.delivery_window_end}"

    @property
    def total_committed_qty(self):
        # Sum only approved commitments; ContractCommitment has 'status' field
        return sum(
            commitment.committed_qty_kg
            for commitment in self.commitments.filter(status='APPROVED')
        )

    @property
    def remaining_qty(self):
        return max(0, self.max_qty_kg - self.total_committed_qty)


class ContractCommitment(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    contract = models.ForeignKey(ForwardContract, on_delete=models.CASCADE, related_name='commitments')
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contract_commitments')
    committed_qty_kg = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_commitments')

    def __str__(self):
        return f"{self.farmer.username} - {self.committed_qty_kg}kg for {self.contract}"


class AdvancePayment(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSED = 'PROCESSED', 'Processed'
        FAILED = 'FAILED', 'Failed'

    contract = models.ForeignKey(ForwardContract, on_delete=models.CASCADE, related_name='advance_payments')
    farmer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='advance_payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    external_ref = models.CharField(max_length=100, blank=True, help_text="Payment gateway reference")
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Advance payment of ₹{self.amount} to {self.farmer.username} for {self.contract}"


