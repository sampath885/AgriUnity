# backend/products/models.py
from django.db import models
from users.models import CustomUser # Assuming your user model is in the 'users' app

class CropProfile(models.Model):
    name = models.CharField(max_length=100, unique=True)
    perishability_score = models.IntegerField(help_text="1-10, 10 is highly perishable")
    is_storable = models.BooleanField(default=False)
    has_msp = models.BooleanField(default=False)
    min_group_kg = models.PositiveIntegerField(default=10000, help_text="Minimum total kg required to form a deal group")

    def __str__(self):
        return self.name

class ProductListing(models.Model):
    class StatusChoices(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        GROUPED = 'GROUPED', 'Grouped'
        ACCEPTED = 'ACCEPTED', 'Accepted (Awaiting Escrow)'
        IN_TRANSIT = 'IN_TRANSIT', 'In Transit'
        DELIVERED = 'DELIVERED', 'Delivered'
        PAID = 'PAID', 'Paid'
        SOLD = 'SOLD', 'Sold'
        GRADING = 'GRADING', 'Grading'

    class GradingStatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
    
    # Updated grade choices to match BIG_DATA.csv
    class GradeChoices(models.TextChoices):
        FAQ = 'FAQ', 'FAQ'
        MEDIUM = 'Medium', 'Medium'
        LARGE = 'Large', 'Large'
        LOCAL = 'Local', 'Local'
        NON_FAQ = 'Non-FAQ', 'Non-FAQ'
        REF_GRADE_1 = 'Ref grade-1', 'Ref grade-1'
        REF_GRADE_2 = 'Ref grade-2', 'Ref grade-2'

    farmer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='listings')
    crop = models.ForeignKey(CropProfile, on_delete=models.CASCADE)
    grade = models.CharField(max_length=20, choices=GradeChoices.choices)
    quantity_kg = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.AVAILABLE)
    created_at = models.DateTimeField(auto_now_add=True)
    grading_status = models.CharField(max_length=20, choices=GradingStatusChoices.choices, default=GradingStatusChoices.PENDING)
    grade_confidence = models.FloatField(null=True, blank=True)
    grading_completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.quantity_kg}kg of {self.crop.name} from {self.farmer.username}"