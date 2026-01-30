"""
Script pour générer des données d'exemple pour le projet
"""

import os
import sys
import django
import random
from datetime import date, timedelta
from decimal import Decimal

# Configuration de Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_scoring_risque.settings')
django.setup()

from application_risque.models import Client, HistoriqueFinancier, DemandeCredit, ScoreRisque
from django.utils import timezone


def generer_clients(nombre=50):
    """Génère des clients d'exemple"""

    noms = [
        'Martin', 'Bernard', 'Dubois', 'Thomas', 'Robert', 'Richard', 'Petit',
        'Durand', 'Leroy', 'Moreau', 'Simon', 'Laurent', 'Lefebvre', 'Michel',
        'Garcia', 'David', 'Bertrand', 'Roux', 'Vincent', 'Fournier', 'Morel',
        'Girard', 'Andre', 'Lefevre', 'Mercier', 'Dupont', 'Lambert', 'Bonnet',
        'Francois', 'Martinez', 'Legrand', 'Garnier', 'Faure', 'Rousseau'
    ]

    prenoms = [
        'Emma', 'Louise', 'Jade', 'Alice', 'Chloe', 'Lina', 'Rose', 'Anna',
        'Mila', 'Léa', 'Manon', 'Julia', 'Inès', 'Léna', 'Camille', 'Sarah',
        'Juliette', 'Lucie', 'Éva', 'Jeanne', 'Lucas', 'Hugo', 'Gabriel',
        'Raphaël', 'Louis', 'Arthur', 'Jules', 'Adam', 'Maël', 'Paul', 'Nathan',
        'Gabin', 'Sacha', 'Noah', 'Léo', 'Tom', 'Théo', 'Aaron', 'Maxime'
    ]

    professions = [p[0] for p in Client.TYPE_PROFESSION]
    etats_civils = [e[0] for e in Client.ETAT_CIVIL]

    clients_crees = []

    for i in range(nombre):
        # Générer une date de naissance aléatoire (âge entre 25 et 65 ans)
        age = random.randint(25, 65)
        date_naissance = date.today() - timedelta(days=age * 365 + random.randint(0, 365))

        client = Client.objects.create(
            nom=random.choice(noms),
            prenom=random.choice(prenoms),
            email=f"{random.choice(prenoms).lower()}.{random.choice(noms).lower()}{i}@example.com",
            telephone=f"0{random.randint(6, 7)}{random.randint(10, 99)}{random.randint(10, 99)}{random.randint(10, 99)}{random.randint(10, 99)}",
            date_naissance=date_naissance,
            age=age,
            etat_civil=random.choice(etats_civils),
            nombre_enfants=random.randint(0, 4),
            profession=random.choice(professions),
            anciennete_emploi=random.randint(1, 240),  # 1 mois à 20 ans
            revenu_mensuel=Decimal(random.randint(1500, 8000)),
            autres_revenus=Decimal(random.randint(0, 2000))
        )

        clients_crees.append(client)
        print(f"Client créé: {client}")

    return clients_crees


def generer_historiques_financiers(clients):
    """Génère des historiques financiers pour les clients"""

    for client in clients:
        historique = HistoriqueFinancier.objects.get(client=client)

        # Mettre à jour avec des données réalistes
        historique.solde_compte = Decimal(random.randint(-500, 5000))
        historique.epargne = Decimal(random.randint(0, 30000))
        historique.dette_cartes = Decimal(random.randint(0, 5000))
        historique.dette_autres = Decimal(random.randint(0, 10000))
        historique.nb_credits_anterieurs = random.randint(0, 5)
        historique.defauts_paiement = random.randint(0, 2)
        historique.duree_relation_banque = random.randint(6, 240)  # 6 mois à 20 ans
        historique.depenses_logement = Decimal(random.randint(400, 1500))
        historique.depenses_autres = Decimal(random.randint(300, 2000))

        historique.save()
        print(f"Historique financier créé pour: {client}")


