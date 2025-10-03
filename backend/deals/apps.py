from django.apps import AppConfig


class DealsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'deals'

    def ready(self):
        # Group formation is centrally handled in products.signals after grading
        # Avoid double-triggering by not importing deals.signals.
        pass