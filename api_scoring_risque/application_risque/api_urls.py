"""
URLs spécifiques à l'API de scoring de risque
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

# Créer un router pour les viewsets
router = DefaultRouter()
router.register(r'clients', api_views.ClientViewSet, basename='client')
router.register(r'historiques-financiers', api_views.HistoriqueFinancierViewSet, basename='historique-financier')
router.register(r'demandes-credit', api_views.DemandeCreditViewSet, basename='demande-credit')
router.register(r'scores-risque', api_views.ScoreRisqueViewSet, basename='score-risque')

# URLs spécifiques pour les fonctionnalités avancées
urlpatterns_api = [
    # Endpoints CRUD via ViewSets
    path('', include(router.urls)),

    # Endpoints fonctionnels spécifiques
    path('evaluation-risque/calculer/',
         api_views.CalculScoreRisqueView.as_view(),
         name='calculer-score-risque'),

    path('demandes-credit/<int:pk>/recommandation/',
         api_views.RecommandationDemandeView.as_view(),
         name='recommandation-demande'),

    path('clients/<int:pk>/simuler/',
         api_views.SimulationClientView.as_view(),
         name='simuler-client'),

    path('evaluation-risque/<int:pk>/expliquer/',
         api_views.ExplicationScoreView.as_view(),
         name='expliquer-score'),

    # Endpoint pour tester le modèle ML directement
    path('modele/predire-direct/',
         api_views.PredictionDirecteView.as_view(),
         name='predire-direct'),

    # Endpoint pour les statistiques du modèle
    path('modele/statistiques/',
         api_views.StatistiquesModeleView.as_view(),
         name='statistiques-modele'),
]

urlpatterns = urlpatterns_api