def generer_demandes_credit(clients, nombre_par_client=2):
    """Génère des demandes de crédit pour les clients"""

    types_credit = [t[0] for t in DemandeCredit.TYPE_CREDIT]

    demandes_crees = []

    for client in clients:
        for _ in range(random.randint(1, nombre_par_client)):
            # Date de demande aléatoire dans les 6 derniers mois
            jours_aleatoires = random.randint(0, 180)
            date_demande = timezone.now() - timedelta(days=jours_aleatoires)

            demande = DemandeCredit.objects.create(
                client=client,
                type_credit=random.choice(types_credit),
                montant_demande=Decimal(random.randint(5000, 50000)),
                duree_mois=random.choice([12, 24, 36, 48, 60, 72, 84, 96, 108, 120]),
                taux_interet=Decimal(random.uniform(1.5, 6.0)),
                destination_credit=random.choice([
                    "Achat de voiture",
                    "Travaux de rénovation",
                    "Projet personnel",
                    "Consolidation de dettes",
                    "Investissement immobilier",
                    "Frais médicaux",
                    "Études des enfants",
                    "Voyage"
                ]),
                avec_garantie=random.choice([True, False]),
                valeur_garantie=Decimal(random.randint(0, 20000)),
                statut=random.choice(['en_attente', 'en_cours', 'approuve', 'rejete']),
                date_demande=date_demande,
                commentaires=random.choice([
                    "Demande standard",
                    "Client fidèle depuis plusieurs années",
                    "Première demande de crédit",
                    "Situation professionnelle stable",
                    "Revenus réguliers"
                ])
            )

            demandes_crees.append(demande)
            print(f"Demande de crédit créée: {demande}")

    return demandes_crees


def generer_scores_risque(demandes):
    """Génère des scores de risque pour les demandes"""

    for demande in demandes:
        # Simuler un score basé sur des facteurs
        client = demande.client
        historique = client.historique_financier

        # Facteurs influençant le score (simplifié)
        facteur_age = max(0, min(100, (client.age - 25) / 40 * 100))  # Meilleur entre 25-65 ans
        facteur_revenu = max(0, min(100, (client.revenu_total() / 5000) * 100))  # Meilleur si > 5000€
        facteur_dette = min(100, (historique.dette_totale() / client.revenu_total()) * 200)  # Pire si dette élevée
        facteur_defauts = min(100, historique.defauts_paiement * 30)  # Pire avec défauts
        facteur_anciennete = max(0, min(100, (historique.duree_relation_banque / 60) * 100))  # Meilleur si > 5 ans

        # Calcul du score (0-100, où 0 = bon risque, 100 = mauvais risque)
        score = (
                facteur_dette * 0.35 +
                facteur_defauts * 0.25 +
                (100 - facteur_revenu) * 0.20 +
                (100 - facteur_age) * 0.10 +
                (100 - facteur_anciennete) * 0.10
        )

        # Ajouter un peu de random pour variété
        score = max(0, min(100, score + random.uniform(-10, 10)))

        # Facteurs contributifs (format JSON simplifié)
        facteurs_positifs = [
            f"Ancienneté dans l'emploi: {client.anciennete_emploi} mois",
            f"Revenu mensuel: {client.revenu_mensuel}€"
        ]

        facteurs_negatifs = []
        if historique.dette_totale() > 0:
            facteurs_negatifs.append(f"Dettes existantes: {historique.dette_totale()}€")
        if historique.defauts_paiement > 0:
            facteurs_negatifs.append(f"Défauts de paiement antérieurs: {historique.defauts_paiement}")

        score_obj = ScoreRisque.objects.create(
            demande_credit=demande,
            score=round(score, 2),
            facteurs_positifs=str(facteurs_positifs),
            facteurs_negatifs=str(facteurs_negatifs),
            valeurs_shap=str({
                "dette_totale": round(facteur_dette * 0.35, 2),
                "defauts_paiement": round(facteur_defauts * 0.25, 2),
                "revenu": round((100 - facteur_revenu) * 0.20, 2),
                "age": round((100 - facteur_age) * 0.10, 2),
                "anciennete_banque": round((100 - facteur_anciennete) * 0.10, 2)
            }),
            version_modele="v1.0-simulation"
        )

        print(f"Score de risque créé: {score_obj.score}% pour demande {demande.id}")


def main():
    """Fonction principale pour générer toutes les données"""

    print("=== Génération des données d'exemple ===")

    # Vérifier si des données existent déjà
    if Client.objects.count() > 0:
        print("Des données existent déjà. Voulez-vous continuer? (o/n)")
        reponse = input().strip().lower()
        if reponse != 'o':
            print("Annulation.")
            return

    # Générer les données
    print("\n1. Génération des clients...")
    clients = generer_clients(30)

    print("\n2. Génération des historiques financiers...")
    generer_historiques_financiers(clients)

    print("\n3. Génération des demandes de crédit...")
    demandes = generer_demandes_credit(clients, 2)

    print("\n4. Génération des scores de risque...")
    generer_scores_risque(demandes)

    print(f"\n=== Génération terminée ===")
    print(f"Clients créés: {Client.objects.count()}")
    print(f"Demandes de crédit: {DemandeCredit.objects.count()}")
    print(f"Scores de risque: {ScoreRisque.objects.count()}")


if __name__ == "__main__":
    main()