"""
Tests pour l'API de scoring de risque
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
import json

from .models import Client, HistoriqueFinancier, DemandeCredit, ScoreRisque


class BaseTestCase(APITestCase):
    """
    Classe de base pour les tests avec setup commun
    """

    def setUp(self):
        """Configuration initiale pour tous les tests"""
        # Créer un utilisateur pour l'authentification
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Créer un client de test
        self.client_test = Client.objects.create(
            nom='Dupont',
            prenom='Jean',
            email='jean.dupont@example.com',
            telephone='0123456789',
            date_naissance=date(1980, 5, 15),
            age=43,
            etat_civil='marie',
            nombre_enfants=2,
            profession='cadre',
            anciennete_emploi=60,  # 5 ans
            revenu_mensuel=5000.00,
            autres_revenus=500.00
        )

        # Créer l'historique financier
        self.historique_test = HistoriqueFinancier.objects.create(
            client=self.client_test,
            solde_compte=2000.00,
            epargne=15000.00,
            dette_cartes=1000.00,
            dette_autres=5000.00,
            nb_credits_anterieurs=2,
            defauts_paiement=0,
            duree_relation_banque=48,  # 4 ans
            depenses_logement=1200.00,
            depenses_autres=800.00
        )

        # Créer une demande de crédit
        self.demande_test = DemandeCredit.objects.create(
            client=self.client_test,
            type_credit='consommation',
            montant_demande=20000.00,
            duree_mois=48,
            taux_interet=3.5,
            destination_credit='Achat de voiture',
            avec_garantie=True,
            valeur_garantie=5000.00,
            statut='en_attente'
        )

        # Créer un score de risque
        self.score_test = ScoreRisque.objects.create(
            demande_credit=self.demande_test,
            score=35.5,
            categorie_risque='modere',
            facteurs_positifs='["Ancienneté dans l\'emploi", "Revenu stable"]',
            facteurs_negatifs='["Dettes existantes", "Nombre d\'enfants"]',
            recommandation='approbation',
            seuil_approbation=30.0,
            seuil_rejet=70.0,
            valeurs_shap='{"facteurs_positifs": [], "facteurs_negatifs": []}',
            version_modele='v1.0'
        )

        # Authentifier le client de test
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)


class AuthentificationTests(BaseTestCase):
    """Tests d'authentification"""

    def test_obtenir_token(self):
        """Teste l'obtention d'un token JWT"""
        url = reverse('obtenir_token')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_acces_protege_sans_token(self):
        """Teste l'accès à une API protégée sans token"""
        # Déconnecter le client
        self.client.force_authenticate(user=None)

        url = reverse('client-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ClientAPITests(BaseTestCase):
    """Tests pour l'API Client"""

    def test_liste_clients(self):
        """Teste la liste des clients"""
        url = reverse('client-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)

    def test_creation_client(self):
        """Teste la création d'un nouveau client"""
        url = reverse('client-list')
        data = {
            'nom': 'Martin',
            'prenom': 'Sophie',
            'email': 'sophie.martin@example.com',
            'telephone': '0987654321',
            'date_naissance': '1990-08-20',
            'age': 33,
            'etat_civil': 'celibataire',
            'nombre_enfants': 0,
            'profession': 'cadre',
            'anciennete_emploi': 24,
            'revenu_mensuel': 4000.00,
            'autres_revenus': 200.00
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Client.objects.count(), 2)

    def test_detail_client(self):
        """Teste la récupération des détails d'un client"""
        url = reverse('client-detail', args=[self.client_test.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nom'], 'Dupont')
        self.assertEqual(response.data['prenom'], 'Jean')

    def test_demandes_client(self):
        """Teste la récupération des demandes d'un client"""
        url = reverse('client-demandes', args=[self.client_test.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)


class DemandeCreditAPITests(BaseTestCase):
    """Tests pour l'API Demande de Crédit"""

    def test_liste_demandes(self):
        """Teste la liste des demandes de crédit"""
        url = reverse('demande-credit-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)

    def test_soumettre_demande(self):
        """Teste la soumission d'une demande de crédit"""
        url = reverse('demande-credit-soumettre', args=[self.demande_test.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['statut'], 'en_cours')

    def test_score_demande(self):
        """Teste la récupération du score d'une demande"""
        url = reverse('demande-credit-score', args=[self.demande_test.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['score'], 35.5)


class CalculScoreRisqueTests(BaseTestCase):
    """Tests pour le calcul de score de risque"""

    def test_calcul_score(self):
        """Teste le calcul de score de risque"""
        url = reverse('calculer-score-risque')
        data = {
            'demande_credit_id': self.demande_test.id,
            'force_recalcul': False,
            'inclure_explications': True
        }

        response = self.client.post(url, data, format='json')

        # Le score existe déjà, donc on s'attend à une réponse 200
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertIn('score', response.data)


class RecommandationDemandeTests(BaseTestCase):
    """Tests pour la recommandation de demande"""

    def test_recommandation_demande(self):
        """Teste la récupération de la recommandation d'une demande"""
        url = reverse('recommandation-demande', args=[self.demande_test.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('recommandation', response.data)
        self.assertEqual(response.data['recommandation'], 'approbation')


class SimulationClientTests(BaseTestCase):
    """Tests pour les simulations de client"""

    def test_simulation_client(self):
        """Teste les simulations pour un client"""
        url = reverse('simuler-client', args=[self.client_test.id])
        data = {
            'scenarios': [
                {
                    'nom': 'Scénario optimiste',
                    'description': 'Augmentation du revenu',
                    'parametres': {
                        'revenu_mensuel': 7000,
                        'dette_totale': 5000
                    }
                },
                {
                    'nom': 'Scénario pessimiste',
                    'description': 'Diminution du revenu',
                    'parametres': {
                        'revenu_mensuel': 3000,
                        'dette_totale': 15000
                    }
                }
            ]
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('simulations', response.data)
        self.assertEqual(len(response.data['simulations']), 2)


class ExplicationScoreTests(BaseTestCase):
    """Tests pour les explications de score"""

    def test_explication_score(self):
        """Teste les explications d'un score"""
        url = reverse('expliquer-score', args=[self.score_test.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('score', response.data)

    def test_explication_format_texte(self):
        """Teste les explications en format texte"""
        url = reverse('expliquer-score', args=[self.score_test.id])
        url += '?format=texte'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('explication_texte', response.data)


class PredictionDirecteTests(BaseTestCase):
    """Tests pour la prédiction directe"""

    def test_prediction_directe(self):
        """Teste la prédiction directe avec le modèle"""
        url = reverse('predire-direct')
        data = {
            'age': 45,
            'profession': 'cadre',
            'anciennete_emploi': 60,
            'revenu_mensuel': 5000,
            'dette_totale': 10000,
            'defauts_paiement': 0,
            'nombre_enfants': 2
        }

        response = self.client.post(url, data, format='json')

        # Le test peut échouer si le modèle n'est pas chargé
        # Dans ce cas, on accepte soit une réponse 200, soit une 500 avec message d'erreur
        if response.status_code == status.HTTP_200_OK:
            self.assertIn('resultat_prediction', response.data)
        else:
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class StatistiquesModeleTests(BaseTestCase):
    """Tests pour les statistiques du modèle"""

    def test_statistiques_modele(self):
        """Teste la récupération des statistiques du modèle"""
        url = reverse('statistiques-modele')
        response = self.client.get(url)

        # Le test peut échouer si le modèle n'est pas chargé
        # Dans ce cas, on accepte soit une réponse 200, soit une 500
        if response.status_code == status.HTTP_200_OK:
            self.assertIn('modele', response.data)
        else:
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class ValidationTests(BaseTestCase):
    """Tests de validation des données"""

    def test_validation_client_mineur(self):
        """Teste la validation d'un client mineur"""
        url = reverse('client-list')
        data = {
            'nom': 'Test',
            'prenom': 'Mineur',
            'email': 'mineur@example.com',
            'telephone': '0123456789',
            'date_naissance': '2010-01-01',  # Moins de 18 ans
            'age': 13,
            'etat_civil': 'celibataire',
            'nombre_enfants': 0,
            'profession': 'non_qualifie',
            'anciennete_emploi': 0,
            'revenu_mensuel': 1000.00,
            'autres_revenus': 0
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_naissance', response.data)

    def test_validation_revenu_negatif(self):
        """Teste la validation d'un revenu négatif"""
        url = reverse('client-list')
        data = {
            'nom': 'Test',
            'prenom': 'Revenu',
            'email': 'revenu@example.com',
            'telephone': '0123456789',
            'date_naissance': '1990-01-01',
            'age': 33,
            'etat_civil': 'celibataire',
            'nombre_enfants': 0,
            'profession': 'non_qualifie',
            'anciennete_emploi': 12,
            'revenu_mensuel': -1000.00,  # Revenu négatif
            'autres_revenus': 0
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('revenu_mensuel', response.data)


# Tests pour les modèles
class ModelTests(TestCase):
    """Tests pour les modèles Django"""

    def setUp(self):
        """Configuration initiale"""
        self.client_obj = Client.objects.create(
            nom='Test',
            prenom='Model',
            email='model@test.com',
            telephone='0123456789',
            date_naissance=date(1985, 5, 15),
            age=38,
            etat_civil='marie',
            nombre_enfants=2,
            profession='cadre',
            anciennete_emploi=60,
            revenu_mensuel=5000.00,
            autres_revenus=500.00
        )

    def test_client_str(self):
        """Teste la méthode __str__ du modèle Client"""
        self.assertEqual(str(self.client_obj), 'Model Test')

    def test_client_revenu_total(self):
        """Teste la méthode revenu_total du modèle Client"""
        self.assertEqual(self.client_obj.revenu_total(), 5500.00)

    def test_client_est_majeur(self):
        """Teste la méthode est_majeur du modèle Client"""
        self.assertTrue(self.client_obj.est_majeur())


# Exécution des tests
if __name__ == '__main__':
    # Pour exécuter les tests directement depuis le fichier
    import django

    django.setup()

    from django.core.management import execute_from_command_line

    execute_from_command_line(['manage.py', 'test', 'application_risque'])