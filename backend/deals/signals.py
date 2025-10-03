from __future__ import annotations

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.db import transaction

from .models import DealGroup, Poll, Vote
from .logistics_manager import compute_hub_recommendation, recompute_hub_recommendation
from notifications.services import notify_poll_created, notify_group_formed


@receiver(post_save, sender=DealGroup)
def handle_deal_group_created(sender, instance, created, **kwargs):
    """Handle deal group creation and updates."""
    if created:
        # New deal group created - compute hub recommendation
        transaction.on_commit(lambda: compute_hub_recommendation(instance))
        
        # Notify farmers about group formation
        transaction.on_commit(lambda: notify_group_formed(instance))
    else:
        # Deal group updated - check if we need to recompute hub recommendation
        # This could happen if products are added/removed
        pass


@receiver(m2m_changed, sender=DealGroup.products.through)
def handle_deal_group_products_changed(sender, instance, action, pk_set, **kwargs):
    """Handle changes to deal group products (membership changes)."""
    if action in ['post_add', 'post_remove']:
        # Products added or removed - recompute hub recommendation
        transaction.on_commit(lambda: recompute_hub_recommendation(instance))
        
        # Update total quantity when products change
        from django.db.models import Sum
        total_quantity = instance.products.aggregate(
            total=Sum('quantity_kg')
        )['total'] or 0
        instance.total_quantity_kg = total_quantity
        instance.save(update_fields=['total_quantity_kg'])
        print(f"🔄 Updated group {instance.id} total quantity to {total_quantity}kg")


@receiver(post_save, sender=Poll)
def handle_poll_created(sender, instance, created, **kwargs):
    """Handle poll creation."""
    if created:
        # Notify farmers about new poll
        transaction.on_commit(lambda: notify_poll_created(instance))


@receiver(post_save, sender=Vote)
def handle_vote_submitted(sender, instance, created, **kwargs):
    """Handle vote submission."""
    if created:
        poll = instance.poll
        
        # Skip automatic processing for location confirmation polls
        # These are handled by custom logic in the views
        if poll.poll_type == 'location_confirmation':
            print(f"📍 Vote submitted for location confirmation poll {poll.id} - skipping automatic processing")
            return
        
        # Only handle price offer polls automatically
        if poll.poll_type == 'price_offer':
            # Check if poll is complete and handle accordingly
            total_votes = poll.votes.count()
            total_farmers = poll.deal_group.products.count()
            
            # If all farmers have voted, process the result
            if total_votes >= total_farmers:
                accept_votes = poll.votes.filter(choice='ACCEPT').count()
                reject_votes = poll.votes.filter(choice='REJECT').count()
                
                if accept_votes > reject_votes:
                    poll.result = 'ACCEPTED'
                    poll.is_active = False
                    poll.save()
                    
                    # Note: Deal creation and status updates are now handled in the views
                    # This prevents conflicts with our custom logic
                    print(f"💰 Price offer poll {poll.id} accepted - status updated to ACCEPTED")
                else:
                    poll.result = 'REJECTED'
                    poll.is_active = False
                    poll.save()
                    print(f"❌ Price offer poll {poll.id} rejected - status updated to REJECTED")


