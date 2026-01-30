"""
Module d'explicabilité utilisant SHAP pour expliquer les prédictions du modèle
"""

import shap
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
import joblib
from django.conf import settings
import warnings

warnings.filterwarnings('ignore')


class ExplicateurSHAP:
    """
    Classe pour expliquer les prédictions du modèle avec SHAP
    """

    def __init__(self, modele=None, preparateur=None):
        """
        Initialise l'explicateur SHAP

        Args:
            modele: Modèle Random Forest entraîné
            preparateur: Préparateur de données
        """
        self.modele = modele
        self.preparateur = preparateur
        self.explicateur = None
        self.valeurs_shap = None

    def initialiser_explicateur(self, X_echantillon=None):
        """
        Initialise l'explicateur SHAP

        Args:
            X_echantillon: Échantillon de données pour calculer les valeurs SHAP
        """
        if self.modele is None:
            raise ValueError("Le modèle doit être fourni pour initialiser SHAP.")

        print("Initialisation de l'explicateur SHAP...")

        # Utiliser TreeExplainer pour les Random Forests
        self.explicateur = shap.TreeExplainer(self.modele)

        # Calculer les valeurs SHAP sur un échantillon si fourni
        if X_echantillon is not None:
            print(f"Calcul des valeurs SHAP sur {len(X_echantillon)} échantillons...")
            self.valeurs_shap = self.explicateur.shap_values(X_echantillon)

        print("Explicateur SHAP initialisé avec succès")

    def expliquer_prediction(self, X_instance):
        """
        Explique une prédiction individuelle

        Args:
            X_instance: Instance unique à expliquer (DataFrame avec une seule ligne)

        Returns:
            dict: Explications SHAP pour cette instance
        """
        if self.explicateur is None:
            self.initialiser_explicateur()

        # Calculer les valeurs SHAP pour cette instance
        shap_values_instance = self.explicateur.shap_values(X_instance)

        # Pour un classifieur binaire, shap_values est une liste [valeurs_classe_0, valeurs_classe_1]
        if isinstance(shap_values_instance, list):
            # Utiliser les valeurs pour la classe 1 (défaut)
            shap_values = shap_values_instance[1][0]
        else:
            shap_values = shap_values_instance[0]

        # Valeur de base (expected value)
        valeur_base = self.explicateur.expected_value
        if isinstance(valeur_base, np.ndarray):
            valeur_base = valeur_base[1]  # Pour la classe 1

        # Prédiction du modèle
        prediction = self.modele.predict_proba(X_instance)[0, 1]

        # Préparer les explications
        caracteristiques = X_instance.columns.tolist()
        valeurs_caracteristiques = X_instance.values[0].tolist()
        contributions = shap_values.tolist()

        # Créer un mapping caractéristique -> contribution
        contributions_dict = {}
        for i, (caract, valeur, contrib) in enumerate(zip(caracteristiques, valeurs_caracteristiques, contributions)):
            contributions_dict[caract] = {
                'valeur': float(valeur),
                'contribution': float(contrib),
                'contribution_abs': abs(float(contrib))
            }

        # Trier par contribution absolue (impact)
        caracteristiques_triees = sorted(
            contributions_dict.items(),
            key=lambda x: x[1]['contribution_abs'],
            reverse=True
        )

        # Séparer les facteurs positifs et négatifs
        facteurs_positifs = []
        facteurs_negatifs = []

        for caract, info in caracteristiques_triees[:10]:  # Top 10
            contribution = info['contribution']

            # Simplification: contribution positive réduit le risque (log-odds)
            if contribution < 0:
                facteurs_positifs.append({
                    'caracteristique': caract,
                    'valeur': info['valeur'],
                    'impact': abs(contribution),
                    'description': self._obtenir_description_caracteristique(caract, info['valeur'])
                })
            else:
                facteurs_negatifs.append({
                    'caracteristique': caract,
                    'valeur': info['valeur'],
                    'impact': abs(contribution),
                    'description': self._obtenir_description_caracteristique(caract, info['valeur'])
                })

        explication = {
            'valeur_base': float(valeur_base),
            'prediction': float(prediction),
            'contributions_total': float(np.sum(shap_values)),
            'facteurs_positifs': facteurs_positifs,
            'facteurs_negatifs': facteurs_negatifs,
            'contributions_detaillees': {
                caract: info for caract, info in contributions_dict.items()
            }
        }

        return explication

    def _obtenir_description_caracteristique(self, nom_caracteristique, valeur):
        """
        Génère une description lisible pour une caractéristique

        Args:
            nom_caracteristique: Nom de la caractéristique
            valeur: Valeur normalisée

        Returns:
            str: Description lisible
        """
        descriptions = {
            'statut_compte': "Statut du compte courant",
            'duree_mois': "Durée du crédit en mois",
            'historique_credit': "Historique des crédits précédents",
            'but': "But du crédit",
            'montant': "Montant du crédit",
            'epargne': "Épargne/actifs",
            'anciennete_emploi': "Ancienneté dans l'emploi actuel",
            'taux_remboursement': "Taux d'épargne/remboursement",
            'etat_civil_sexe': "État civil et sexe",
            'autres_debiteurs': "Autres débiteurs/garants",
            'residence_depuis': "Durée de résidence",
            'biens': "Biens immobiliers",
            'age': "Âge",
            'autres_plans': "Autres plans d'épargne/prêts",
            'logement': "Type de logement",
            'credits_existants': "Crédits existants",
            'emploi': "Type d'emploi",
            'personnes_charge': "Personnes à charge",
            'telephone': "Téléphone",
            'travailleur_etranger': "Travailleur étranger"
        }

        description = descriptions.get(nom_caracteristique, nom_caracteristique)

        # Ajouter une interprétation basée sur la valeur
        if valeur > 1:
            interpretation = "valeur élevée"
        elif valeur < -1:
            interpretation = "valeur basse"
        else:
            interpretation = "valeur moyenne"

        return f"{description} ({interpretation})"

    def generer_graphique_shap(self, X_instance, chemin_sauvegarde=None):
        """
        Génère un graphique SHAP waterfall pour une instance

        Args:
            X_instance: Instance à expliquer
            chemin_sauvegarde: Chemin pour sauvegarder le graphique

        Returns:
            chemin_fichier: Chemin du fichier sauvegardé
        """
        if self.explicateur is None:
            self.initialiser_explicateur()

        # Calculer les valeurs SHAP
        shap_values_instance = self.explicateur.shap_values(X_instance)

        # Préparer pour le graphique waterfall
        if isinstance(shap_values_instance, list):
            shap_values_plot = shap_values_instance[1][0]
            expected_value = self.explicateur.expected_value[1]
        else:
            shap_values_plot = shap_values_instance[0]
            expected_value = self.explicateur.expected_value

        # Créer le graphique waterfall
        plt.figure(figsize=(10, 8))

        # Utiliser les noms de caractéristiques originaux si possible
        noms_caracteristiques = X_instance.columns.tolist()

        shap.waterfall_plot(
            shap.Explanation(
                values=shap_values_plot,
                base_values=expected_value,
                data=X_instance.values[0],
                feature_names=noms_caracteristiques
            ),
            max_display=15,
            show=False
        )

        plt.title("Explication SHAP de la prédiction de risque", fontsize=14, pad=20)
        plt.tight_layout()

        # Sauvegarder ou afficher
        if chemin_sauvegarde:
            plt.savefig(chemin_sauvegarde, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"Graphique SHAP sauvegardé: {chemin_sauvegarde}")
            return chemin_sauvegarde
        else:
            plt.show()
            return None

    def analyser_importance_globale(self, X_echantillon, chemin_sauvegarde=None):
        """
        Analyse l'importance globale des caractéristiques

        Args:
            X_echantillon: Échantillon de données
            chemin_sauvegarde: Chemin pour sauvegarder le graphique

        Returns:
            dict: Importance globale des caractéristiques
        """
        if self.explicateur is None:
            self.initialiser_explicateur(X_echantillon)

        # Calculer les valeurs SHAP pour l'échantillon
        shap_values = self.explicateur.shap_values(X_echantillon)

        if isinstance(shap_values, list):
            shap_values_global = shap_values[1]
        else:
            shap_values_global = shap_values

        # Importance moyenne absolue
        importance_absolue = np.abs(shap_values_global).mean(axis=0)

        # Créer un DataFrame avec les importances
        importance_df = pd.DataFrame({
            'caracteristique': X_echantillon.columns,
            'importance_moyenne': importance_absolue
        }).sort_values('importance_moyenne', ascending=False)

        # Générer un graphique d'importance globale
        plt.figure(figsize=(12, 8))

        # Bar plot des importances
        bars = plt.barh(
            importance_df['caracteristique'][:15][::-1],  # Top 15, inversé pour meilleure lisibilité
            importance_df['importance_moyenne'][:15][::-1]
        )

        plt.xlabel('Importance SHAP moyenne absolue', fontsize=12)
        plt.title('Importance globale des caractéristiques', fontsize=14, pad=20)
        plt.grid(axis='x', alpha=0.3)

        # Colorer les barres
        for bar in bars:
            bar.set_alpha(0.8)

        plt.tight_layout()

        # Sauvegarder ou afficher
        if chemin_sauvegarde:
            plt.savefig(chemin_sauvegarde, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"Graphique d'importance globale sauvegardé: {chemin_sauvegarde}")
        else:
            plt.show()

        # Retourner les importances
        return importance_df.to_dict('records')

    def sauvegarder_explications(self, explications, chemin_fichier):
        """
        Sauvegarde les explications SHAP dans un fichier JSON

        Args:
            explications: Explications à sauvegarder
            chemin_fichier: Chemin du fichier JSON
        """

        # Convertir les types numpy en types Python natifs
        def convertir_types(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convertir_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convertir_types(item) for item in obj]
            else:
                return obj

        explications_converties = convertir_types(explications)

        with open(chemin_fichier, 'w') as f:
            json.dump(explications_converties, f, indent=4)

        print(f"Explications sauvegardées: {chemin_fichier}")

    def charger_explications(self, chemin_fichier):
        """
        Charge les explications SHAP depuis un fichier JSON

        Args:
            chemin_fichier: Chemin du fichier JSON

        Returns:
            dict: Explications chargées
        """
        with open(chemin_fichier, 'r') as f:
            explications = json.load(f)

        print(f"Explications chargées: {chemin_fichier}")
        return explications


