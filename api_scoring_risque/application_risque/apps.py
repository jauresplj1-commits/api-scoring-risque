"""
Configuration de l'application de scoring de risque
"""

from django.apps import AppConfig


class ApplicationRisqueConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'application_risque'

    def ready(self):

        """
        Point d'initialisation pour les signaux ou autres configurations
        """

        import application_risque.signals