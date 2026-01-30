"""
URLs principales de l'API de Scoring de Risque
"""

from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Vue de documentation Swagger
vue_schema = get_schema_view(
    openapi.Info(
        title="API de Scoring de Risque d'Insolvabilité",
        default_version='v1',
        description="""
        ## API pour l'évaluation du risque d'insolvabilité des clients

        Cette API permet de:
        - Gérer les informations clients
        - Évaluer le risque de crédit avec des modèles de Machine Learning
        - Simuler différents scénarios de crédit
        - Expliquer les décisions de scoring avec SHAP

        ### Authentification
        L'API utilise JWT (JSON Web Tokens) pour l'authentification.
        1. Obtenez un token avec `/api/token/`
        2. Utilisez le token dans l'en-tête: `Authorization: Bearer <votre_token>`

        ### Endpoints Principaux
        1. **POST /api/evaluation-risque/calculer/** - Calculer un score de risque
        2. **GET /api/demandes-credit/{id}/recommandation/** - Obtenir une recommandation
        3. **POST /api/clients/{id}/simuler/** - Simuler des scénarios
        4. **GET /api/evaluation-risque/{id}/expliquer/** - Expliquer un score

        ### Modèles de Machine Learning
        - Utilise un Random Forest entraîné sur le German Credit Dataset
        - Intègre SHAP pour l'explicabilité des prédictions
        - Supporte les simulations de scénarios

        ### Sécurité
        - Toutes les données financières sont chiffrées
        - Journalisation complète des accès
        - Validation stricte des entrées
        """,
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="Licence MIT"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# URLs d'authentification JWT
urlpatterns_auth = [
    path('token/', TokenObtainPairView.as_view(), name='obtenir_token'),
    path('token/refresh/', TokenRefreshView.as_view(), name='rafraichir_token'),
]

# URLs de documentation
urlpatterns_docs = [
    re_path(r'^documentation(?P<format>\.json|\.yaml)$',
            vue_schema.without_ui(cache_timeout=0),
            name='schema-json'),
    path('documentation/', vue_schema.with_ui('swagger', cache_timeout=0),
         name='documentation-swagger'),
    path('redoc/', vue_schema.with_ui('redoc', cache_timeout=0),
         name='documentation-redoc'),
]

# URLs principales
urlpatterns = [
    # Administration
    path('admin/', admin.site.urls),

    # Documentation
    path('', include(urlpatterns_docs)),

    # API
    path('api/', include(urlpatterns_auth)),
    path('api/', include('application_risque.urls')),
]

# Handler pour les erreurs 404/500
handler404 = 'api_scoring_risque.views.handler_404'
handler500 = 'api_scoring_risque.views.handler_500'