"""
Préparation et traitement du dataset German Credit Data
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib
import os


class PreparateurDonnees:
    """
    Classe pour préparer et prétraiter les données du German Credit Dataset
    """

    def __init__(self, chemin_dataset=None):
        """
        Initialise le préparateur de données

        Args:
            chemin_dataset: Chemin vers le fichier du dataset
        """
        self.chemin_dataset = chemin_dataset or self._telecharger_dataset()
        self.dataframe = None
        self.encoders = {}
        self.scaler = StandardScaler()

    def _telecharger_dataset(self):
        """
        Télécharge ou localise le dataset German Credit
        Note: Dans un environnement de production, on stockerait le dataset localement
        """
        # URLs alternatives pour le dataset
        urls = [
            "https://archive.ics.uci.edu/ml/machine-learning-databases/statlog/german/german.data",
            "https://raw.githubusercontent.com/scikit-learn/scikit-learn/main/sklearn/datasets/data/german.data"
        ]

        chemin_local = "donnees/german_credit_data.csv"

        # Si le fichier n'existe pas localement, essayer de le télécharger
        if not os.path.exists(chemin_local):
            print("Téléchargement du dataset German Credit...")
            try:
                import urllib.request
                urllib.request.urlretrieve(urls[0], chemin_local)
                print(f"Dataset téléchargé: {chemin_local}")
            except:
                print("Échec du téléchargement. Création d'un dataset simulé...")
                self._creer_dataset_simule(chemin_local)

        return chemin_local

    def _creer_dataset_simule(self, chemin_sortie):
        """
        Crée un dataset simulé si le téléchargement échoue
        """
        # Nombre d'échantillons
        n_echantillons = 1000

        # Génération de données simulées basées sur la description du German Credit Dataset
        donnees = {
            'statut_compte': np.random.choice(['A11', 'A12', 'A13', 'A14'], n_echantillons),
            'duree_mois': np.random.randint(4, 72, n_echantillons),
            'historique_credit': np.random.choice(['A30', 'A31', 'A32', 'A33', 'A34'], n_echantillons),
            'but': np.random.choice(['A40', 'A41', 'A42', 'A43', 'A44', 'A45', 'A46', 'A47', 'A48', 'A49', 'A410'],
                                    n_echantillons),
            'montant': np.random.randint(250, 10000, n_echantillons),
            'epargne': np.random.choice(['A61', 'A62', 'A63', 'A64', 'A65'], n_echantillons),
            'anciennete_emploi': np.random.choice(['A71', 'A72', 'A73', 'A74', 'A75'], n_echantillons),
            'taux_remboursement': np.random.randint(1, 4, n_echantillons),
            'etat_civil_sexe': np.random.choice(['A91', 'A92', 'A93', 'A94'], n_echantillons),
            'autres_debiteurs': np.random.choice(['A101', 'A102', 'A103'], n_echantillons),
            'residence_depuis': np.random.randint(1, 4, n_echantillons),
            'biens': np.random.choice(['A121', 'A122', 'A123', 'A124'], n_echantillons),
            'age': np.random.randint(19, 75, n_echantillons),
            'autres_plans': np.random.choice(['A141', 'A142', 'A143'], n_echantillons),
            'logement': np.random.choice(['A151', 'A152', 'A153'], n_echantillons),
            'credits_existants': np.random.randint(1, 4, n_echantillons),
            'emploi': np.random.choice(['A171', 'A172', 'A173', 'A174'], n_echantillons),
            'personnes_charge': np.random.randint(1, 2, n_echantillons),
            'telephone': np.random.choice(['A191', 'A192'], n_echantillons),
            'travailleur_etranger': np.random.choice(['A201', 'A202'], n_echantillons),
            'cible': np.random.choice([1, 2], n_echantillons, p=[0.7, 0.3])  # 70% bon crédit, 30% mauvais
        }

        dataframe = pd.DataFrame(donnees)
        dataframe.to_csv(chemin_sortie, index=False)
        print(f"Dataset simulé créé: {chemin_sortie}")

        return chemin_sortie

    def charger_donnees(self):
        """
        Charge et prépare le dataset

        Returns:
            DataFrame pandas avec les données
        """
        # Noms des colonnes selon la documentation UCI
        noms_colonnes = [
            'statut_compte', 'duree_mois', 'historique_credit', 'but', 'montant',
            'epargne', 'anciennete_emploi', 'taux_remboursement', 'etat_civil_sexe',
            'autres_debiteurs', 'residence_depuis', 'biens', 'age', 'autres_plans',
            'logement', 'credits_existants', 'emploi', 'personnes_charge',
            'telephone', 'travailleur_etranger', 'cible'
        ]

        try:
            # Essayer de charger le dataset avec les noms de colonnes
            self.dataframe = pd.read_csv(
                self.chemin_dataset,
                sep=' ',
                header=None,
                names=noms_colonnes
            )
        except:
            # Si échec, essayer sans séparateur spécifique
            self.dataframe = pd.read_csv(self.chemin_dataset)

        # Ajuster la cible: 1 = bon crédit, 2 = mauvais crédit -> convertir en 0 = bon, 1 = mauvais
        if 'cible' in self.dataframe.columns:
            self.dataframe['cible'] = self.dataframe['cible'].map({1: 0, 2: 1})

        print(f"Dataset chargé: {self.dataframe.shape[0]} échantillons, {self.dataframe.shape[1]} caractéristiques")
        print(f"Distribution des classes: {self.dataframe['cible'].value_counts().to_dict()}")

        return self.dataframe

    def preprocesser_donnees(self, dataframe=None):
        """
        Prétraite les données pour l'entraînement

        Args:
            dataframe: DataFrame à prétraiter (utilise self.dataframe si None)

        Returns:
            X, y: Données d'entrée et labels
        """
        if dataframe is None:
            dataframe = self.dataframe

        if dataframe is None:
            raise ValueError("Aucune donnée à prétraiter. Chargez d'abord les données.")

        # Séparer les caractéristiques et la cible
        X = dataframe.drop('cible', axis=1)
        y = dataframe['cible']

        # Séparer les caractéristiques catégorielles et numériques
        colonnes_categorielles = X.select_dtypes(include=['object']).columns
        colonnes_numeriques = X.select_dtypes(include=['int64', 'float64']).columns

        print(f"Caractéristiques catégorielles: {len(colonnes_categorielles)}")
        print(f"Caractéristiques numériques: {len(colonnes_numeriques)}")

        # Encoder les caractéristiques catégorielles
        X_encoded = X.copy()
        for colonne in colonnes_categorielles:
            encoder = LabelEncoder()
            X_encoded[colonne] = encoder.fit_transform(X[colonne])
            self.encoders[colonne] = encoder

        # Normaliser les caractéristiques numériques
        if len(colonnes_numeriques) > 0:
            X_encoded[colonnes_numeriques] = self.scaler.fit_transform(X_encoded[colonnes_numeriques])

        return X_encoded, y

    def preparer_pour_entrainement(self, taille_test=0.2, random_state=42):
        """
        Prépare les données pour l'entraînement

        Args:
            taille_test: Proportion des données à utiliser pour le test
            random_state: Seed pour la reproductibilité

        Returns:
            X_train, X_test, y_train, y_test: Données d'entraînement et de test
        """
        if self.dataframe is None:
            self.charger_donnees()

        X, y = self.preprocesser_donnees()

        # Diviser en ensembles d'entraînement et de test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=taille_test,
            random_state=random_state,
            stratify=y  # Conserver la distribution des classes
        )

        print(f"Données d'entraînement: {X_train.shape}")
        print(f"Données de test: {X_test.shape}")

        return X_train, X_test, y_train, y_test

    def sauvegarder_preprocesseurs(self, chemin_dossier='gestion_modeles/preprocesseurs'):
        """
        Sauvegarde les encodeurs et le scaler pour une utilisation future

        Args:
            chemin_dossier: Dossier où sauvegarder les préprocesseurs
        """
        os.makedirs(chemin_dossier, exist_ok=True)

        # Sauvegarder les encodeurs
        for nom, encodeur in self.encoders.items():
            chemin_fichier = os.path.join(chemin_dossier, f'encodeur_{nom}.pkl')
            joblib.dump(encodeur, chemin_fichier)
            print(f"Encodeur sauvegardé: {chemin_fichier}")

        # Sauvegarder le scaler
        chemin_scaler = os.path.join(chemin_dossier, 'scaler.pkl')
        joblib.dump(self.scaler, chemin_scaler)
        print(f"Scaler sauvegardé: {chemin_scaler}")

        # Sauvegarder la liste des colonnes
        colonnes_info = {
            'colonnes_categorielles': list(self.encoders.keys()),
            'colonnes_numeriques': [col for col in self.dataframe.columns if
                                    col != 'cible' and col not in self.encoders]
        }
        joblib.dump(colonnes_info, os.path.join(chemin_dossier, 'colonnes_info.pkl'))

    def charger_preprocesseurs(self, chemin_dossier='gestion_modeles/preprocesseurs'):
        """
        Charge les préprocesseurs sauvegardés

        Args:
            chemin_dossier: Dossier où charger les préprocesseurs
        """
        # Charger les encodeurs
        fichiers = os.listdir(chemin_dossier)
        for fichier in fichiers:
            if fichier.startswith('encodeur_'):
                nom = fichier.replace('encodeur_', '').replace('.pkl', '')
                chemin = os.path.join(chemin_dossier, fichier)
                self.encoders[nom] = joblib.load(chemin)
                print(f"Encodeur chargé: {nom}")

        # Charger le scaler
        chemin_scaler = os.path.join(chemin_dossier, 'scaler.pkl')
        if os.path.exists(chemin_scaler):
            self.scaler = joblib.load(chemin_scaler)
            print("Scaler chargé")

    def transformer_nouvelles_donnees(self, X_nouvelles):
        """
        Transforme de nouvelles données avec les préprocesseurs entraînés

        Args:
            X_nouvelles: Nouvelles données à transformer

        Returns:
            X_transformees: Données transformées
        """
        X_transformees = X_nouvelles.copy()

        # Encoder les caractéristiques catégorielles
        for colonne, encodeur in self.encoders.items():
            if colonne in X_transformees.columns:
                # Pour les nouvelles valeurs non vues pendant l'entraînement
                valeurs_uniques = set(X_transformees[colonne].unique())
                valeurs_entrainees = set(encodeur.classes_)

                # Assigner une valeur spéciale pour les nouvelles catégories
                valeurs_nouvelles = valeurs_uniques - valeurs_entrainees
                if valeurs_nouvelles:
                    print(f"Avertissement: Nouvelles catégories dans {colonne}: {valeurs_nouvelles}")
                    # Utiliser la catégorie la plus fréquente comme valeur par défaut
                    valeur_defaut = encodeur.transform([encodeur.classes_[0]])[0]
                    X_transformees[colonne] = X_transformees[colonne].apply(
                        lambda x: encodeur.transform([x])[0] if x in encodeur.classes_ else valeur_defaut
                    )
                else:
                    X_transformees[colonne] = encodeur.transform(X_transformees[colonne])

        # Normaliser les caractéristiques numériques
        colonnes_numeriques = X_transformees.select_dtypes(include=['int64', 'float64']).columns
        if len(colonnes_numeriques) > 0:
            X_transformees[colonnes_numeriques] = self.scaler.transform(X_transformees[colonnes_numeriques])

        return X_transformees


# Fonction utilitaire pour tester le module
def tester_preparation():
    """Teste le module de préparation des données"""
    print("=== Test du module de préparation des données ===")

    preparateur = PreparateurDonnees()

    # Charger les données
    dataframe = preparateur.charger_donnees()
    print(f"\nAperçu des données:\n{dataframe.head()}")
    print(f"\nInfos sur les données:\n{dataframe.info()}")

    # Préparer pour l'entraînement
    X_train, X_test, y_train, y_test = preparateur.preparer_pour_entrainement()

    print(f"\nForme des données d'entraînement: {X_train.shape}")
    print(f"Forme des données de test: {X_test.shape}")
    print(f"Distribution des classes (train): {pd.Series(y_train).value_counts().to_dict()}")
    print(f"Distribution des classes (test): {pd.Series(y_test).value_counts().to_dict()}")

    # Sauvegarder les préprocesseurs
    preparateur.sauvegarder_preprocesseurs()

    print("\n=== Test terminé avec succès ===")

    return preparateur, X_train, X_test, y_train, y_test


if __name__ == "__main__":
    tester_preparation()