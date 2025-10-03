import time
import random
from django.utils import timezone
from products.models import ProductListing


def grade_listing_image(listing_id: int, image_name: str = None):
    """
    Simulate async grading of a product listing image.
    In production, this would be a Celery task calling a CV service.
    """
    try:
        listing = ProductListing.objects.get(id=listing_id)
        
        # Simulate processing time
        time.sleep(2)
        
        # Simulate AI grading based on image name or random
        if image_name and 'good' in image_name.lower():
            grade = 'FAQ'
            confidence = random.uniform(0.85, 0.95)
        elif image_name and 'excellent' in image_name.lower():
            grade = 'Ref grade-1'
            confidence = random.uniform(0.90, 0.98)
        else:
            # Random grade for demo using grades from BIG_DATA.csv
            grades = ['FAQ', 'Medium', 'Large', 'Local', 'Non-FAQ', 'Ref grade-1', 'Ref grade-2']
            grade = random.choice(grades)
            confidence = random.uniform(0.70, 0.90)
        
        # Update listing with grading results
        listing.grade = grade
        listing.grade_confidence = confidence
        listing.grading_status = ProductListing.GradingStatusChoices.COMPLETED
        listing.grading_completed_at = timezone.now()
        listing.status = ProductListing.StatusChoices.AVAILABLE
        listing.save()
        
        print(f"Grading completed for listing {listing_id}: {grade} (confidence: {confidence:.2f})")
        
        # Trigger grouping attempt now that grading is complete
        from deals.utils import check_and_form_groups
        try:
            check_and_form_groups(listing)
        except Exception as e:
            print(f"Grouping failed after grading for listing {listing_id}: {e}")
            
    except ProductListing.DoesNotExist:
        print(f"Listing {listing_id} not found for grading")
    except Exception as e:
        print(f"Grading failed for listing {listing_id}: {e}")
        # Mark as failed
        try:
            listing = ProductListing.objects.get(id=listing_id)
            listing.grading_status = ProductListing.GradingStatusChoices.FAILED
            listing.save()
        except:
            pass
