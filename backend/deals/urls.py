# backend/deals/urls.py
from django.urls import path
from .views import AvailableGroupsView, SubmitOfferView
from .views import ActivePollsView, CastVoteView
from .views import NegotiationMessagesView, GroupMessagesView, GroupMembersView, GroupDetailView, MyDealGroupsView
from .views import (
    book_shipment_view, scan_receipt_view, release_payouts_view, rate_deal_view,
    my_deals_buyer_view, my_deals_farmer_view, deal_detail_view, deposit_escrow_view,
    group_deal_view, LogisticsInfoView, RecomputeHubView,
    AIAdvisorView, CropAdviceView, GroupAnalysisView, MarketAnalysisView,
    ActivePollView, VoteView, CollectionConfirmView, PaymentConfirmView, ShipmentBookView, NegotiationHistoryView,
    BuyerNegotiationChatView, HubConfirmationView, LocationConfirmationPollView, LocationVoteView, PollToGroupView, BuyerDealGroupsView, BuyerDealsView,
    MCPPricePredictionView, MCPMarketDataView, MCPHubOptimizationView, MCPPerformanceStatsView, MCPCacheManagementView
)

urlpatterns = [
    path('available-groups/', AvailableGroupsView.as_view(), name='available-groups'),
    path('groups/<int:group_id>/submit-offer/', SubmitOfferView.as_view(), name='submit-offer'),
    path('groups/<int:group_id>/messages/', NegotiationMessagesView.as_view(), name='negotiation-messages'),
    path('my-polls/', ActivePollsView.as_view(), name='my-polls'),
    path('location-polls/', LocationConfirmationPollView.as_view(), name='location-polls-list'),
    path('polls/<int:poll_id>/vote/', CastVoteView.as_view(), name='cast-vote'),

    path('groups/<int:group_id>/', GroupDetailView.as_view(), name='group-detail'),
    path('groups/<int:group_id>/chat/', GroupMessagesView.as_view(), name='group-chat'),
    path('groups/<int:group_id>/members/', GroupMembersView.as_view(), name='group-members'),
    path('my-groups/', MyDealGroupsView.as_view(), name='my-groups'),

    # Missing endpoints that frontend needs
    path('groups/<int:group_id>/active-poll/', ActivePollView.as_view(), name='active-poll'),
    path('polls/<int:poll_id>/group/', PollToGroupView.as_view(), name='poll-to-group'),
    path('groups/<int:group_id>/vote/', VoteView.as_view(), name='vote'),
    path('groups/<int:group_id>/collection/confirm/', CollectionConfirmView.as_view(), name='collection-confirm'),
    path('groups/<int:group_id>/payment/confirm/', PaymentConfirmView.as_view(), name='payment-confirm'),
    path('groups/<int:group_id>/shipment/book/', ShipmentBookView.as_view(), name='shipment-book'),
    path('groups/<int:group_id>/negotiation-history/', NegotiationHistoryView.as_view(), name='negotiation-history'),
    path('groups/<int:group_id>/buyer-chat/', BuyerNegotiationChatView.as_view(), name='buyer-negotiation-chat'),
    path('groups/<int:group_id>/confirm-hub/', HubConfirmationView.as_view(), name='confirm-hub'),
    path('groups/<int:group_id>/location-poll/', LocationConfirmationPollView.as_view(), name='location-poll'),
    path('location-polls/<int:poll_id>/vote/', LocationVoteView.as_view(), name='location-vote'),

    # Post-acceptance lifecycle
    path('deals/<int:deal_id>/shipments/book/', book_shipment_view, name='book-shipment'),
    path('deals/<int:deal_id>/escrow/deposit/', deposit_escrow_view, name='deposit-escrow'),
    path('receipts/scan/', scan_receipt_view, name='scan-receipt'),
    path('deals/<int:deal_id>/payouts/release/', release_payouts_view, name='release-payouts'),
    path('deals/<int:deal_id>/rate/', rate_deal_view, name='rate-deal'),
    path('deals/mine/buyer/', my_deals_buyer_view, name='my-deals-buyer'),
    path('deals/mine/farmer/', my_deals_farmer_view, name='my-deals-farmer'),
    path('buyer/deal-groups/', BuyerDealGroupsView.as_view(), name='buyer-deal-groups'),
    path('buyer/deals/', BuyerDealsView.as_view(), name='buyer-deals'),
    path('deals/<int:deal_id>/', deal_detail_view, name='deal-detail'),
    path('groups/<int:group_id>/deal/', group_deal_view, name='group-deal'),
    
    # Logistics endpoints
    path('groups/<int:group_id>/logistics/', LogisticsInfoView.as_view(), name='logistics-info'),
    path('groups/<int:group_id>/logistics/recompute/', RecomputeHubView.as_view(), name='recompute-hub'),
    
    # AI Advisor endpoints
    path('ai-advisor/', AIAdvisorView.as_view(), name='ai-advisor'),
    path('ai-advisor/crop-advice/', CropAdviceView.as_view(), name='crop-advice'),
    path('ai-advisor/group-analysis/', GroupAnalysisView.as_view(), name='group-analysis'),
    path('ai-advisor/market-analysis/', MarketAnalysisView.as_view(), name='market-analysis'),
    
    # MCP Performance Server endpoints
    path('mcp/price-prediction/', MCPPricePredictionView.as_view(), name='mcp-price-prediction'),
    path('mcp/market-data/', MCPMarketDataView.as_view(), name='mcp-market-data'),
    path('mcp/hub-optimization/', MCPHubOptimizationView.as_view(), name='mcp-hub-optimization'),
    path('mcp/performance-stats/', MCPPerformanceStatsView.as_view(), name='mcp-performance-stats'),
    path('mcp/cache-management/', MCPCacheManagementView.as_view(), name='mcp-cache-management'),
]