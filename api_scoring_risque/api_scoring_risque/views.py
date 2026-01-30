"""
Vues personnalisées pour les erreurs et la documentation
"""

from django.shortcuts import render
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework import status
import json


def handler_404(request, exception):
    """Handler personnalisé pour les erreurs 404"""
    if request.path.startswith('/api/'):
        # Pour les API, retourner du JSON
        return Response(
            {
                'error': 'Not Found',
                'message': 'La ressource demandée n\'existe pas.',
                'path': request.path
            },
            status=status.HTTP_404_NOT_FOUND
        )

    # Pour les autres requêtes, utiliser le template par défaut
    return render(request, '404.html', status=404)


def handler_500(request):
    """Handler personnalisé pour les erreurs 500"""
    if request.path.startswith('/api/'):
        # Pour les API, retourner du JSON
        return Response(
            {
                'error': 'Internal Server Error',
                'message': 'Une erreur interne du serveur est survenue.',
                'path': request.path
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Pour les autres requêtes, utiliser le template par défaut
    return render(request, '500.html', status=500)


class DocumentationView:
    """
    Vue pour servir la documentation de l'API
    """

    @staticmethod
    def get_api_info(request):
        """Retourne les informations sur l'API"""
        info = {
            'name': 'API de Scoring de Risque d\'Insolvabilité',
            'version': '1.0.0',
            'description': 'API pour l\'évaluation du risque de crédit avec ML',
            'endpoints': {
                'authentication': {
                    'obtain_token': {
                        'method': 'POST',
                        'url': '/api/token/',
                        'description': 'Obtenir un token JWT'
                    },
                    'refresh_token': {
                        'method': 'POST',
                        'url': '/api/token/refresh/',
                        'description': 'Rafraîchir un token JWT'
                    }
                },
                'clients': {
                    'list': {
                        'method': 'GET',
                        'url': '/api/clients/',
                        'description': 'Lister tous les clients'
                    },
                    'create': {
                        'method': 'POST',
                        'url': '/api/clients/',
                        'description': 'Créer un nouveau client'
                    }
                },
                'risk_assessment': {
                    'calculate': {
                        'method': 'POST',
                        'url': '/api/evaluation-risque/calculer/',
                        'description': 'Calculer un score de risque'
                    },
                    'explain': {
                        'method': 'GET',
                        'url': '/api/evaluation-risque/{id}/expliquer/',
                        'description': 'Expliquer un score de risque'
                    }
                }
            },
            'authentication': 'JWT (Bearer token)',
            'rate_limiting': '100 requêtes par heure par utilisateur',
            'contact': 'contact@example.com'
        }

        return Response(info)