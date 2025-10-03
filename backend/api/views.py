# backend/api/views.py
from django.http import JsonResponse
from .location_data import LOCATION_DATA # Import our new data
from locations.models import PinCode

# This view is for the health check, keep it
def health_check(request):
    return JsonResponse({"status": "ok", "message": "Backend is running!"})

# --- Add the new views below ---

def get_states(request):
    """Returns a list of all available states."""
    states = list(LOCATION_DATA.keys())
    return JsonResponse({"states": states})


def get_districts(request, state):
    """Returns a list of districts for a given state."""
    districts = LOCATION_DATA.get(state, [])
    return JsonResponse({"districts": districts})


def pin_lookup(request, code):
    """Quick PIN to district/state lookup for frontend convenience."""
    try:
        pc = PinCode.objects.get(code=str(code))
        return JsonResponse({
            'code': pc.code,
            'district': pc.district,
            'state': pc.state,
            'latitude': pc.latitude,
            'longitude': pc.longitude,
        })
    except PinCode.DoesNotExist:
        return JsonResponse({'error': 'PIN not found'}, status=404)