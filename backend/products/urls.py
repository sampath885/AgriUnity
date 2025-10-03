# backend/products/urls.py
from django.urls import path
from .views import ProductListingListAPI, MyListingsView, CropListView, ProductListingUpdateView, CropListAPI

urlpatterns = [
    path('list-product/', ProductListingListAPI.as_view(), name='list-product'),
    path('my-listings/', MyListingsView.as_view(), name='my-listings'),
    path('listings/<int:pk>/', ProductListingUpdateView.as_view(), name='update-listing'),
    path('crops/', CropListView.as_view(), name='crop-list'),
    path('crops/public/', CropListAPI.as_view(), name='public-crop-list'),
]