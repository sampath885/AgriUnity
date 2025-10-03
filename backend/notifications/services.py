from django.utils import timezone
from notifications.models import Notification, NotificationTemplate


def create_notification(user, notification_type, title, message, **kwargs):
    """Create a notification for a user."""
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        **kwargs
    )
    
    # In production, this would trigger SMS/email sending
    # For now, just mark as sent
    notification.status = Notification.StatusChoices.SENT
    notification.sent_at = timezone.now()
    notification.save()
    
    print(f"Notification sent to {user.username}: {title}")
    return notification


def notify_poll_created(poll):
    """Notify farmers when a poll is created for their group."""
    from deals.models import DealGroup
    from users.models import CustomUser
    
    # Get all farmers in the group
    farmers = CustomUser.objects.filter(
        listings__in=poll.deal_group.products.all()
    ).distinct()
    
    for farmer in farmers:
        create_notification(
            user=farmer,
            notification_type=Notification.NotificationType.POLL_CREATED,
            title=f"New Poll: {poll.deal_group.group_id}",
            message=f"A buyer has offered ₹{poll.buyer_offer_price}/kg for your {poll.deal_group.products.first().crop.name}. Please vote within 6 hours.",
            related_poll_id=poll.id,
            related_deal_group_id=poll.deal_group.id
        )


def notify_group_formed(deal_group):
    """Notify farmers when their group is formed."""
    from users.models import CustomUser
    
    farmers = CustomUser.objects.filter(
        listings__in=deal_group.products.all()
    ).distinct()
    
    for farmer in farmers:
        create_notification(
            user=farmer,
            notification_type=Notification.NotificationType.GROUP_FORMED,
            title=f"Group Formed: {deal_group.group_id}",
            message=f"Your {deal_group.products.first().crop.name} has been grouped with {deal_group.total_quantity_kg}kg total. Collection point: {deal_group.recommended_collection_point.name if deal_group.recommended_collection_point else 'TBD'}",
            related_deal_group_id=deal_group.id
        )


def notify_deal_completed(deal):
    """Notify participants when a deal is completed."""
    from users.models import CustomUser
    
    # Notify farmers
    farmers = CustomUser.objects.filter(
        listings__in=deal.group.products.all()
    ).distinct()
    
    for farmer in farmers:
        create_notification(
            user=farmer,
            notification_type=Notification.NotificationType.DEAL_COMPLETED,
            title=f"Deal Completed: {deal.group.group_id}",
            message=f"Your deal has been finalized at ₹{deal.final_price_per_kg}/kg. Payment processing will begin soon.",
            related_deal_group_id=deal.group.id
        )
    
    # Notify buyer
    create_notification(
        user=deal.buyer,
        notification_type=Notification.NotificationType.DEAL_COMPLETED,
        title=f"Deal Completed: {deal.group.group_id}",
        message=f"Your purchase of {deal.group.total_quantity_kg}kg has been confirmed. Logistics details will be provided shortly.",
        related_deal_group_id=deal.group.id
    )
