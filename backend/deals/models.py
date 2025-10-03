# backend/deals/models.py
from django.db import models
from products.models import ProductListing # Important: Import from the products app
from users.models import CustomUser

class DealGroup(models.Model):
    class StatusChoices(models.TextChoices):
        FORMED = 'FORMED', 'Formed'
        NEGOTIATING = 'NEGOTIATING', 'Negotiating'
        SOLD = 'SOLD', 'Sold'
        EXPIRED = 'EXPIRED', 'Expired'

    # e.g., KADAPA-TOMATO-A-20240809
    group_id = models.CharField(max_length=100, unique=True) 
    products = models.ManyToManyField(ProductListing)
    total_quantity_kg = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.FORMED)
    created_at = models.DateTimeField(auto_now_add=True)
    # Recommended collection point suggested by logistics service
    recommended_collection_point = models.ForeignKey('hubs.HubPartner', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.group_id


class Deal(models.Model):
    """Represents a finalized, successful transaction."""
    group = models.OneToOneField(DealGroup, on_delete=models.PROTECT)
    buyer = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    final_price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    finalized_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Deal for {self.group.group_id}"


class DealLineItem(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='line_items')
    listing = models.ForeignKey('products.ProductListing', on_delete=models.PROTECT)
    quantity_kg = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity_kg}kg @ {self.unit_price} for {self.listing_id}"


class PaymentIntent(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSED = 'PROCESSED', 'Processed'
        FAILED = 'FAILED', 'Failed'

    deal = models.OneToOneField(Deal, on_delete=models.CASCADE, related_name='payment_intent')
    buyer = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    external_ref = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)


class Payout(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSED = 'PROCESSED', 'Processed'
        FAILED = 'FAILED', 'Failed'

    farmer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payouts')
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    external_ref = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)


class Shipment(models.Model):
    class Status(models.TextChoices):
        BOOKED = 'BOOKED', 'Booked'
        IN_TRANSIT = 'IN_TRANSIT', 'In Transit'
        DELIVERED = 'DELIVERED', 'Delivered'

    deal = models.OneToOneField(Deal, on_delete=models.CASCADE, related_name='shipment')
    hub = models.ForeignKey('hubs.HubPartner', null=True, blank=True, on_delete=models.SET_NULL)
    pickup_window_start = models.DateTimeField(null=True, blank=True)
    pickup_window_end = models.DateTimeField(null=True, blank=True)
    carrier = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BOOKED)
    created_at = models.DateTimeField(auto_now_add=True)


class DeliveryReceipt(models.Model):
    line_item = models.ForeignKey(DealLineItem, on_delete=models.CASCADE, related_name='receipts')
    received_qty_kg = models.PositiveIntegerField()
    receiver = models.CharField(max_length=100, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)


class DealRating(models.Model):
    deal = models.OneToOneField(Deal, on_delete=models.CASCADE, related_name='rating')
    buyer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Poll(models.Model):
    """Represents a voting session for the farmers in a group."""
    class PollType(models.TextChoices):
        PRICE_OFFER = 'price_offer', 'Price Offer'
        LOCATION_CONFIRMATION = 'location_confirmation', 'Location Confirmation'
    
    deal_group = models.ForeignKey(DealGroup, on_delete=models.CASCADE, related_name='polls')
    poll_type = models.CharField(max_length=25, choices=PollType.choices, default=PollType.PRICE_OFFER)
    buyer_offer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    agent_justification = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    offering_buyer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    # This field will store the outcome once the poll is closed
    result = models.CharField(max_length=20, blank=True, null=True) # e.g., 'ACCEPTED', 'REJECTED'
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Poll for {self.deal_group.group_id} at {self.buyer_offer_price}/kg"

class Vote(models.Model):
    """Represents a single farmer's vote on a poll."""
    class VoteChoice(models.TextChoices):
        ACCEPT = 'ACCEPT', 'Accept'
        REJECT = 'REJECT', 'Reject'
        YES = 'YES', 'Yes'
        NO = 'NO', 'No'

    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  # Changed from 'farmer' to 'voter' to handle both farmers and buyers
    choice = models.CharField(max_length=10, choices=VoteChoice.choices)
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A user can only vote once on a specific poll
        unique_together = ('poll', 'voter')

    def __str__(self):
        return f"{self.voter.username}'s vote on {self.poll}"


class NegotiationMessage(models.Model):
    class MessageType(models.TextChoices):
        OFFER = 'offer', 'Offer'
        COUNTER_OFFER = 'counter-offer', 'Counter Offer'
        TEXT = 'text', 'Text'

    deal_group = models.ForeignKey(DealGroup, on_delete=models.CASCADE, related_name='negotiation_messages')
    sender = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='sent_negotiation_messages')
    recipient = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='received_negotiation_messages')
    message_type = models.CharField(max_length=20, choices=MessageType.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        sender_name = self.sender.username if self.sender else 'Agent'
        return f"[{self.deal_group.group_id}] {sender_name}: {self.message_type}"


class NegotiationSession(models.Model):
    """Tracks buyer-specific negotiation anchors for a deal group."""
    deal_group = models.ForeignKey(DealGroup, on_delete=models.CASCADE, related_name='negotiation_sessions')
    buyer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='negotiation_sessions')
    last_counter_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    negotiation_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('deal_group', 'buyer')


