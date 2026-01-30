"""
Signaux pour maintenir la cohérence des données
"""

import json
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Client, HistoriqueFinancier, DemandeCredit, ScoreRisque


@receiver(pre_save, sender=Client)
def calculer_age_client(sender, instance, **kwargs):
    """
    Calcule l'âge du client à partir de sa date de naissance
    Note: Dans un système réel, on calculerait dynamiquement,
    mais pour ce projet, nous stockons l'âge pour simplifier
    """
    if instance.date_naissance:
        aujourdhui = timezone.now().date()
        age = aujourdhui.year - instance.date_naissance.year
        # Ajuster si l'anniversaire n'est pas encore passé cette année
        if (aujourdhui.month, aujourdhui.day) < (instance.date_naissance.month, instance.date_naissance.day):
            age -= 1
        instance.age = max(18, age)  # Minimum 18 ans


@receiver(post_save, sender=Client)
def creer_historique_financier(sender, instance, created, **kwargs):
    """
    Crée automatiquement un historique financier pour un nouveau client
    """
    if created:
        HistoriqueFinancier.objects.create(
            client=instance,
            solde_compte=0,
            epargne=0,
            dette_cartes=0,
            dette_autres=0,
            nb_credits_anterieurs=0,
            defauts_paiement=0,
            duree_relation_banque=0,
            depenses_logement=0,
            depenses_autres=0
        )


@receiver(post_save, sender=DemandeCredit)
def mettre_a_jour_statut_demande(sender, instance, **kwargs):
    """
    Met à jour automatiquement la date de traitement quand le statut change
    """
    if instance.statut in ['approuve', 'rejete', 'annule'] and not instance.date_traitement:
        instance.date_traitement = timezone.now()
        # Éviter la récursion en utilisant update()
        DemandeCredit.objects.filter(id=instance.id).update(
            date_traitement=instance.date_traitement
        )


@receiver(post_save, sender=ScoreRisque)
def mettre_a_jour_recommandation_demande(sender, instance, **kwargs):
    """
    Met à jour la recommandation de la demande de crédit basée sur le score
    """
    demande = instance.demande_credit

    # Mettre à jour la recommandation dans la demande
    if instance.recommandation == 'approbation':
        demande.statut = 'approuve'
    elif instance.recommandation == 'rejet':
        demande.statut = 'rejete'
    elif instance.recommandation in ['revision', 'garantie']:
        demande.statut = 'en_cours'

    demande.save()


@receiver(pre_save, sender=ScoreRisque)
def determiner_categorie_risque(sender, instance, **kwargs):
    """
    Détermine la catégorie de risque basée sur le score
    """
    score = instance.score

    if score < 25:
        instance.categorie_risque = 'faible'
    elif score < 50:
        instance.categorie_risque = 'modere'
    elif score < 75:
        instance.categorie_risque = 'eleve'
    else:
        instance.categorie_risque = 'tres_eleve'

    # Déterminer la recommandation automatiquement
    if score <= instance.seuil_approbation:
        instance.recommandation = 'approbation'
    elif score >= instance.seuil_rejet:
        instance.recommandation = 'rejet'
    elif score <= 50:
        instance.recommandation = 'garantie'
    else:
        instance.recommandation = 'revision'