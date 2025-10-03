# backend/products/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from .models import CropProfile, ProductListing
from .serializers import CropProfileSerializer, ProductListingSerializer

# Can be added to backend/products/views.py or a new permissions file
from core.permissions import IsAuthenticatedAndFarmer

class CropListAPI(APIView):
    """Get list of available crops for registration forms."""
    permission_classes = [AllowAny]
    
    def get(self, request, *args, **kwargs):
        try:
            crops = CropProfile.objects.all().order_by('name')
            serializer = CropProfileSerializer(crops, many=True)
            return Response({
                'crops': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': f'Failed to fetch crops: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductListingListAPI(generics.ListCreateAPIView):
    queryset = ProductListing.objects.all()
    serializer_class = ProductListingSerializer
    permission_classes = [permissions.IsAuthenticated, IsAuthenticatedAndFarmer]
    parser_classes = [MultiPartParser, FormParser]

    # Note: The AI grade is determined in the serializer create()
    # If you prefer doing it here, you can override perform_create and set serializer.validated_data

# A view for farmers to see their own listings
class MyListingsView(generics.ListAPIView):
    serializer_class = ProductListingSerializer
    permission_classes = [permissions.IsAuthenticated, IsAuthenticatedAndFarmer]

    def get_queryset(self):
        return ProductListing.objects.filter(farmer=self.request.user).order_by('-created_at')


class ProductListingUpdateView(generics.RetrieveUpdateAPIView):
    queryset = ProductListing.objects.all()
    serializer_class = ProductListingSerializer
    permission_classes = [permissions.IsAuthenticated, IsAuthenticatedAndFarmer]

    def get_queryset(self):
        # Farmer can edit only their own listings when not grouped/sold
        return ProductListing.objects.filter(
            farmer=self.request.user,
            status__in=[ProductListing.StatusChoices.AVAILABLE, ProductListing.StatusChoices.GRADING]
        )

# A view to get the list of supported crops for the frontend form
class CropListView(generics.ListAPIView):
    queryset = CropProfile.objects.all()
    serializer_class = CropProfileSerializer
    # Allow unauthenticated access so registration page can fetch crop options
    permission_classes = [permissions.AllowAny]