class MarketPrice(models.Model):
    """Stores historical market price data from CSV for efficient bargaining"""
    crop_name = models.CharField(max_length=100, db_index=True)
    region = models.CharField(max_length=100, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(db_index=True)
    source = models.CharField(max_length=50, default='CSV_Import')  # CSV_Import, API, Manual
    quality_grade = models.CharField(max_length=20, blank=True, null=True)  # Grade A, B, C
    volume_kg = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['crop_name', 'region', 'date']),
            models.Index(fields=['crop_name', 'date']),
            models.Index(fields=['region', 'date']),
        ]
        ordering = ['-date', 'crop_name']
    
    def __str__(self):
        return f"{self.crop_name} - {self.region} - ₹{self.price}/kg - {self.date}"


class GroupMessage(models.Model):
    """Enhanced chat-like message within a deal group for farmers and AI agent communications."""
    class MessageType(models.TextChoices):
        FARMER_MESSAGE = 'farmer_message', 'Farmer Message'
        AI_AGENT_MESSAGE = 'ai_agent_message', 'AI Agent Message'
        SYSTEM_ANNOUNCEMENT = 'system_announcement', 'System Announcement'
        PRICE_EXPLANATION = 'price_explanation', 'Price Explanation'
        HUB_DETAILS = 'hub_details', 'Hub Details'
        MARKET_ANALYSIS = 'market_analysis', 'Market Analysis'
    
    class MessageCategory(models.TextChoices):
        GENERAL_CHAT = 'general_chat', 'General Chat'
        PRICING_DISCUSSION = 'pricing_discussion', 'Pricing Discussion'
        LOGISTICS_INFO = 'logistics_info', 'Logistics Information'
        MARKET_INSIGHTS = 'market_insights', 'Market Insights'
        DECISION_GUIDANCE = 'decision_guidance', 'Decision Guidance'
        TRUST_BUILDING = 'trust_building', 'Trust Building'
    
    deal_group = models.ForeignKey(DealGroup, on_delete=models.CASCADE, related_name='group_messages')
    sender = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='group_messages')
    message_type = models.CharField(max_length=20, choices=MessageType.choices, default=MessageType.FARMER_MESSAGE)
    category = models.CharField(max_length=20, choices=MessageCategory.choices, default=MessageCategory.GENERAL_CHAT)
    content = models.TextField()
    
    # AI Agent specific fields
    is_ai_agent = models.BooleanField(default=False)
    ai_response_to = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='ai_responses')
    session_id = models.CharField(max_length=100, blank=True, help_text="Session ID for conversation continuity")
    
    # Enhanced content fields for narrative stories
    narrative_story = models.TextField(blank=True, help_text="Detailed narrative explanation for farmers")
    market_data_summary = models.JSONField(default=dict, blank=True, help_text="Summary of market data used")
    hub_details = models.JSONField(default=dict, blank=True, help_text="Common hub and logistics details")
    trust_indicators = models.JSONField(default=dict, blank=True, help_text="Data points to build trust")
    
    # Message metadata
    is_pinned = models.BooleanField(default=False, help_text="Pin important messages")
    farmer_reactions = models.JSONField(default=dict, blank=True, help_text="Farmer reactions (👍, 👎, etc.)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['deal_group', 'session_id']),
            models.Index(fields=['deal_group', 'is_ai_agent']),
            models.Index(fields=['deal_group', 'category']),
        ]

    def __str__(self):
        sender_name = self.sender.username if self.sender else 'AI Agent'
        return f"[{self.deal_group.group_id}] {sender_name}: {self.content[:50]}"
    
    @property
    def sender_name(self):
        """Get sender name for display"""
        if self.is_ai_agent:
            return "AI Agent (Union Leader)"
        elif self.sender:
            return self.sender.username
        else:
            return "System"
    
    def get_narrative_story(self):
        """Get the narrative story or generate one if missing"""
        if self.narrative_story:
            return self.narrative_story
        elif self.is_ai_agent and self.content:
            # Generate narrative story from content
            return self._generate_narrative_story()
        return ""
    
    def _generate_narrative_story(self):
        """Generate narrative story from AI agent content"""
        # This will be implemented in the AI agent logic
        return self.content


class AISessionMemory(models.Model):
    """Tracks AI agent conversation memory and context for each deal group"""
    deal_group = models.ForeignKey(DealGroup, on_delete=models.CASCADE, related_name='ai_sessions')
    session_id = models.CharField(max_length=100, unique=True)
    
    # Conversation context
    conversation_history = models.JSONField(default=list, help_text="List of message IDs in conversation order")
    farmer_questions = models.JSONField(default=list, help_text="Questions asked by farmers")
    ai_responses = models.JSONField(default=list, help_text="AI agent responses given")
    
    # Market context
    current_market_analysis = models.JSONField(default=dict, help_text="Current market analysis for the group")
    pricing_decisions = models.JSONField(default=list, help_text="Pricing decisions made and explained")
    trust_building_moments = models.JSONField(default=list, help_text="Key moments that build trust")
    
    # Session metadata
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['deal_group', 'session_id']),
            models.Index(fields=['session_id', 'is_active']),
        ]
    
    def __str__(self):
        return f"AI Session {self.session_id} for {self.deal_group.group_id}"
    
    def add_message(self, message_id: int, message_type: str):
        """Add message to conversation history"""
        if message_type == 'farmer':
            self.farmer_questions.append(message_id)
        elif message_type == 'ai':
            self.ai_responses.append(message_id)
        
        self.conversation_history.append(message_id)
        self.save()
    
    def get_recent_context(self, limit: int = 10):
        """Get recent conversation context for AI agent"""
        return {
            'recent_messages': self.conversation_history[-limit:],
            'farmer_questions': self.farmer_questions[-limit:],
            'ai_responses': self.ai_responses[-limit:],
            'market_analysis': self.current_market_analysis,
            'pricing_decisions': self.pricing_decisions[-5:],  # Last 5 decisions
        }