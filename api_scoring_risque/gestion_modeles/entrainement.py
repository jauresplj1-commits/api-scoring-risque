"""
Entraînement du modèle Random Forest pour le scoring de risque
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.utils import class_weight
import joblib
import json
import os
import warnings

warnings.filterwarnings('ignore')

from .preparation_donnees import PreparateurDonnees


class EntraineurModeleRisque:
    """
    Classe pour entraîner et évaluer un modèle Random Forest
    """

    def __init__(self, random_state=42):
        """
        Initialise l'entraîneur de modèle

        Args:
            random_state: Seed pour la reproductibilité
        """
        self.random_state = random_state
        self.modele = None
        self.meilleurs_parametres = None
        self.scores_cv = None
        self.preparateur = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None

    def preparer_donnees(self, chemin_dataset=None):
        """
        Prépare les données pour l'entraînement

        Args:
            chemin_dataset: Chemin vers le dataset
        """
        print("Préparation des données...")
        self.preparateur = PreparateurDonnees(chemin_dataset)
        self.X_train, self.X_test, self.y_train, self.y_test = self.preparateur.preparer_pour_entrainement(
            random_state=self.random_state
        )

        print(f"Données préparées:")
        print(f"  - Train: {self.X_train.shape}")
        print(f"  - Test: {self.X_test.shape}")

        # Calculer les poids des classes pour gérer le déséquilibre
        classes = np.unique(self.y_train)
        poids_classes = class_weight.compute_class_weight(
            class_weight='balanced',
            classes=classes,
            y=self.y_train
        )
        self.poids_classes = dict(zip(classes, poids_classes))

        print(f"Poids des classes: {self.poids_classes}")

    def entrainer_modele_base(self):
        """
        Entraîne un modèle Random Forest avec les paramètres par défaut
        """
        print("\nEntraînement du modèle Random Forest (paramètres par défaut)...")

        # Créer et entraîner le modèle
        self.modele = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight=self.poids_classes,
            random_state=self.random_state,
            n_jobs=-1  # Utiliser tous les cœurs disponibles
        )

        self.modele.fit(self.X_train, self.y_train)

        # Évaluation
        self.evaluer_modele()

        return self.modele

    def optimiser_hyperparametres(self):
        """
        Optimise les hyperparamètres du modèle avec GridSearch
        """
        print("\nOptimisation des hyperparamètres avec GridSearchCV...")

        # Définir la grille des hyperparamètres
        grille_parametres = {
            'n_estimators': [50, 100, 200],
            'max_depth': [5, 10, 15, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'max_features': ['sqrt', 'log2']
        }

        # Créer le modèle de base
        modele_base = RandomForestClassifier(
            class_weight=self.poids_classes,
            random_state=self.random_state,
            n_jobs=-1
        )

        # Configuration de GridSearchCV
        recherche_grille = GridSearchCV(
            estimator=modele_base,
            param_grid=grille_parametres,
            cv=5,  # 5-fold cross-validation
            scoring='roc_auc',
            n_jobs=-1,
            verbose=1
        )

        # Exécuter la recherche
        recherche_grille.fit(self.X_train, self.y_train)

        # Stocker les résultats
        self.modele = recherche_grille.best_estimator_
        self.meilleurs_parametres = recherche_grille.best_params_
        self.scores_cv = recherche_grille.cv_results_

        print(f"\nMeilleurs paramètres trouvés:")
        for param, valeur in self.meilleurs_parametres.items():
            print(f"  {param}: {valeur}")

        print(f"Meilleur score (ROC-AUC): {recherche_grille.best_score_:.4f}")

        # Évaluation avec les meilleurs paramètres
        self.evaluer_modele()

        return self.modele

    def evaluer_modele(self):
        """
        Évalue le modèle sur les données de test
        """
        if self.modele is None:
            raise ValueError("Le modèle doit être entraîné avant l'évaluation.")

        print("\nÉvaluation du modèle sur les données de test:")

        # Prédictions
        y_pred = self.modele.predict(self.X_test)
        y_pred_proba = self.modele.predict_proba(self.X_test)[:, 1]

        # Métriques
        rapport_classification = classification_report(self.y_test, y_pred)
        matrice_confusion = confusion_matrix(self.y_test, y_pred)
        score_roc_auc = roc_auc_score(self.y_test, y_pred_proba)

        print("Rapport de classification:")
        print(rapport_classification)

        print("Matrice de confusion:")
        print(matrice_confusion)

        print(f"Score ROC-AUC: {score_roc_auc:.4f}")

        # Scores de cross-validation
        scores_cv = cross_val_score(
            self.modele,
            self.X_train,
            self.y_train,
            cv=5,
            scoring='roc_auc',
            n_jobs=-1
        )

        print(f"Scores de cross-validation (ROC-AUC):")
        print(f"  Scores individuels: {scores_cv}")
        print(f"  Moyenne: {scores_cv.mean():.4f}")
        print(f"  Écart-type: {scores_cv.std():.4f}")

        # Importance des caractéristiques
        importances = self.modele.feature_importances_
        indices = np.argsort(importances)[::-1]

        print("\nTop 10 des caractéristiques les plus importantes:")
        for i in range(min(10, len(importances))):
            idx = indices[i]
            print(f"  {i + 1}. {self.X_train.columns[idx]}: {importances[idx]:.4f}")

        self.metrics = {
            'classification_report': classification_report(self.y_test, y_pred, output_dict=True),
            'confusion_matrix': matrice_confusion.tolist(),
            'roc_auc': score_roc_auc,
            'cv_scores': scores_cv.tolist(),
            'cv_mean': scores_cv.mean(),
            'cv_std': scores_cv.std(),
            'feature_importances': {self.X_train.columns[i]: float(importances[i]) for i in indices}
        }

        return self.metrics

    def sauvegarder_modele(self, chemin_dossier='gestion_modeles/modeles'):
        """
        Sauvegarde le modèle entraîné

        Args:
            chemin_dossier: Dossier où sauvegarder le modèle
        """
        if self.modele is None:
            raise ValueError("Le modèle doit être entraîné avant de pouvoir être sauvegardé.")

        os.makedirs(chemin_dossier, exist_ok=True)

        # Chemin pour le modèle
        chemin_modele = os.path.join(chemin_dossier, 'modele_risque_rf.pkl')

        # Sauvegarder le modèle
        joblib.dump(self.modele, chemin_modele)
        print(f"Modèle sauvegardé: {chemin_modele}")

        # Sauvegarder les métriques
        chemin_metrics = os.path.join(chemin_dossier, 'metrics_modele.json')
        with open(chemin_metrics, 'w') as f:
            json.dump(self.metrics, f, indent=4)
        print(f"Métriques sauvegardées: {chemin_metrics}")

        # Sauvegarder les paramètres
        chemin_params = os.path.join(chemin_dossier, 'parametres_modele.json')
        parametres = {
            'meilleurs_parametres': self.meilleurs_parametres,
            'random_state': self.random_state,
            'features': list(self.X_train.columns),
            'poids_classes': {int(k): float(v) for k, v in self.poids_classes.items()}
        }
        with open(chemin_params, 'w') as f:
            json.dump(parametres, f, indent=4)
        print(f"Paramètres sauvegardés: {chemin_params}")

        # Sauvegarder également les préprocesseurs
        if self.preparateur:
            self.preparateur.sauvegarder_preprocesseurs()

    def charger_modele(self, chemin_dossier='gestion_modeles/modeles'):
        """
        Charge un modèle pré-entraîné

        Args:
            chemin_dossier: Dossier où charger le modèle
        """
        chemin_modele = os.path.join(chemin_dossier, 'modele_risque_rf.pkl')

        if not os.path.exists(chemin_modele):
            raise FileNotFoundError(f"Modèle non trouvé: {chemin_modele}")

        # Charger le modèle
        self.modele = joblib.load(chemin_modele)
        print(f"Modèle chargé: {chemin_modele}")

        # Charger les paramètres
        chemin_params = os.path.join(chemin_dossier, 'parametres_modele.json')
        if os.path.exists(chemin_params):
            with open(chemin_params, 'r') as f:
                parametres = json.load(f)
            self.meilleurs_parametres = parametres.get('meilleurs_parametres')
            self.random_state = parametres.get('random_state', 42)
            print("Paramètres du modèle chargés")

        # Charger les préprocesseurs
        self.preparateur = PreparateurDonnees()
        self.preparateur.charger_preprocesseurs()

        return self.modele

    def preparer_donnees_client(self, donnees_client):
        """
        Prépare les données d'un client pour la prédiction

        Args:
            donnees_client: Dictionnaire avec les données du client

        Returns:
            donnees_preparees: Données préparées pour le modèle
        """
        # Convertir en DataFrame
        df_client = pd.DataFrame([donnees_client])

        # Transformer avec les préprocesseurs
        if self.preparateur:
            df_transformees = self.preparateur.transformer_nouvelles_donnees(df_client)
        else:
            raise ValueError("Le préparateur de données n'est pas initialisé.")

        return df_transformees

    def predire_risque(self, donnees_client):
        """
        Prédit le risque pour un client

        Args:
            donnees_client: Dictionnaire avec les données du client

        Returns:
            dict: Résultats de la prédiction
        """
        if self.modele is None:
            raise ValueError("Le modèle doit être chargé ou entraîné avant la prédiction.")

        # Préparer les données
        X_client = self.preparer_donnees_client(donnees_client)

        # Faire la prédiction
        probabilite_defaut = self.modele.predict_proba(X_client)[0, 1]

        # Convertir en score de risque (0-100)
        score_risque = probabilite_defaut * 100

        # Déterminer la catégorie
        if score_risque < 25:
            categorie = 'faible'
        elif score_risque < 50:
            categorie = 'modere'
        elif score_risque < 75:
            categorie = 'eleve'
        else:
            categorie = 'tres_eleve'

        # Importance des caractéristiques pour cette prédiction
        importances = self.modele.feature_importances_

        # Préparer les facteurs contributifs
        facteurs_positifs = []
        facteurs_negatifs = []

        for idx, importance in enumerate(importances):
            nom_caracteristique = X_client.columns[idx]
            valeur = X_client.iloc[0, idx]

            # Simplification: considérer que les valeurs élevées des caractéristiques importantes
            # avec une importance positive sont négatives (augmentent le risque)
            if importance > 0.01:  # Seuil d'importance
                if valeur > 0.5:  # Valeur normalisée élevée
                    facteurs_negatifs.append(f"{nom_caracteristique}: valeur élevée")
                else:
                    facteurs_positifs.append(f"{nom_caracteristique}: valeur basse")

        resultat = {
            'score_risque': float(score_risque),
            'probabilite_defaut': float(probabilite_defaut),
            'categorie_risque': categorie,
            'facteurs_positifs': facteurs_positifs[:5],  # Top 5
            'facteurs_negatifs': facteurs_negatifs[:5],  # Top 5
            'recommandation': 'approbation' if score_risque < 30 else 'rejet' if score_risque > 70 else 'revision'
        }

        return resultat


# Fonction principale pour entraîner le modèle
def entrainer_modele_complet(sauvegarder=True):
    """
    Pipeline complet d'entraînement du modèle

    Args:
        sauvegarder: Si True, sauvegarde le modèle

    Returns:
        EntraineurModeleRisque: Entraîneur avec modèle entraîné
    """
    print("=== Pipeline d'entraînement du modèle de risque ===")

    # Initialiser l'entraîneur
    entraîneur = EntraineurModeleRisque(random_state=42)

    # Préparer les données
    entraîneur.preparer_donnees()

    # Entraîner le modèle de base
    print("\n1. Entraînement du modèle de base...")
    entraîneur.entrainer_modele_base()

    # Optimiser les hyperparamètres
    print("\n2. Optimisation des hyperparamètres...")
    entraîneur.optimiser_hyperparametres()

    # Sauvegarder le modèle
    if sauvegarder:
        print("\n3. Sauvegarde du modèle...")
        entraîneur.sauvegarder_modele()

    print("\n=== Entraînement terminé avec succès ===")

    return entraîneur


# Fonction pour tester le modèle
def tester_modele_entraine():
    """
    Teste le modèle entraîné avec des données d'exemple
    """
    print("=== Test du modèle entraîné ===")

    # Charger ou entraîner le modèle
    entraîneur = EntraineurModeleRisque()

    try:
        entraîneur.charger_modele()
        print("Modèle chargé avec succès")
    except:
        print("Modèle non trouvé, entraînement d'un nouveau modèle...")
        entraîneur = entrainer_modele_complet(sauvegarder=True)

    # Données d'exemple pour un client
    donnees_exemple = {
        'statut_compte': 'A14',
        'duree_mois': 24,
        'historique_credit': 'A34',
        'but': 'A43',
        'montant': 5000,
        'epargne': 'A65',
        'anciennete_emploi': 'A75',
        'taux_remboursement': 3,
        'etat_civil_sexe': 'A93',
        'autres_debiteurs': 'A101',
        'residence_depuis': 2,
        'biens': 'A121',
        'age': 35,
        'autres_plans': 'A143',
        'logement': 'A152',
        'credits_existants': 1,
        'emploi': 'A173',
        'personnes_charge': 1,
        'telephone': 'A191',
        'travailleur_etranger': 'A201'
    }

    # Faire une prédiction
    print("\nPrédiction pour un client d'exemple:")
    resultat = entraîneur.predire_risque(donnees_exemple)

    print(f"\nRésultats de la prédiction:")
    print(f"  Score de risque: {resultat['score_risque']:.2f}%")
    print(f"  Probabilité de défaut: {resultat['probabilite_defaut']:.4f}")
    print(f"  Catégorie de risque: {resultat['categorie_risque']}")
    print(f"  Recommandation: {resultat['recommandation']}")

    print(f"\nFacteurs positifs (réduisent le risque):")
    for facteur in resultat['facteurs_positifs']:
        print(f"  - {facteur}")

    print(f"\nFacteurs négatifs (augmentent le risque):")
    for facteur in resultat['facteurs_negatifs']:
        print(f"  - {facteur}")

    print("\n=== Test terminé avec succès ===")

    return entraîneur, resultat


if __name__ == "__main__":
    # Tester le pipeline d'entraînement
    # entraîneur = entrainer_modele_complet(sauvegarder=True)

    # Tester le modèle entraîné
    entraîneur, resultat = tester_modele_entraine()