from django.db import models
from django.conf import settings


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        POLL_CREATED = 'POLL_CREATED', 'Poll Created'
        POLL_EXPIRED = 'POLL_EXPIRED', 'Poll Expired'
        GROUP_FORMED = 'GROUP_FORMED', 'Group Formed'
        DEAL_COMPLETED = 'DEAL_COMPLETED', 'Deal Completed'
        CONTRACT_OFFER = 'CONTRACT_OFFER', 'Contract Offer'
        SYSTEM_UPDATE = 'SYSTEM_UPDATE', 'System Update'
        HUB_SELECTED = 'HUB_SELECTED', 'Hub Selected'
        ESCROW_DEPOSITED = 'ESCROW_DEPOSITED', 'Escrow Deposited'
        SHIPMENT_BOOKED = 'SHIPMENT_BOOKED', 'Shipment Booked'
        PAYOUT_RELEASED = 'PAYOUT_RELEASED', 'Payout Released'

    class StatusChoices(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        FAILED = 'FAILED', 'Failed'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Optional related object references
    related_deal_group_id = models.IntegerField(null=True, blank=True)
    related_poll_id = models.IntegerField(null=True, blank=True)
    related_contract_id = models.IntegerField(null=True, blank=True)
    related_hub_id = models.IntegerField(null=True, blank=True)
    related_deal_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} for {self.user.username} - {self.title}"


class NotificationTemplate(models.Model):
    """Templates for different types of notifications."""
    notification_type = models.CharField(max_length=20, choices=Notification.NotificationType.choices)
    title_template = models.CharField(max_length=255)
    message_template = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.notification_type} Template"