# Fonction utilitaire pour tester le module SHAP
def tester_explicabilite():
    """
    Teste le module d'explicabilité SHAP
    """
    print("=== Test du module d'explicabilité SHAP ===")

    # Charger le modèle et les données
    from gestion_modeles.entrainement import EntraineurModeleRisque

    entraîneur = EntraineurModeleRisque()

    try:
        entraîneur.charger_modele()
        print("Modèle chargé avec succès")
    except:
        print("Entraînement d'un nouveau modèle...")
        entraîneur.preparer_donnees()
        entraîneur.entrainer_modele_base()

    # Initialiser l'explicateur SHAP
    explicateur = ExplicateurSHAP(
        modele=entraîneur.modele,
        preparateur=entraîneur.preparateur
    )

    # Prendre un échantillon pour l'initialisation
    X_sample = entraîneur.X_train.sample(100, random_state=42)
    explicateur.initialiser_explicateur(X_sample)

    # Prendre une instance spécifique à expliquer
    instance_idx = 0
    X_instance = entraîneur.X_train.iloc[[instance_idx]]

    print(f"\nExplication de l'instance {instance_idx}:")
    print(f"Valeurs des caractéristiques:")
    for col, val in X_instance.iloc[0].items():
        print(f"  {col}: {val:.4f}")

    # Obtenir les explications
    explications = explicateur.expliquer_prediction(X_instance)

    print(f"\nRésumé des explications:")
    print(f"Valeur de base (expected value): {explications['valeur_base']:.4f}")
    print(f"Prédiction du modèle: {explications['prediction']:.4f}")
    print(f"Somme des contributions: {explications['contributions_total']:.4f}")

    print(f"\nTop 3 facteurs positifs (réduisent le risque):")
    for i, facteur in enumerate(explications['facteurs_positifs'][:3]):
        print(f"  {i + 1}. {facteur['caracteristique']}: {facteur['description']}")
        print(f"     Impact: {facteur['impact']:.4f}")

    print(f"\nTop 3 facteurs négatifs (augmentent le risque):")
    for i, facteur in enumerate(explications['facteurs_negatifs'][:3]):
        print(f"  {i + 1}. {facteur['caracteristique']}: {facteur['description']}")
        print(f"     Impact: {facteur['impact']:.4f}")

    # Générer un graphique
    print(f"\nGénération du graphique SHAP...")
    chemin_graphique = 'media/shap_waterfall.png'
    os.makedirs(os.path.dirname(chemin_graphique), exist_ok=True)
    explicateur.generer_graphique_shap(X_instance, chemin_graphique)

    # Analyser l'importance globale
    print(f"\nAnalyse de l'importance globale...")
    importance_globale = explicateur.analyser_importance_globale(
        X_sample,
        'media/shap_importance_globale.png'
    )

    print(f"\nTop 5 caractéristiques globalement importantes:")
    for i, item in enumerate(importance_globale[:5]):
        print(f"  {i + 1}. {item['caracteristique']}: {item['importance_moyenne']:.4f}")

    # Sauvegarder les explications
    explicateur.sauvegarder_explications(
        explications,
        'media/explications_shap.json'
    )

    print("\n=== Test SHAP terminé avec succès ===")

    return explicateur, explications


if __name__ == "__main__":
    # Tester le module SHAP
    explicateur, explications = tester_explicabilite()