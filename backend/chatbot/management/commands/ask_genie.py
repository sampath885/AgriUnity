# backend/chatbot/management/commands/ask_genie.py

from django.core.management.base import BaseCommand
from chatbot.qa_logic import get_answer # Import our new function

class Command(BaseCommand):
    help = 'Asks a question to the AgriGenie chatbot.'

    def add_arguments(self, parser):
        parser.add_argument('query', type=str, help='The question to ask the chatbot.')
        parser.add_argument(
            '--role',
            type=str,
            default='Farmer',
            help='The role of the user asking the question (e.g., Farmer, Buyer).'
        )

    def handle(self, *args, **options):
        query = options['query']
        role = options['role']

        self.stdout.write(self.style.HTTP_INFO(f"Asking AgriGenie as a '{role}'..."))
        self.stdout.write(self.style.SQL_KEYWORD(f"Query: {query}"))
        self.stdout.write("="*30)

        # Call the main logic function
        answer = get_answer(query, role)

        self.stdout.write(self.style.SUCCESS(answer))