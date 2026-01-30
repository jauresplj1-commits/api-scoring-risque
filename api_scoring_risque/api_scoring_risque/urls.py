"""
URL configuration for api_scoring_risque project.
"""

"""
URLs principales de l'API de Scoring de Risque
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Vue de documentation Swagger
vue_schema = get_schema_view(
    openapi.Info(
        title="API de Scoring de Risque d'Insolvabilité",
        default_version='v1',
        description="API pour l'évaluation du risque d'insolvabilité des clients",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="Licence MIT"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# Définition des URLs
urlpatterns = [
    # Administration
    path('admin/', admin.site.urls),

    # Documentation API
    path('documentation/', vue_schema.with_ui('swagger', cache_timeout=0), name='documentation-swagger'),
    path('redoc/', vue_schema.with_ui('redoc', cache_timeout=0), name='documentation-redoc'),

    # API
    path('api/', include('application_risque.urls')),
]
