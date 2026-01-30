"""
Modèles de données pour l'API de Scoring de Risque
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Client(models.Model):
    """
    Modèle représentant un client avec ses informations personnelles
    """

    # Choix pour les types de professions
    TYPE_PROFESSION = (
        ('sans_emploi', 'Sans emploi'),
        ('non_qualifie', 'Travail non qualifié'),
        ('qualifie', 'Travail qualifié'),
        ('cadre', 'Cadre'),
        ('independant', 'Indépendant'),
        ('fonctionnaire', 'Fonctionnaire'),
    )

    # Choix pour les états civils
    ETAT_CIVIL = (
        ('celibataire', 'Célibataire'),
        ('marie', 'Marié(e)'),
        ('divorce', 'Divorcé(e)'),
        ('veuf', 'Veuf/Veuve'),
    )

    # Informations personnelles
    nom = models.CharField(max_length=100, verbose_name="Nom de famille")
    prenom = models.CharField(max_length=100, verbose_name="Prénom")
    email = models.EmailField(unique=True, verbose_name="Adresse email")
    telephone = models.CharField(max_length=20, verbose_name="Numéro de téléphone")

    # Démographie
    date_naissance = models.DateField(verbose_name="Date de naissance")
    age = models.IntegerField(
        verbose_name="Âge",
        validators=[MinValueValidator(18), MaxValueValidator(100)]
    )
    etat_civil = models.CharField(
        max_length=20,
        choices=ETAT_CIVIL,
        verbose_name="État civil"
    )
    nombre_enfants = models.IntegerField(
        default=0,
        verbose_name="Nombre d'enfants à charge",
        validators=[MinValueValidator(0)]
    )

    # Profession
    profession = models.CharField(
        max_length=50,
        choices=TYPE_PROFESSION,
        verbose_name="Type de profession"
    )
    anciennete_emploi = models.IntegerField(
        verbose_name="Ancienneté dans l'emploi (mois)",
        validators=[MinValueValidator(0)]
    )

    # Revenus
    revenu_mensuel = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Revenu mensuel net (€)",
        validators=[MinValueValidator(0)]
    )
    autres_revenus = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Autres revenus mensuels (€)",
        validators=[MinValueValidator(0)]
    )

    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    date_modification = models.DateTimeField(auto_now=True, verbose_name="Date de modification")

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ['nom', 'prenom']

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    def revenu_total(self):
        """Calcule le revenu total mensuel"""
        return self.revenu_mensuel + self.autres_revenus

    def est_majeur(self):
        """Vérifie si le client est majeur"""
        return self.age >= 18


class HistoriqueFinancier(models.Model):
    """
    Modèle représentant l'historique financier d'un client
    """

    client = models.OneToOneField(
        Client,
        on_delete=models.CASCADE,
        related_name='historique_financier',
        verbose_name="Client"
    )

    # Comptes bancaires
    solde_compte = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Solde du compte courant (€)"
    )
    epargne = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Épargne totale (€)"
    )

    # Dettes existantes
    dette_cartes = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Dette cartes de crédit (€)"
    )
    dette_autres = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Autres dettes (€)"
    )

    # Historique de crédit
    nb_credits_anterieurs = models.IntegerField(
        default=0,
        verbose_name="Nombre de crédits antérieurs",
        validators=[MinValueValidator(0)]
    )
    defauts_paiement = models.IntegerField(
        default=0,
        verbose_name="Nombre de défauts de paiement",
        validators=[MinValueValidator(0)]
    )
    duree_relation_banque = models.IntegerField(
        verbose_name="Durée de relation avec la banque (mois)",
        validators=[MinValueValidator(0)]
    )

    # Dépenses mensuelles moyennes
    depenses_logement = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Dépenses logement mensuelles (€)"
    )
    depenses_autres = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Autres dépenses mensuelles (€)"
    )

    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Historique Financier"
        verbose_name_plural = "Historiques Financiers"

    def __str__(self):
        return f"Historique financier de {self.client}"

    def dette_totale(self):
        """Calcule la dette totale du client"""
        return self.dette_cartes + self.dette_autres

    def depenses_totales(self):
        """Calcule les dépenses mensuelles totales"""
        return self.depenses_logement + self.depenses_autres

    def ratio_dette_revenu(self):
        """Calcule le ratio dette/revenu du client"""
        revenu_total = self.client.revenu_total()
        if revenu_total > 0:
            return (self.dette_totale() / revenu_total) * 100
        return 0


class DemandeCredit(models.Model):
    """
    Modèle représentant une demande de crédit
    """

    # Choix pour les types de crédit
    TYPE_CREDIT = (
        ('consommation', 'Crédit consommation'),
        ('immobilier', 'Crédit immobilier'),
        ('professionnel', 'Crédit professionnel'),
        ('urgence', 'Crédit urgent'),
    )

    # Choix pour les statuts de la demande
    STATUT_DEMANDE = (
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours d\'analyse'),
        ('approuve', 'Approuvé'),
        ('rejete', 'Rejeté'),
        ('annule', 'Annulé'),
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='demandes_credit',
        verbose_name="Client"
    )

    # Informations sur le crédit
    type_credit = models.CharField(
        max_length=50,
        choices=TYPE_CREDIT,
        verbose_name="Type de crédit"
    )
    montant_demande = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Montant demandé (€)",
        validators=[MinValueValidator(100)]
    )
    duree_mois = models.IntegerField(
        verbose_name="Durée du crédit (mois)",
        validators=[MinValueValidator(1), MaxValueValidator(360)]
    )
    taux_interet = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Taux d'intérêt annuel (%)",
        validators=[MinValueValidator(0), MaxValueValidator(50)]
    )

    # Destination du crédit
    destination_credit = models.CharField(
        max_length=200,
        verbose_name="Destination du crédit"
    )

    # Garanties
    avec_garantie = models.BooleanField(default=False, verbose_name="Avec garantie")
    valeur_garantie = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Valeur de la garantie (€)"
    )

    # Statut
    statut = models.CharField(
        max_length=20,
        choices=STATUT_DEMANDE,
        default='en_attente',
        verbose_name="Statut de la demande"
    )

    # Dates importantes
    date_demande = models.DateTimeField(auto_now_add=True, verbose_name="Date de la demande")
    date_traitement = models.DateTimeField(null=True, blank=True, verbose_name="Date de traitement")
    date_echeance = models.DateField(null=True, blank=True, verbose_name="Date d'échéance")

    # Métadonnées
    commentaires = models.TextField(blank=True, verbose_name="Commentaires")

    class Meta:
        verbose_name = "Demande de Crédit"
        verbose_name_plural = "Demandes de Crédit"
        ordering = ['-date_demande']

    def __str__(self):
        return f"Demande {self.id} - {self.client} - {self.montant_demande}€"

    def mensualite(self):
        """Calcule la mensualité du crédit"""
        if self.duree_mois > 0:
            taux_mensuel = (self.taux_interet / 100) / 12
            numerateur = taux_mensuel * (1 + taux_mensuel) ** self.duree_mois
            denominateur = (1 + taux_mensuel) ** self.duree_mois - 1
            return round(self.montant_demande * numerateur / denominateur, 2)
        return 0

    def montant_total(self):
        """Calcule le montant total à rembourser"""
        mensualite = self.mensualite()
        return round(mensualite * self.duree_mois, 2) if mensualite > 0 else 0

    def cout_total_interets(self):
        """Calcule le coût total des intérêts"""
        return round(self.montant_total() - self.montant_demande, 2)

    def traiter(self):
        """Marque la demande comme traitée"""
        self.date_traitement = timezone.now()
        self.save()


class ScoreRisque(models.Model):
    """
    Modèle représentant le score de risque d'une demande de crédit
    """

    demande_credit = models.OneToOneField(
        DemandeCredit,
        on_delete=models.CASCADE,
        related_name='score_risque',
        verbose_name="Demande de crédit"
    )

    # Score principal
    score = models.FloatField(
        verbose_name="Score de risque (0-100)",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Catégorie de risque
    CATEGORIE_RISQUE = (
        ('faible', 'Faible risque'),
        ('modere', 'Risque modéré'),
        ('eleve', 'Risque élevé'),
        ('tres_eleve', 'Très haut risque'),
    )
    categorie_risque = models.CharField(
        max_length=20,
        choices=CATEGORIE_RISQUE,
        verbose_name="Catégorie de risque"
    )

    # Facteurs contributifs (stockés en JSON via TextField pour simplicité)
    facteurs_positifs = models.TextField(
        verbose_name="Facteurs positifs (JSON)",
        help_text="Facteurs qui ont réduit le risque, au format JSON"
    )
    facteurs_negatifs = models.TextField(
        verbose_name="Facteurs négatifs (JSON)",
        help_text="Facteurs qui ont augmenté le risque, au format JSON"
    )

    # Recommandation
    RECOMMANDATION = (
        ('approbation', 'Approbation'),
        ('rejet', 'Rejet'),
        ('revision', 'Nécessite révision'),
        ('garantie', 'Approbation avec garantie supplémentaire'),
    )
    recommandation = models.CharField(
        max_length=20,
        choices=RECOMMANDATION,
        verbose_name="Recommandation"
    )

    # Seuils de décision
    seuil_approbation = models.FloatField(
        default=30.0,
        verbose_name="Seuil d'approbation (%)",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    seuil_rejet = models.FloatField(
        default=70.0,
        verbose_name="Seuil de rejet (%)",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Explicabilité
    valeurs_shap = models.TextField(
        blank=True,
        verbose_name="Valeurs SHAP (JSON)",
        help_text="Valeurs SHAP pour l'explicabilité du score"
    )

    # Métadonnées
    date_calcul = models.DateTimeField(auto_now_add=True, verbose_name="Date du calcul")
    version_modele = models.CharField(max_length=50, verbose_name="Version du modèle utilisé")

    class Meta:
        verbose_name = "Score de Risque"
        verbose_name_plural = "Scores de Risque"
        ordering = ['-date_calcul']

    def __str__(self):
        return f"Score {self.score}% - {self.demande_credit}"

    def est_approuve(self):
        """Détermine si la demande est approuvée"""
        return self.recommandation == 'approbation'

    def est_rejete(self):
        """Détermine si la demande est rejetée"""
        return self.recommandation == 'rejet'

    def get_categorie_couleur(self):
        """Retourne une couleur associée à la catégorie de risque"""
        couleurs = {
            'faible': 'success',
            'modere': 'warning',
            'eleve': 'danger',
            'tres_eleve': 'dark',
        }
        return couleurs.get(self.categorie_risque, 'secondary')