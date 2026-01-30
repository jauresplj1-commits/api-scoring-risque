"""
Module d'audit pour tracer les actions sensibles
"""

import logging
import json
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser

# Logger d'audit
audit_logger = logging.getLogger('audit')


class AuditLogger:
    """
    Classe pour logger les actions d'audit
    """

    @staticmethod
    def log_action(user, action, object_type, object_id=None, details=None):
        """
        Log une action pour l'audit

        Args:
            user: Utilisateur effectuant l'action
            action: Action effectuée (create, read, update, delete, calculate, etc.)
            object_type: Type d'objet concerné
            object_id: ID de l'objet concerné
            details: Détails supplémentaires
        """
        # Préparer les informations utilisateur
        user_info = 'anonymous'
        if not isinstance(user, AnonymousUser) and user.is_authenticated:
            user_info = f"{user.username} ({user.id})"

        # Préparer les détails
        details_str = json.dumps(details) if details else ''

        # Log l'action
        audit_logger.info(
            '',
            extra={
                'user': user_info,
                'action': action,
                'object_type': object_type,
                'object_id': object_id,
                'details': details_str
            }
        )

    @staticmethod
    def log_risk_calculation(user, demande_id, score, details=None):
        """Log un calcul de risque"""
        AuditLogger.log_action(
            user=user,
            action='calculate_risk',
            object_type='DemandeCredit',
            object_id=demande_id,
            details={
                'score': score,
                'timestamp': timezone.now().isoformat(),
                **(details or {})
            }
        )

    @staticmethod
    def log_data_access(user, object_type, object_id, fields_accessed=None):
        """Log un accès aux données"""
        AuditLogger.log_action(
            user=user,
            action='access_data',
            object_type=object_type,
            object_id=object_id,
            details={
                'fields_accessed': fields_accessed,
                'timestamp': timezone.now().isoformat()
            }
        )

    @staticmethod
    def log_sensitive_operation(user, operation, object_type, object_id, justification=None):
        """Log une opération sensible"""
        AuditLogger.log_action(
            user=user,
            action=f'sensitive_{operation}',
            object_type=object_type,
            object_id=object_id,
            details={
                'justification': justification,
                'timestamp': timezone.now().isoformat()
            }
        )


# Middleware d'audit
class AuditMiddleware:
    """
    Middleware pour logger automatiquement les requêtes
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log la requête
        if request.user.is_authenticated and request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            # Extraire des informations de la requête
            path_info = request.path_info
            method = request.method

            # Ne pas logger les requêtes de token et autres endpoints non critiques
            if not any(endpoint in path_info for endpoint in ['/api/token/', '/admin/', '/documentation/']):
                AuditLogger.log_action(
                    user=request.user,
                    action=f'http_{method.lower()}',
                    object_type='HTTP_Request',
                    object_id=None,
                    details={
                        'path': path_info,
                        'method': method,
                        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                        'ip_address': self.get_client_ip(request)
                    }
                )

        response = self.get_response(request)
        return response

    @staticmethod
    def get_client_ip(request):
        """Récupère l'adresse IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip