"""
Gestionnaire principal pour l'utilisation des modèles de scoring de risque
"""

import os
import sys
import joblib
import json
import numpy as np
import pandas as pd
from django.conf import settings
from django.utils import timezone

from .entrainement import EntraineurModeleRisque
from .explicabilite_shap import ExplicateurSHAP


class GestionnaireModeleRisque:
    """
    Gestionnaire principal pour les opérations liées aux modèles de risque
    """

    _instance = None

    def __new__(cls):
        """Implémentation du pattern Singleton"""
        if cls._instance is None:
            cls._instance = super(GestionnaireModeleRisque, cls).__new__(cls)
            cls._instance.initialiser()
        return cls._instance

    def initialiser(self):
        """Initialise le gestionnaire de modèle"""
        self.modele_charge = False
        self.entraîneur = None
        self.explicateur = None
        self.derniere_mise_a_jour = None

        # Chemins
        self.dossier_modeles = getattr(settings, 'DOSSIER_MODELES', 'gestion_modeles/modeles')
        self.dossier_preprocesseurs = getattr(settings, 'DOSSIER_PREPROCESSEURS', 'gestion_modeles/preprocesseurs')

        # Créer les dossiers si nécessaire
        os.makedirs(self.dossier_modeles, exist_ok=True)
        os.makedirs(self.dossier_preprocesseurs, exist_ok=True)
        os.makedirs('media/shap', exist_ok=True)

    def charger_modele(self, forcer_entrainement=False):
        """
        Charge le modèle entraîné ou en entraîne un nouveau si nécessaire

        Args:
            forcer_entrainement: Si True, force un nouvel entraînement

        Returns:
            bool: True si le modèle a été chargé avec succès
        """
        chemin_modele = os.path.join(self.dossier_modeles, 'modele_risque_rf.pkl')

        # Vérifier si le modèle existe et si on ne force pas l'entraînement
        if os.path.exists(chemin_modele) and not forcer_entrainement:
            try:
                print("Chargement du modèle existant...")
                self.entraîneur = EntraineurModeleRisque()
                self.entraîneur.charger_modele(self.dossier_modeles)
                self.modele_charge = True
                self.derniere_mise_a_jour = timezone.now()
                print("Modèle chargé avec succès")

                # Initialiser l'explicateur SHAP
                self._initialiser_explicateur()

                return True

            except Exception as e:
                print(f"Erreur lors du chargement du modèle: {e}")
                print("Tentative d'entraînement d'un nouveau modèle...")
                return self.entrainer_modele()

        else:
            print("Aucun modèle trouvé ou entraînement forcé...")
            return self.entrainer_modele()

    def _initialiser_explicateur(self):
        """Initialise l'explicateur SHAP avec un échantillon de données"""
        if self.entraîneur and self.entraîneur.X_train is not None:
            # Prendre un échantillon pour SHAP
            X_sample = self.entraîneur.X_train.sample(
                min(100, len(self.entraîneur.X_train)),
                random_state=42
            )

            self.explicateur = ExplicateurSHAP(
                modele=self.entraîneur.modele,
                preparateur=self.entraîneur.preparateur
            )
            self.explicateur.initialiser_explicateur(X_sample)
            print("Explicateur SHAP initialisé")

    def entrainer_modele(self):
        """
        Entraîne un nouveau modèle

        Returns:
            bool: True si l'entraînement a réussi
        """
        try:
            print("Début de l'entraînement du modèle...")
            self.entraîneur = EntraineurModeleRisque(random_state=42)
            self.entraîneur.preparer_donnees()
            self.entraîneur.optimiser_hyperparametres()
            self.entraîneur.sauvegarder_modele(self.dossier_modeles)

            self.modele_charge = True
            self.derniere_mise_a_jour = timezone.now()

            # Initialiser l'explicateur SHAP
            self._initialiser_explicateur()

            print("Modèle entraîné et sauvegardé avec succès")
            return True

        except Exception as e:
            print(f"Erreur lors de l'entraînement du modèle: {e}")
            import traceback
            traceback.print_exc()
            return False

    def evaluer_modele(self):
        """
        Évalue le modèle chargé

        Returns:
            dict: Métriques d'évaluation
        """
        if not self.modele_charge or self.entraîneur is None:
            raise ValueError("Le modèle doit être chargé avant l'évaluation")

        print("Évaluation du modèle...")
        return self.entraîneur.evaluer_modele()

    def calculer_score_risque(self, donnees_client):
        """
        Calcule le score de risque pour un client

        Args:
            donnees_client: Dictionnaire avec les données du client

        Returns:
            dict: Résultats du scoring
        """
        if not self.modele_charge or self.entraîneur is None:
            self.charger_modele()

        # Convertir les données du format Django au format du modèle
        donnees_formatees = self._formater_donnees_client(donnees_client)

        # Calculer le score avec le modèle
        resultat_prediction = self.entraîneur.predire_risque(donnees_formatees)

        # Ajouter des explications SHAP si disponible
        if self.explicateur:
            try:
                X_client = self.entraîneur.preparer_donnees_client(donnees_formatees)
                explications_shap = self.explicateur.expliquer_prediction(X_client)

                # Fusionner les résultats
                resultat_prediction['explications_shap'] = {
                    'valeur_base': explications_shap['valeur_base'],
                    'contributions_total': explications_shap['contributions_total'],
                    'facteurs_positifs_detailles': explications_shap['facteurs_positifs'],
                    'facteurs_negatifs_detailles': explications_shap['facteurs_negatifs']
                }

                # Générer un graphique SHAP
                identifiant_unique = f"shap_{int(timezone.now().timestamp())}"
                chemin_graphique = f"media/shap/{identifiant_unique}.png"

                self.explicateur.generer_graphique_shap(X_client, chemin_graphique)
                resultat_prediction['graphique_shap'] = chemin_graphique

                # Sauvegarder les explications détaillées
                chemin_explications = f"media/shap/{identifiant_unique}.json"
                self.explicateur.sauvegarder_explications(explications_shap, chemin_explications)

            except Exception as e:
                print(f"Erreur lors de l'explication SHAP: {e}")
                resultat_prediction['explications_shap'] = None
                resultat_prediction['graphique_shap'] = None

        # Ajouter des métadonnées
        resultat_prediction['metadonnees'] = {
            'modele_version': 'v1.0',
            'date_calcul': timezone.now().isoformat(),
            'source_donnees': 'German Credit Dataset',
            'algorithme': 'Random Forest Classifier'
        }

        return resultat_prediction

    def _formater_donnees_client(self, donnees_client):
        """
        Formate les données d'un client Django au format du modèle ML

        Args:
            donnees_client: Dictionnaire avec les données Django

        Returns:
            dict: Données formatées pour le modèle
        """
        # Cette fonction doit mapper les données du modèle Django vers le format du dataset German Credit
        # C'est une simplification - dans un cas réel, le mapping serait plus complexe

        mapping_caracteristiques = {
            'age': 'age',
            'profession': 'emploi',
            'anciennete_emploi': 'anciennete_emploi',
            'revenu_mensuel': 'montant',
            'dette_totale': 'credits_existants',
            'defauts_paiement': 'historique_credit'
        }

        donnees_formatees = {}

        # Mapper les caractéristiques connues
        for champ_django, champ_modele in mapping_caracteristiques.items():
            if champ_django in donnees_client:
                donnees_formatees[champ_modele] = donnees_client[champ_django]

        # Remplir les caractéristiques manquantes avec des valeurs par défaut
        caracteristiques_requises = [
            'statut_compte', 'duree_mois', 'historique_credit', 'but', 'montant',
            'epargne', 'anciennete_emploi', 'taux_remboursement', 'etat_civil_sexe',
            'autres_debiteurs', 'residence_depuis', 'biens', 'age', 'autres_plans',
            'logement', 'credits_existants', 'emploi', 'personnes_charge',
            'telephone', 'travailleur_etranger'
        ]

        valeurs_par_defaut = {
            'statut_compte': 'A14',
            'duree_mois': 24,
            'historique_credit': 'A34' if donnees_client.get('defauts_paiement', 0) > 0 else 'A30',
            'but': 'A43',
            'montant': float(donnees_client.get('revenu_mensuel', 2000)) * 3,
            'epargne': 'A61',
            'anciennete_emploi': 'A73' if donnees_client.get('anciennete_emploi', 0) > 12 else 'A71',
            'taux_remboursement': 2,
            'etat_civil_sexe': 'A93',
            'autres_debiteurs': 'A101',
            'residence_depuis': 2,
            'biens': 'A121',
            'age': donnees_client.get('age', 35),
            'autres_plans': 'A143',
            'logement': 'A152',
            'credits_existants': 1 if donnees_client.get('dette_totale', 0) > 0 else 0,
            'emploi': 'A173',
            'personnes_charge': donnees_client.get('nombre_enfants', 0),
            'telephone': 'A191',
            'travailleur_etranger': 'A201'
        }

        # S'assurer que toutes les caractéristiques requises sont présentes
        for caract in caracteristiques_requises:
            if caract not in donnees_formatees:
                donnees_formatees[caract] = valeurs_par_defaut.get(caract, 0)

        return donnees_formatees

    def simuler_scenarios(self, donnees_client_base, variations):
        """
        Simule différents scénarios de crédit

        Args:
            donnees_client_base: Données de base du client
            variations: Liste de dictionnaires avec les variations à appliquer

        Returns:
            list: Résultats des différentes simulations
        """
        if not self.modele_charge:
            self.charger_modele()

        resultats = []

        for i, variation in enumerate(variations):
            # Appliquer la variation aux données de base
            donnees_simulation = donnees_client_base.copy()
            donnees_simulation.update(variation['parametres'])

            # Calculer le score
            resultat = self.calculer_score_risque(donnees_simulation)

            # Ajouter des informations sur la simulation
            resultat_simulation = {
                'scenario_id': i + 1,
                'scenario_nom': variation.get('nom', f'Scénario {i + 1}'),
                'description': variation.get('description', ''),
                'parametres_modifies': list(variation['parametres'].keys()),
                'resultat': resultat
            }

            resultats.append(resultat_simulation)

        return resultats

    def obtenir_statistiques_modele(self):
        """
        Retourne des statistiques sur le modèle chargé

        Returns:
            dict: Statistiques du modèle
        """
        if not self.modele_charge:
            raise ValueError("Le modèle doit être chargé")

        # Charger les métriques sauvegardées
        chemin_metrics = os.path.join(self.dossier_modeles, 'metrics_modele.json')
        chemin_params = os.path.join(self.dossier_modeles, 'parametres_modele.json')

        statistiques = {
            'charge': self.modele_charge,
            'derniere_mise_a_jour': self.derniere_mise_a_jour.isoformat() if self.derniere_mise_a_jour else None,
            'type_modele': 'Random Forest Classifier',
            'explicateur_shap_disponible': self.explicateur is not None
        }

        if os.path.exists(chemin_metrics):
            with open(chemin_metrics, 'r') as f:
                statistiques['metrics'] = json.load(f)

        if os.path.exists(chemin_params):
            with open(chemin_params, 'r') as f:
                statistiques['parametres'] = json.load(f)

        return statistiques

    def nettoyer_fichiers_temporaires(self):
        """
        Nettoie les fichiers temporaires et anciens graphiques SHAP
        """
        import glob
        import os
        from datetime import datetime, timedelta

        # Supprimer les graphiques SHAP de plus de 7 jours
        dossier_shap = 'media/shap'
        if os.path.exists(dossier_shap):
            fichiers_shap = glob.glob(os.path.join(dossier_shap, '*.png')) + \
                            glob.glob(os.path.join(dossier_shap, '*.json'))

            date_limite = datetime.now() - timedelta(days=7)

            for fichier in fichiers_shap:
                date_modification = datetime.fromtimestamp(os.path.getmtime(fichier))
                if date_modification < date_limite:
                    os.remove(fichier)
                    print(f"Fichier supprimé: {fichier}")


# Fonction utilitaire pour obtenir le gestionnaire de modèle
def obtenir_gestionnaire_modele():
    """
    Retourne l'instance singleton du gestionnaire de modèle

    Returns:
        GestionnaireModeleRisque: Instance du gestionnaire
    """
    return GestionnaireModeleRisque()


# Test du gestionnaire de modèle
def tester_gestionnaire():
    """
    Teste le gestionnaire de modèle
    """
    print("=== Test du gestionnaire de modèle ===")

    # Obtenir le gestionnaire
    gestionnaire = obtenir_gestionnaire_modele()

    # Charger ou entraîner le modèle
    succes = gestionnaire.charger_modele()

    if not succes:
        print("Échec du chargement/entraînement du modèle")
        return None

    # Afficher les statistiques du modèle
    stats = gestionnaire.obtenir_statistiques_modele()
    print(f"\nStatistiques du modèle:")
    print(f"  Chargé: {stats['charge']}")
    print(f"  Dernière mise à jour: {stats['derniere_mise_a_jour']}")
    print(f"  Type: {stats['type_modele']}")
    print(f"  SHAP disponible: {stats['explicateur_shap_disponible']}")

    if 'metrics' in stats:
        print(f"  ROC-AUC: {stats['metrics'].get('roc_auc', 'N/A'):.4f}")

    # Tester avec des données d'exemple
    donnees_client_exemple = {
        'age': 45,
        'profession': 'cadre',
        'anciennete_emploi': 60,  # mois
        'revenu_mensuel': 5000.0,
        'dette_totale': 10000.0,
        'defauts_paiement': 0,
        'nombre_enfants': 2
    }

    print(f"\nCalcul du score pour un client d'exemple...")
    resultat = gestionnaire.calculer_score_risque(donnees_client_exemple)

    print(f"\nRésultat du scoring:")
    print(f"  Score de risque: {resultat['score_risque']:.2f}%")
    print(f"  Catégorie: {resultat['categorie_risque']}")
    print(f"  Recommandation: {resultat['recommandation']}")

    # Tester les simulations
    print(f"\nTest des simulations de scénarios...")

    variations = [
        {
            'nom': 'Scénario optimiste',
            'description': 'Augmentation du revenu et réduction de la dette',
            'parametres': {
                'revenu_mensuel': 7000.0,
                'dette_totale': 5000.0
            }
        },
        {
            'nom': 'Scénario pessimiste',
            'description': 'Diminution du revenu et augmentation de la dette',
            'parametres': {
                'revenu_mensuel': 3000.0,
                'dette_totale': 20000.0,
                'defauts_paiement': 1
            }
        }
    ]

    simulations = gestionnaire.simuler_scenarios(donnees_client_exemple, variations)

    print(f"\nRésultats des simulations:")
    for simulation in simulations:
        print(f"  {simulation['scenario_nom']}: {simulation['resultat']['score_risque']:.2f}% "
              f"({simulation['resultat']['recommandation']})")

    # Nettoyer les fichiers temporaires
    print(f"\nNettoyage des fichiers temporaires...")
    gestionnaire.nettoyer_fichiers_temporaires()

    print("\n=== Test du gestionnaire terminé avec succès ===")

    return gestionnaire, resultat


if __name__ == "__main__":
    # Tester le gestionnaire
    gestionnaire, resultat = tester_gestionnaire()