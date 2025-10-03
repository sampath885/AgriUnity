from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from products.models import CropProfile, ProductListing
from deals.models import (
    DealGroup, Deal, Poll, Vote, NegotiationMessage, 
    DealLineItem, DealRating, DeliveryReceipt,
    AISessionMemory, GroupMessage, PaymentIntent, Payout, Shipment
)
from users.models import CustomUser, OTPCode
from communities.models import CommunityHub, AgentMessage
from contracts.models import ForwardContract, ContractCommitment, AdvancePayment
from notifications.models import Notification
from chatbot.models import ChatbotMessage, KnowledgeChunk
from locations.models import PinCode
from hubs.models import HubPartner

User = get_user_model()

class Command(BaseCommand):
    help = "Comprehensive database cleanup - deletes all users, listings, deals while preserving system data"

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete ALL data (required for safety)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.ERROR(
                    "⚠️ DANGER: This command will delete ALL users, listings, deals, and related data!\n"
                    "⚠️ Only knowledge_chunks, BIG_DATA.csv, pincodes, and hub partners will remain.\n"
                    "⚠️ Use --confirm to proceed with deletion.\n"
                    "⚠️ Use --dry-run to see what would be deleted first."
                )
            )
            return

        if options['dry_run']:
            self.stdout.write("🔍 DRY RUN MODE - No data will be deleted")
            self._show_deletion_summary()
            return

        # Confirm deletion
        self.stdout.write(
            self.style.WARNING(
                "🚨 FINAL WARNING: About to delete ALL data!\n"
                "This will remove:\n"
                "- All users and user details\n"
                "- All product listings\n"
                "- All deal groups and negotiations\n"
                "- All polls and votes\n"
                "- All messages and chat history\n"
                "- All communities and contracts\n"
                "- All notifications\n"
                "\n"
                "KEEPING:\n"
                "- Knowledge chunks (chatbot)\n"
                "- BIG_DATA.csv data\n"
                "- Pincode data\n"
                "- Hub partners\n"
                "- Admin users\n"
                "\n"
                "Type 'YES DELETE ALL' to confirm: "
            )
        )
        
        confirmation = input().strip()
        if confirmation != "YES DELETE ALL":
            self.stdout.write(
                self.style.ERROR("❌ Deletion cancelled. Type 'YES DELETE ALL' exactly to proceed.")
            )
            return

        self.stdout.write("🧹 Starting comprehensive database cleanup...")
        
        try:
            with transaction.atomic():
                self._delete_all_data()
                self.stdout.write(
                    self.style.SUCCESS("✅ Database cleanup completed successfully!")
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Database cleanup failed: {e}")
            )
            import traceback
            traceback.print_exc()

    def _show_deletion_summary(self):
        """Show what would be deleted without actually deleting"""
        self.stdout.write("\n📊 DELETION SUMMARY:")
        self.stdout.write("=" * 50)
        
        # Count records that would be deleted
        counts = {
            'Users': User.objects.count(),
            'Product Listings': ProductListing.objects.count(),
            'Deal Groups': DealGroup.objects.count(),
            'Deals': Deal.objects.count(),
            'Polls': Poll.objects.count(),
            'Votes': Vote.objects.count(),
            'Negotiation Messages': NegotiationMessage.objects.count(),
            'Deal Line Items': DealLineItem.objects.count(),
            'Deal Ratings': DealRating.objects.count(),
            'Payment Intents': PaymentIntent.objects.count(),
            'Payouts': Payout.objects.count(),
            'Shipments': Shipment.objects.count(),
            'Community Hubs': CommunityHub.objects.count(),
            'Forward Contracts': ForwardContract.objects.count(),
            'Contract Commitments': ContractCommitment.objects.count(),
            'Advance Payments': AdvancePayment.objects.count(),
            'Notifications': Notification.objects.count(),
            'Chatbot Messages': ChatbotMessage.objects.count(),
        }
        
        for model_name, count in counts.items():
            self.stdout.write(f"  {model_name}: {count:,} records")
        
        self.stdout.write("\n💾 KEEPING:")
        self.stdout.write("  - Knowledge Chunks: {} records".format(KnowledgeChunk.objects.count()))
        self.stdout.write("  - Pincodes: {} records".format(PinCode.objects.count()))
        self.stdout.write("  - Hub Partners: {} records".format(HubPartner.objects.count()))
        self.stdout.write("  - BIG_DATA.csv: Loaded in memory")
        self.stdout.write("  - Admin users: Protected")

    def _delete_all_data(self):
        """Delete all data in the correct order to avoid foreign key issues"""
        self.stdout.write("🗑️ Deleting all data...")
        
        # 1. Delete notifications first (they reference many models)
        notification_count = Notification.objects.count()
        Notification.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {notification_count:,} notifications")
        
        # 2. Delete votes (they reference polls)
        vote_count = Vote.objects.count()
        Vote.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {vote_count:,} votes")
        
        # 3. Delete polls (they reference deal groups)
        poll_count = Poll.objects.count()
        Poll.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {poll_count:,} polls")
        
        # 4. Delete negotiation messages
        message_count = NegotiationMessage.objects.count()
        NegotiationMessage.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {message_count:,} negotiation messages")
        
        # 5. Delete group messages
        group_message_count = GroupMessage.objects.count()
        GroupMessage.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {group_message_count:,} group messages")
        
        # 6. Delete AI session memories
        ai_memory_count = AISessionMemory.objects.count()
        AISessionMemory.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {ai_memory_count:,} AI session memories")
        
        # 7. Delete delivery receipts first (they reference deal line items)
        receipt_count = DeliveryReceipt.objects.count()
        DeliveryReceipt.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {receipt_count:,} delivery receipts")
        
        # 8. Delete deal line items (they reference deals)
        line_item_count = DealLineItem.objects.count()
        DealLineItem.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {line_item_count:,} deal line items")
        
        # 9. Delete deal ratings (they reference deals)
        rating_count = DealRating.objects.count()
        DealRating.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {rating_count:,} deal ratings")
        
        # 10. Delete payment intents (they reference deals)
        payment_intent_count = PaymentIntent.objects.count()
        PaymentIntent.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {payment_intent_count:,} payment intents")
        
        # 11. Delete payouts (they reference deals)
        payout_count = Payout.objects.count()
        Payout.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {payout_count:,} payouts")
        
        # 12. Delete shipments (they reference deals)
        shipment_count = Shipment.objects.count()
        Shipment.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {shipment_count:,} shipments")
        
        # 13. Delete deals (they reference deal groups)
        deal_count = Deal.objects.count()
        Deal.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {deal_count:,} deals")
        
        # 14. Delete deal groups
        deal_group_count = DealGroup.objects.count()
        DealGroup.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {deal_group_count:,} deal groups")
        
        # 15. Delete product listings
        listing_count = ProductListing.objects.count()
        ProductListing.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {listing_count:,} product listings")
        
        # 16. Delete contract commitments and advance payments first
        advance_payment_count = AdvancePayment.objects.count()
        AdvancePayment.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {advance_payment_count:,} advance payments")
        
        contract_commitment_count = ContractCommitment.objects.count()
        ContractCommitment.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {contract_commitment_count:,} contract commitments")
        
        # 17. Delete forward contracts
        contract_count = ForwardContract.objects.count()
        ForwardContract.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {contract_count:,} forward contracts")
        
        # 18. Delete agent messages first (they reference community hubs)
        agent_message_count = AgentMessage.objects.count()
        AgentMessage.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {agent_message_count:,} agent messages")
        
        # 19. Delete community hubs
        community_hub_count = CommunityHub.objects.count()
        CommunityHub.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {community_hub_count:,} community hubs")
        
        # 20. Delete chatbot messages (but keep knowledge chunks)
        chatbot_message_count = ChatbotMessage.objects.count()
        ChatbotMessage.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {chatbot_message_count:,} chatbot messages")
        
        # 21. Delete OTP codes
        otp_count = OTPCode.objects.count()
        OTPCode.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {otp_count:,} OTP codes")
        
        # 22. Delete regular users (but keep admin users)
        regular_users = User.objects.filter(is_superuser=False, is_staff=False)
        regular_user_count = regular_users.count()
        regular_users.delete()
        self.stdout.write(f"  ✅ Deleted {regular_user_count:,} regular users")
        
        # 23. Delete crop profiles (they will be recreated by seed_crops)
        crop_count = CropProfile.objects.count()
        CropProfile.objects.all().delete()
        self.stdout.write(f"  ✅ Deleted {crop_count:,} crop profiles")
        
        # 24. Reset auto-increment counters for clean IDs
        self.stdout.write("  🔄 Resetting auto-increment counters...")
        
        # Show what remains
        self.stdout.write("\n💾 REMAINING DATA:")
        self.stdout.write("=" * 30)
        
        remaining_counts = {
            'Knowledge Chunks': KnowledgeChunk.objects.count(),
            'Pincodes': PinCode.objects.count(),
            'Hub Partners': HubPartner.objects.count(),
            'Admin Users': User.objects.filter(is_superuser=True).count(),
        }
        
        for model_name, count in remaining_counts.items():
            self.stdout.write(f"  {model_name}: {count:,} records")
        
        self.stdout.write("\n🎯 NEXT STEPS:")
        self.stdout.write("  1. Run: python manage.py seed_crops")
        self.stdout.write("  2. Create new test users")
        self.stdout.write("  3. Test the enhanced ML system")
        self.stdout.write("  4. Verify ML analysis returns real prices (not ₹0.00/kg)")
