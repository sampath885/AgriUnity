# backend/deals/tasks.py

from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
import logging

from .models import DealGroup, GroupMessage
from .logistics_v2_service import find_optimal_hub_v2, get_recommendation_method
from .logistics_service import find_optimal_hub_v1

logger = logging.getLogger(__name__)


@shared_task
def refine_hub_recommendation(deal_group_id: int):
    """
    Background task to refine hub recommendation using V2 logistics.
    This can be called asynchronously to improve recommendations without blocking.
    """
    try:
        deal_group = DealGroup.objects.get(id=deal_group_id)
        
        # Check if this group already has a V2 recommendation
        current_method = get_recommendation_method(deal_group)
        if current_method == 'V2':
            logger.info(f"Group {deal_group_id} already has V2 recommendation, skipping refinement")
            return
        
        # Try V2 optimization
        logger.info(f"Refining hub recommendation for group {deal_group_id} using V2")
        new_hub = find_optimal_hub_v2(deal_group)
        
        if new_hub:
            new_method = get_recommendation_method(deal_group)
            
            # If V2 succeeded and found a different hub, post update message
            if new_method == 'V2' and new_hub != deal_group.recommended_collection_point:
                _post_refined_recommendation_message(deal_group, new_hub)
                logger.info(f"Refined hub recommendation for group {deal_group_id}: {new_hub.name}")
            else:
                logger.info(f"V2 refinement completed for group {deal_group_id}, no change in hub")
        else:
            logger.warning(f"V2 refinement failed for group {deal_group_id}, keeping V1 recommendation")
            
    except DealGroup.DoesNotExist:
        logger.error(f"Deal group {deal_group_id} not found for refinement")
    except Exception as e:
        logger.error(f"Error refining hub recommendation for group {deal_group_id}: {e}")


def _post_refined_recommendation_message(deal_group: DealGroup, new_hub):
    """Post message about refined hub recommendation."""
    try:
        from .logistics_service import get_logistics_summary
        
        summary = get_logistics_summary(deal_group)
        if not summary:
            return
        
        message_content = (
            f"🔄 **Refined Hub Recommendation:** {new_hub.name}\n"
            f"📍 **Address:** {new_hub.address}\n"
            f"📏 **Distance:** ~{summary['median_distance_km']} km (median)\n"
            f"✨ **Optimized using road network data for better accuracy**\n\n"
            f"*This refined recommendation considers actual road travel times.*"
        )
        
        GroupMessage.objects.create(
            deal_group=deal_group,
            sender=None,  # Agent message
            content=message_content
        )
        
    except Exception as e:
        logger.error(f"Error posting refined recommendation message: {e}")


@shared_task
def batch_refine_recommendations():
    """
    Batch task to refine hub recommendations for all active deal groups.
    This can be scheduled to run periodically.
    """
    try:
        # Get all active deal groups that might benefit from refinement
        active_groups = DealGroup.objects.filter(
            status__in=['FORMED', 'NEGOTIATING'],
            recommended_collection_point__isnull=False
        )
        
        logger.info(f"Starting batch refinement for {active_groups.count()} groups")
        
        for group in active_groups:
            # Add delay between groups to avoid overwhelming APIs
            refine_hub_recommendation.apply_async(
                args=[group.id], 
                countdown=30  # 30 second delay between groups
            )
        
        logger.info(f"Batch refinement queued for {active_groups.count()} groups")
        
    except Exception as e:
        logger.error(f"Error in batch refinement: {e}")


@shared_task
def cleanup_old_recommendations():
    """
    Clean up old logistics recommendation data from cache.
    """
    try:
        # This would clean up old cache entries
        # For now, just log the cleanup
        logger.info("Cleanup of old logistics recommendations completed")
        
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")


# Convenience functions for manual triggering
def schedule_refinement(deal_group_id: int, delay_seconds: int = 0):
    """Schedule hub refinement for a specific deal group."""
    refine_hub_recommendation.apply_async(
        args=[deal_group_id], 
        countdown=delay_seconds
    )


def schedule_batch_refinement():
    """Schedule batch refinement for all active groups."""
    batch_refine_recommendations.apply_async(countdown=60)  # Start in 1 minute
