"""
Vues Django REST Framework pour l'API de scoring de risque
"""

from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
import json

from .models import Client, HistoriqueFinancier, DemandeCredit, ScoreRisque
from .serializers import (
    ClientSerializer, HistoriqueFinancierSerializer,
    DemandeCreditSerializer, ScoreRisqueSerializer,
    CalculScoreSerializer, SimulationCreditSerializer,
    ExplicationScoreSerializer, DonneesModeleSerializer
)
from gestion_modeles.gestionnaire_modele import obtenir_gestionnaire_modele


class ClientViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des clients
    """

    queryset = Client.objects.all().order_by('-date_creation')
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get'])
    def demandes(self, request, pk=None):
        """Retourne toutes les demandes de crédit d'un client"""
        client = self.get_object()
        demandes = client.demandes_credit.all().order_by('-date_demande')
        serializer = DemandeCreditSerializer(demandes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def historique(self, request, pk=None):
        """Retourne l'historique financier d'un client"""
        client = self.get_object()
        try:
            historique = client.historique_financier
            serializer = HistoriqueFinancierSerializer(historique)
            return Response(serializer.data)
        except HistoriqueFinancier.DoesNotExist:
            return Response(
                {'detail': 'Historique financier non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def calculer_score_rapide(self, request, pk=None):
        """
        Calcule un score rapide pour le client
        (utilise les données existantes pour une prédiction rapide)
        """
        client = self.get_object()
        historique = client.historique_financier

        # Préparer les données pour le modèle
        donnees_client = {
            'age': client.age,
            'profession': client.profession,
            'anciennete_emploi': client.anciennete_emploi,
            'revenu_mensuel': float(client.revenu_mensuel),
            'dette_totale': float(historique.dette_totale()),
            'defauts_paiement': historique.defauts_paiement,
            'nombre_enfants': client.nombre_enfants
        }

        # Obtenir le gestionnaire de modèle
        gestionnaire = obtenir_gestionnaire_modele()

        # Calculer le score
        resultat = gestionnaire.calculer_score_risque(donnees_client)

        return Response({
            'client': ClientSerializer(client).data,
            'score_risque': resultat['score_risque'],
            'categorie': resultat['categorie_risque'],
            'recommandation': resultat['recommandation'],
            'facteurs_positifs': resultat.get('facteurs_positifs', []),
            'facteurs_negatifs': resultat.get('facteurs_negatifs', []),
            'metadonnees': resultat.get('metadonnees', {})
        })


class HistoriqueFinancierViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des historiques financiers
    """

    queryset = HistoriqueFinancier.objects.all().order_by('-date_creation')
    serializer_class = HistoriqueFinancierSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filtre les historiques par client si un client_id est fourni"""
        queryset = super().get_queryset()
        client_id = self.request.query_params.get('client_id')

        if client_id:
            queryset = queryset.filter(client_id=client_id)

        return queryset


class DemandeCreditViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des demandes de crédit
    """

    queryset = DemandeCredit.objects.all().order_by('-date_demande')
    serializer_class = DemandeCreditSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filtre les demandes par client ou statut"""
        queryset = super().get_queryset()
        client_id = self.request.query_params.get('client_id')
        statut = self.request.query_params.get('statut')

        if client_id:
            queryset = queryset.filter(client_id=client_id)

        if statut:
            queryset = queryset.filter(statut=statut)

        return queryset

    @action(detail=True, methods=['post'])
    def soumettre(self, request, pk=None):
        """Soumet une demande pour évaluation"""
        demande = self.get_object()

        if demande.statut != 'en_attente':
            return Response(
                {'detail': 'Cette demande a déjà été traitée.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Changer le statut
        demande.statut = 'en_cours'
        demande.save()

        serializer = self.get_serializer(demande)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def score(self, request, pk=None):
        """Retourne le score de risque associé à cette demande"""
        demande = self.get_object()

        try:
            score = demande.score_risque
            serializer = ScoreRisqueSerializer(score)
            return Response(serializer.data)
        except ScoreRisque.DoesNotExist:
            return Response(
                {'detail': 'Aucun score de risque trouvé pour cette demande'},
                status=status.HTTP_404_NOT_FOUND
            )


class ScoreRisqueViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des scores de risque
    """

    queryset = ScoreRisque.objects.all().order_by('-date_calcul')
    serializer_class = ScoreRisqueSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filtre les scores par demande ou catégorie"""
        queryset = super().get_queryset()
        demande_id = self.request.query_params.get('demande_id')
        categorie = self.request.query_params.get('categorie')

        if demande_id:
            queryset = queryset.filter(demande_credit_id=demande_id)

        if categorie:
            queryset = queryset.filter(categorie_risque=categorie)

        return queryset


# Vues spécifiques pour les fonctionnalités principales
class CalculScoreRisqueView(APIView):
    """
    Endpoint pour calculer le score de risque d'une demande de crédit
    Correspond à: POST /api/risk-assessment/calculate/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Calcule le score de risque pour une demande de crédit

        Corps attendu:
        {
            "demande_credit_id": 1,
            "force_recalcul": false,
            "inclure_explications": true
        }
        """
        serializer = CalculScoreSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        demande_id = serializer.validated_data['demande_credit_id']
        force_recalcul = serializer.validated_data['force_recalcul']
        inclure_explications = serializer.validated_data['inclure_explications']

        # Récupérer la demande de crédit
        demande = get_object_or_404(DemandeCredit, id=demande_id)
        client = demande.client
        historique = client.historique_financier

        # Vérifier si un score existe déjà
        if hasattr(demande, 'score_risque') and not force_recalcul:
            score_existant = demande.score_risque
            serializer_score = ScoreRisqueSerializer(score_existant)
            return Response({
                'message': 'Un score existe déjà pour cette demande',
                'score': serializer_score.data
            }, status=status.HTTP_200_OK)

        # Préparer les données pour le modèle ML
        donnees_client = {
            'age': client.age,
            'profession': client.profession,
            'anciennete_emploi': client.anciennete_emploi,
            'revenu_mensuel': float(client.revenu_mensuel),
            'dette_totale': float(historique.dette_totale()),
            'defauts_paiement': historique.defauts_paiement,
            'nombre_enfants': client.nombre_enfants
        }

        # Ajouter des informations spécifiques à la demande
        donnees_client.update({
            'montant_credit': float(demande.montant_demande),
            'duree_credit': demande.duree_mois,
            'taux_interet': float(demande.taux_interet)
        })

        try:
            # Obtenir le gestionnaire de modèle
            gestionnaire = obtenir_gestionnaire_modele()

            # Calculer le score
            resultat = gestionnaire.calculer_score_risque(donnees_client)

            # Créer ou mettre à jour le score dans la base de données
            with transaction.atomic():
                # Supprimer l'ancien score s'il existe
                if hasattr(demande, 'score_risque'):
                    demande.score_risque.delete()

                # Créer le nouveau score
                score = ScoreRisque.objects.create(
                    demande_credit=demande,
                    score=resultat['score_risque'],
                    facteurs_positifs=json.dumps(resultat.get('facteurs_positifs', [])),
                    facteurs_negatifs=json.dumps(resultat.get('facteurs_negatifs', [])),
                    recommandation=resultat['recommandation'],
                    seuil_approbation=30.0,
                    seuil_rejet=70.0,
                    valeurs_shap=json.dumps(
                        resultat.get('explications_shap', {}) if inclure_explications else {}
                    ),
                    version_modele='v1.0'
                )

            # Mettre à jour le statut de la demande
            if resultat['recommandation'] == 'approbation':
                demande.statut = 'approuve'
            elif resultat['recommandation'] == 'rejet':
                demande.statut = 'rejete'
            else:
                demande.statut = 'en_cours'

            demande.save()

            # Préparer la réponse
            response_data = {
                'message': 'Score calculé avec succès',
                'demande': DemandeCreditSerializer(demande).data,
                'score': ScoreRisqueSerializer(score).data,
                'details_prediction': {
                    'score_risque': resultat['score_risque'],
                    'probabilite_defaut': resultat.get('probabilite_defaut'),
                    'categorie_risque': resultat['categorie_risque'],
                    'recommandation': resultat['recommandation']
                }
            }

            # Ajouter les explications si demandées
            if inclure_explications and 'explications_shap' in resultat:
                response_data['explications'] = resultat['explications_shap']

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'detail': f'Erreur lors du calcul du score: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RecommandationDemandeView(APIView):
    """
    Endpoint pour obtenir la recommandation d'une demande de crédit
    Correspond à: GET /api/loan-applications/{id}/recommendation/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        """
        Retourne la recommandation pour une demande de crédit

        Si aucun score n'existe, calcule d'abord le score
        """
        demande = get_object_or_404(DemandeCredit, id=pk)

        # Vérifier si un score existe
        if hasattr(demande, 'score_risque'):
            score = demande.score_risque
            recommandation = score.recommandation
            details_score = ScoreRisqueSerializer(score).data

        else:
            # Calculer le score d'abord
            # Pour simplifier, on utilise la vue de calcul
            calcul_view = CalculScoreRisqueView()
            fake_request = type('Request', (), {'data': {
                'demande_credit_id': pk,
                'force_recalcul': False,
                'inclure_explications': False
            }, 'user': request.user})()

            try:
                response = calcul_view.post(fake_request)
                if response.status_code != 201:
                    return Response(
                        {'detail': 'Impossible de calculer le score'},
                        status=response.status_code
                    )

                score_data = response.data['score']
                recommandation = score_data['recommandation']
                details_score = score_data

            except Exception as e:
                return Response(
                    {'detail': f'Erreur lors du calcul: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Préparer la réponse détaillée
        response_data = {
            'demande': {
                'id': demande.id,
                'client': str(demande.client),
                'montant': float(demande.montant_demande),
                'duree': demande.duree_mois,
                'statut': demande.statut
            },
            'recommandation': recommandation,
            'recommandation_display': dict(ScoreRisque.RECOMMANDATION).get(recommandation, ''),
            'score_details': details_score
        }

        # Ajouter une justification basée sur la recommandation
        justifications = {
            'approbation': 'Le profil du client et les conditions du crédit présentent un risque acceptable.',
            'rejet': 'Le niveau de risque est trop élevé pour accorder ce crédit.',
            'revision': 'Des informations supplémentaires ou des ajustements sont nécessaires.',
            'garantie': 'Le crédit peut être accordé avec des garanties supplémentaires.'
        }

        response_data['justification'] = justifications.get(recommandation, '')

        return Response(response_data)


class SimulationClientView(APIView):
    """
    Endpoint pour simuler différents scénarios de crédit pour un client
    Correspond à: POST /api/clients/{id}/simulate/
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        """
        Simule différents scénarios de crédit pour un client

        Corps attendu:
        {
            "scenarios": [
                {
                    "nom": "Scénario optimiste",
                    "description": "Augmentation du revenu",
                    "parametres": {
                        "revenu_mensuel": 7000,
                        "dette_totale": 5000
                    }
                },
                ...
            ]
        }
        """
        client = get_object_or_404(Client, id=pk)
        historique = client.historique_financier

        serializer = SimulationCreditSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        scenarios = serializer.validated_data['scenarios']

        # Données de base du client
        donnees_base = {
            'age': client.age,
            'profession': client.profession,
            'anciennete_emploi': client.anciennete_emploi,
            'revenu_mensuel': float(client.revenu_mensuel),
            'dette_totale': float(historique.dette_totale()),
            'defauts_paiement': historique.defauts_paiement,
            'nombre_enfants': client.nombre_enfants
        }

        try:
            # Obtenir le gestionnaire de modèle
            gestionnaire = obtenir_gestionnaire_modele()

            # Préparer les variations pour la simulation
            variations = []
            for scenario in scenarios:
                variations.append({
                    'nom': scenario.get('nom', 'Scénario'),
                    'description': scenario.get('description', ''),
                    'parametres': scenario['parametres']
                })

            # Exécuter les simulations
            resultats_simulation = gestionnaire.simuler_scenarios(donnees_base, variations)

            # Préparer la réponse
            response_data = {
                'client': ClientSerializer(client).data,
                'donnees_base': donnees_base,
                'simulations': []
            }

            for simulation in resultats_simulation:
                resultat_sim = {
                    'scenario_id': simulation['scenario_id'],
                    'scenario_nom': simulation['scenario_nom'],
                    'description': simulation['description'],
                    'parametres_modifies': simulation['parametres_modifies'],
                    'resultat': {
                        'score_risque': simulation['resultat']['score_risque'],
                        'categorie_risque': simulation['resultat']['categorie_risque'],
                        'recommandation': simulation['resultat']['recommandation'],
                        'facteurs_positifs': simulation['resultat'].get('facteurs_positifs', []),
                        'facteurs_negatifs': simulation['resultat'].get('facteurs_negatifs', [])
                    }
                }

                response_data['simulations'].append(resultat_sim)

            # Ajouter une analyse comparative
            if len(response_data['simulations']) > 0:
                scores = [s['resultat']['score_risque'] for s in response_data['simulations']]
                meilleur_scenario = min(enumerate(scores), key=lambda x: x[1])
                pire_scenario = max(enumerate(scores), key=lambda x: x[1])

                response_data['analyse_comparative'] = {
                    'meilleur_scenario': {
                        'index': meilleur_scenario[0],
                        'nom': response_data['simulations'][meilleur_scenario[0]]['scenario_nom'],
                        'score': meilleur_scenario[1]
                    },
                    'pire_scenario': {
                        'index': pire_scenario[0],
                        'nom': response_data['simulations'][pire_scenario[0]]['scenario_nom'],
                        'score': pire_scenario[1]
                    },
                    'ecart_scores': pire_scenario[1] - meilleur_scenario[1]
                }

            return Response(response_data)

        except Exception as e:
            return Response(
                {'detail': f'Erreur lors de la simulation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExplicationScoreView(APIView):
    """
    Endpoint pour expliquer les facteurs d'un score de risque
    Correspond à: GET /api/risk-assessment/{id}/explain/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        """
        Explique les facteurs contribuant à un score de risque

        Paramètres de requête:
        - format: 'texte', 'graphique', ou 'complet' (par défaut)
        """
        score = get_object_or_404(ScoreRisque, id=pk)

        # Déterminer le format demandé
        format_demande = request.query_params.get('format', 'complet')

        try:
            # Charger les explications SHAP si disponibles
            valeurs_shap = json.loads(score.valeurs_shap) if score.valeurs_shap else {}

            # Préparer la réponse de base
            response_data = {
                'score': ScoreRisqueSerializer(score).data,
                'demande_credit': DemandeCreditSerializer(score.demande_credit).data,
                'client': ClientSerializer(score.demande_credit.client).data
            }

            # Si des valeurs SHAP sont disponibles, les inclure
            if valeurs_shap and format_demande in ['graphique', 'complet']:
                response_data['explications_shap'] = valeurs_shap

                # Ajouter un résumé des facteurs clés
                if 'facteurs_positifs_detailles' in valeurs_shap:
                    facteurs_positifs = valeurs_shap['facteurs_positifs_detailles']
                    facteurs_negatifs = valeurs_shap.get('facteurs_negatifs_detailles', [])

                    # Trier par impact
                    facteurs_positifs_tries = sorted(
                        facteurs_positifs,
                        key=lambda x: x.get('impact', 0),
                        reverse=True
                    )[:5]

                    facteurs_negatifs_tries = sorted(
                        facteurs_negatifs,
                        key=lambda x: x.get('impact', 0),
                        reverse=True
                    )[:5]

                    response_data['facteurs_cles'] = {
                        'principaux_facteurs_positifs': facteurs_positifs_tries,
                        'principaux_facteurs_negatifs': facteurs_negatifs_tries
                    }

            # Si le format est 'texte', simplifier la réponse
            if format_demande == 'texte':
                response_data_simplifie = {
                    'score': score.score,
                    'categorie': score.get_categorie_risque_display(),
                    'recommandation': score.get_recommandation_display(),
                    'facteurs_positifs': json.loads(score.facteurs_positifs) if score.facteurs_positifs else [],
                    'facteurs_negatifs': json.loads(score.facteurs_negatifs) if score.facteurs_negatifs else [],
                    'explication_texte': self._generer_explication_texte(score, valeurs_shap)
                }
                return Response(response_data_simplifie)

            return Response(response_data)

        except Exception as e:
            return Response(
                {'detail': f'Erreur lors de la génération des explications: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _generer_explication_texte(self, score, valeurs_shap):
        """Génère une explication texte du score"""
        explication = f"Score de risque: {score.score:.1f}%\n"
        explication += f"Catégorie: {score.get_categorie_risque_display()}\n"
        explication += f"Recommandation: {score.get_recommandation_display()}\n\n"

        # Facteurs positifs
        facteurs_positifs = json.loads(score.facteurs_positifs) if score.facteurs_positifs else []
        if facteurs_positifs:
            explication += "Facteurs réduisant le risque:\n"
            for i, facteur in enumerate(facteurs_positifs[:3], 1):
                explication += f"  {i}. {facteur}\n"

        # Facteurs négatifs
        facteurs_negatifs = json.loads(score.facteurs_negatifs) if score.facteurs_negatifs else []
        if facteurs_negatifs:
            explication += "\nFacteurs augmentant le risque:\n"
            for i, facteur in enumerate(facteurs_negatifs[:3], 1):
                explication += f"  {i}. {facteur}\n"

        # Explications SHAP si disponibles
        if valeurs_shap and 'facteurs_positifs_detailles' in valeurs_shap:
            explication += "\nAnalyse détaillée (SHAP):\n"

            facteurs_shap_positifs = valeurs_shap['facteurs_positifs_detailles'][:2]
            facteurs_shap_negatifs = valeurs_shap.get('facteurs_negatifs_detailles', [])[:2]

            if facteurs_shap_positifs:
                explication += "Principaux contributeurs positifs:\n"
                for facteur in facteurs_shap_positifs:
                    impact = facteur.get('impact', 0)
                    description = facteur.get('description', '')
                    explication += f"  - {description} (impact: {impact:.4f})\n"

            if facteurs_shap_negatifs:
                explication += "\nPrincipaux contributeurs négatifs:\n"
                for facteur in facteurs_shap_negatifs:
                    impact = facteur.get('impact', 0)
                    description = facteur.get('description', '')
                    explication += f"  - {description} (impact: {impact:.4f})\n"

        return explication


# Vues supplémentaires
class PredictionDirecteView(APIView):
    """
    Endpoint pour faire une prédiction directe avec le modèle ML
    (Utile pour tester le modèle sans passer par la base de données)
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Fait une prédiction directe avec les données fournies

        Corps attendu:
        {
            "age": 45,
            "profession": "cadre",
            "anciennete_emploi": 60,
            "revenu_mensuel": 5000,
            "dette_totale": 10000,
            "defauts_paiement": 0,
            "nombre_enfants": 2
        }
        """
        serializer = DonneesModeleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        donnees_client = serializer.validated_data

        try:
            # Obtenir le gestionnaire de modèle
            gestionnaire = obtenir_gestionnaire_modele()

            # Faire la prédiction
            resultat = gestionnaire.calculer_score_risque(donnees_client)

            return Response({
                'donnees_entree': donnees_client,
                'resultat_prediction': resultat
            })

        except Exception as e:
            return Response(
                {'detail': f'Erreur lors de la prédiction: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StatistiquesModeleView(APIView):
    """
    Endpoint pour obtenir des statistiques sur le modèle ML
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Retourne les statistiques du modèle chargé"""
        try:
            # Obtenir le gestionnaire de modèle
            gestionnaire = obtenir_gestionnaire_modele()

            # Charger le modèle s'il n'est pas déjà chargé
            if not gestionnaire.modele_charge:
                gestionnaire.charger_modele()

            # Obtenir les statistiques
            stats = gestionnaire.obtenir_statistiques_modele()

            return Response({
                'modele': {
                    'charge': stats['charge'],
                    'derniere_mise_a_jour': stats['derniere_mise_a_jour'],
                    'type': stats['type_modele'],
                    'shap_disponible': stats['explicateur_shap_disponible']
                },
                'performance': stats.get('metrics', {}),
                'parametres': stats.get('parametres', {})
            })

        except Exception as e:
            return Response(
                {'detail': f'Erreur lors de la récupération des statistiques: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )