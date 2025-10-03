from django.urls import path
from .views import (
    BuyerContractListCreateView,
    BuyerContractDetailView,
    PublicContractsListView,
    CreateCommitmentView,
)

urlpatterns = [
    # Buyer endpoints
    path('buyer/contracts/', BuyerContractListCreateView.as_view(), name='buyer-contracts'),
    path('buyer/contracts/<int:pk>/', BuyerContractDetailView.as_view(), name='buyer-contract-detail'),

    # Farmer endpoints
    path('public-contracts/', PublicContractsListView.as_view(), name='public-contracts'),
    path('commitments/', CreateCommitmentView.as_view(), name='create-commitment'),
]


