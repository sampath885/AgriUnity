# backend/chatbot/apps.py

from django.apps import AppConfig
import threading
import sys

class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbot'
    
    # A flag to ensure the watcher starts only once
    watcher_started = False

    def ready(self):
        """
        This method is called when the Django application is fully loaded.
        """
        # Start the watcher only when the Django development server is running,
        # not during scripts, management commands, or tests.
        if self.watcher_started:
            return
        if 'runserver' not in sys.argv:
            return

        if threading.main_thread() == threading.current_thread():
            print("--- Main application thread is ready. Starting watcher. ---")
            from . import watcher_service
            watcher_service.run_watcher_in_background()
            self.watcher_started = True