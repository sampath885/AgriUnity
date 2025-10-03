from rest_framework import generics, permissions
from .models import ForwardContract, ContractCommitment
from .serializers import ForwardContractSerializer, ContractCommitmentSerializer
from core.permissions import IsAuthenticatedAndFarmer, IsAuthenticatedAndVerifiedBuyer


# Buyer CRUD for their contracts
class BuyerContractListCreateView(generics.ListCreateAPIView):
    serializer_class = ForwardContractSerializer
    permission_classes = [IsAuthenticatedAndVerifiedBuyer]

    def get_queryset(self):
        return ForwardContract.objects.filter(buyer=self.request.user).order_by('-created_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        return context


class BuyerContractDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ForwardContractSerializer
    permission_classes = [IsAuthenticatedAndVerifiedBuyer]

    def get_queryset(self):
        return ForwardContract.objects.filter(buyer=self.request.user)


# Public contracts for farmers to see and commit to
class PublicContractsListView(generics.ListAPIView):
    serializer_class = ForwardContractSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ForwardContract.objects.filter(status=ForwardContract.StatusChoices.ACTIVE).order_by('-created_at')


class CreateCommitmentView(generics.CreateAPIView):
    serializer_class = ContractCommitmentSerializer
    permission_classes = [IsAuthenticatedAndFarmer]


class FarmerCommitmentsListView(generics.ListAPIView):
    serializer_class = ContractCommitmentSerializer
    permission_classes = [IsAuthenticatedAndFarmer]

    def get_queryset(self):
        return ContractCommitment.objects.filter(farmer=self.request.user).order_by('-created_at')


