from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .models import PinCode
import logging

logger = logging.getLogger(__name__)


class PincodeDetailView(APIView):
    """Get state and district information for a pincode."""
    permission_classes = [AllowAny]  # Allow public access for registration
    
    def get(self, request, pincode, *args, **kwargs):
        try:
            logger.info(f"Pincode lookup requested for: {pincode}")
            
            # Validate pincode format
            if not pincode.isdigit() or len(pincode) != 6:
                logger.warning(f"Invalid pincode format: {pincode}")
                return Response(
                    {"error": "Invalid pincode format. Must be 6 digits."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Find pincode in database
            pincode_obj = PinCode.objects.filter(code=pincode).first()
            
            if not pincode_obj:
                logger.warning(f"Pincode not found in database: {pincode}")
                return Response(
                    {"error": "Pincode not found in our database."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            logger.info(f"Pincode found: {pincode} -> {pincode_obj.district}, {pincode_obj.state}")
            
            # Return location data
            return Response({
                "pincode": pincode_obj.code,
                "state": pincode_obj.state,
                "district": pincode_obj.district,
                "latitude": pincode_obj.latitude,
                "longitude": pincode_obj.longitude
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in pincode lookup for {pincode}: {str(e)}")
            return Response(
                {"error": f"An error occurred: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
