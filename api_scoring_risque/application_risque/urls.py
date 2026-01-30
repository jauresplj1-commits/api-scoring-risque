"""
URLs de l'application de scoring de risque
"""

from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # Authentification
    path('token/', TokenObtainPairView.as_view(), name='obtenir_token'),
    path('token/refresh/', TokenRefreshView.as_view(), name='rafraichir_token'),

    # Inclure les autres URLs de l'API
    path('evaluation-risque/', include('application_risque.api_urls')),
]