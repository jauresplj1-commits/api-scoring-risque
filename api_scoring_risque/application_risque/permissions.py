"""
Permissions personnalisées pour l'API de scoring de risque
"""

from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission qui permet l'écriture seulement aux administrateurs
    """

    def has_permission(self, request, view):
        # Les requêtes GET, HEAD, OPTIONS sont autorisées
        if request.method in permissions.SAFE_METHODS:
            return True

        # L'écriture n'est autorisée qu'aux administrateurs
        return request.user and request.user.is_staff


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission qui permet l'accès seulement au propriétaire ou aux administrateurs
    """

    def has_object_permission(self, request, view, obj):
        # Les administrateurs ont tous les droits
        if request.user and request.user.is_staff:
            return True

        # Vérifier si l'utilisateur est le propriétaire
        if hasattr(obj, 'client'):
            return obj.client.user == request.user if hasattr(obj.client, 'user') else False

        # Pour les objets Client, vérifier directement
        if isinstance(obj, type(view.queryset.model)) and hasattr(obj, 'user'):
            return obj.user == request.user

        return False


class CanCalculateRiskScore(permissions.BasePermission):
    """
    Permission qui vérifie si l'utilisateur peut calculer des scores de risque
    """

    def has_permission(self, request, view):
        # Vérifier si l'utilisateur a la permission spécifique
        return request.user.has_perm('application_risque.calculate_risk_score')


class CanViewFinancialHistory(permissions.BasePermission):
    """
    Permission qui vérifie si l'utilisateur peut voir les historiques financiers
    """

    def has_permission(self, request, view):
        # Les administrateurs peuvent tout voir
        if request.user and request.user.is_staff:
            return True

        # Vérifier les permissions spécifiques
        return request.user.has_perm('application_risque.view_financial_history')


# Permissions basées sur les rôles
class IsRiskAnalyst(permissions.BasePermission):
    """Permission pour les analystes de risque"""

    def has_permission(self, request, view):
        return request.user.groups.filter(name='Risk Analysts').exists() or request.user.is_staff


class IsCreditOfficer(permissions.BasePermission):
    """Permission pour les agents de crédit"""

    def has_permission(self, request, view):
        return request.user.groups.filter(name='Credit Officers').exists() or request.user.is_staff


class IsClient(permissions.BasePermission):
    """Permission pour les clients"""

    def has_permission(self, request, view):
        return request.user.groups.filter(name='Clients').exists()