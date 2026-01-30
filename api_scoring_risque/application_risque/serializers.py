"""
Serializers Django REST Framework pour l'API de scoring de risque
"""

from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from .models import Client, HistoriqueFinancier, DemandeCredit, ScoreRisque


class ClientSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle Client
    """

    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=Client.objects.all())]
    )

    revenu_total = serializers.SerializerMethodField()
    est_majeur = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            'id', 'nom', 'prenom', 'email', 'telephone',
            'date_naissance', 'age', 'etat_civil', 'nombre_enfants',
            'profession', 'anciennete_emploi', 'revenu_mensuel',
            'autres_revenus', 'revenu_total', 'est_majeur',
            'date_creation', 'date_modification'
        ]
        read_only_fields = ['date_creation', 'date_modification', 'age']

    def get_revenu_total(self, obj):
        """Calcule le revenu total du client"""
        return obj.revenu_total()

    def get_est_majeur(self, obj):
        """Vérifie si le client est majeur"""
        return obj.est_majeur()

    def validate_date_naissance(self, value):
        """
        Valide que la date de naissance correspond à un âge >= 18 ans
        """
        aujourdhui = timezone.now().date()
        age = aujourdhui.year - value.year

        # Ajuster si l'anniversaire n'est pas encore passé cette année
        if (aujourdhui.month, aujourdhui.day) < (value.month, value.day):
            age -= 1

        if age < 18:
            raise serializers.ValidationError(
                "Le client doit avoir au moins 18 ans."
            )

        return value

    def validate_revenu_mensuel(self, value):
        """Valide que le revenu mensuel est positif"""
        if value <= 0:
            raise serializers.ValidationError(
                "Le revenu mensuel doit être supérieur à 0."
            )
        return value


class HistoriqueFinancierSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle HistoriqueFinancier
    """

    client_nom_complet = serializers.CharField(source='client.__str__', read_only=True)
    dette_totale = serializers.SerializerMethodField()
    depenses_totales = serializers.SerializerMethodField()
    ratio_dette_revenu = serializers.SerializerMethodField()

    class Meta:
        model = HistoriqueFinancier
        fields = [
            'id', 'client', 'client_nom_complet',
            'solde_compte', 'epargne', 'dette_cartes', 'dette_autres',
            'dette_totale', 'nb_credits_anterieurs', 'defauts_paiement',
            'duree_relation_banque', 'depenses_logement', 'depenses_autres',
            'depenses_totales', 'ratio_dette_revenu',
            'date_creation', 'date_modification'
        ]
        read_only_fields = ['date_creation', 'date_modification']

    def get_dette_totale(self, obj):
        return obj.dette_totale()

    def get_depenses_totales(self, obj):
        return obj.depenses_totales()

    def get_ratio_dette_revenu(self, obj):
        return obj.ratio_dette_revenu()

    def validate(self, data):
        """Validation croisée des données"""
        # Vérifier que le solde du compte n'est pas trop négatif
        solde_compte = data.get('solde_compte', getattr(self.instance, 'solde_compte', None))
        if solde_compte and solde_compte < -5000:
            raise serializers.ValidationError({
                'solde_compte': "Le solde du compte ne peut pas être inférieur à -5000€."
            })

        # Vérifier la cohérence des dettes
        dette_cartes = data.get('dette_cartes', getattr(self.instance, 'dette_cartes', 0))
        dette_autres = data.get('dette_autres', getattr(self.instance, 'dette_autres', 0))

        if dette_cartes < 0 or dette_autres < 0:
            raise serializers.ValidationError({
                'dette_cartes': "Les dettes ne peuvent pas être négatives.",
                'dette_autres': "Les dettes ne peuvent pas être négatives."
            })

        return data


class DemandeCreditSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle DemandeCredit
    """

    client_nom_complet = serializers.CharField(source='client.__str__', read_only=True)
    mensualite = serializers.SerializerMethodField()
    montant_total = serializers.SerializerMethodField()
    cout_total_interets = serializers.SerializerMethodField()
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    type_credit_display = serializers.CharField(source='get_type_credit_display', read_only=True)

    class Meta:
        model = DemandeCredit
        fields = [
            'id', 'client', 'client_nom_complet',
            'type_credit', 'type_credit_display',
            'montant_demande', 'duree_mois', 'taux_interet',
            'destination_credit', 'avec_garantie', 'valeur_garantie',
            'statut', 'statut_display', 'date_demande', 'date_traitement',
            'date_echeance', 'commentaires',
            'mensualite', 'montant_total', 'cout_total_interets'
        ]
        read_only_fields = ['date_demande', 'date_traitement']

    def get_mensualite(self, obj):
        return obj.mensualite()

    def get_montant_total(self, obj):
        return obj.montant_total()

    def get_cout_total_interets(self, obj):
        return obj.cout_total_interets()

    def validate(self, data):
        """Validation croisée des données de crédit"""
        montant_demande = data.get('montant_demande')
        duree_mois = data.get('duree_mois')
        taux_interet = data.get('taux_interet')
        valeur_garantie = data.get('valeur_garantie', 0)
        avec_garantie = data.get('avec_garantie', False)

        # Vérifier la durée maximale
        if duree_mois and duree_mois > 360:  # 30 ans
            raise serializers.ValidationError({
                'duree_mois': "La durée du crédit ne peut pas dépasser 360 mois (30 ans)."
            })

        # Vérifier le taux d'intérêt maximal
        if taux_interet and taux_interet > 50:  # 50% maximum
            raise serializers.ValidationError({
                'taux_interet': "Le taux d'intérêt ne peut pas dépasser 50%."
            })

        # Vérifier la cohérence garantie/valeur
        if avec_garantie and valeur_garantie <= 0:
            raise serializers.ValidationError({
                'valeur_garantie': "Une valeur de garantie positive est requise quand 'avec_garantie' est True."
            })

        # Vérifier que la mensualité n'est pas trop élevée par rapport au revenu
        if self.instance and self.instance.client and montant_demande and duree_mois:
            client = self.instance.client
            mensualite_calculee = self._calculer_mensualite(montant_demande, taux_interet or self.instance.taux_interet,
                                                            duree_mois)

            # Règle du tiers: mensualité < 1/3 du revenu
            if mensualite_calculee > client.revenu_total() / 3:
                raise serializers.ValidationError({
                    'montant_demande': f"La mensualité estimée ({mensualite_calculee:.2f}€) dépasse le tiers du revenu du client ({client.revenu_total() / 3:.2f}€)."
                })

        return data

    def _calculer_mensualite(self, montant, taux, duree):
        """Calcule la mensualité pour validation"""
        if duree > 0:
            taux_mensuel = (taux / 100) / 12
            numerateur = taux_mensuel * (1 + taux_mensuel) ** duree
            denominateur = (1 + taux_mensuel) ** duree - 1
            return round(montant * numerateur / denominateur, 2)
        return 0


class ScoreRisqueSerializer(serializers.ModelSerializer):
    """
    Serializer pour le modèle ScoreRisque
    """

    demande_credit_info = serializers.SerializerMethodField()
    categorie_risque_display = serializers.CharField(source='get_categorie_risque_display', read_only=True)
    recommandation_display = serializers.CharField(source='get_recommandation_display', read_only=True)
    est_approuve = serializers.SerializerMethodField()
    est_rejete = serializers.SerializerMethodField()
    categorie_couleur = serializers.SerializerMethodField()

    # Pour les champs JSON, nous les validons mais les traitons comme des strings
    facteurs_positifs = serializers.JSONField(
        required=False,
        help_text="Facteurs positifs au format JSON"
    )
    facteurs_negatifs = serializers.JSONField(
        required=False,
        help_text="Facteurs négatifs au format JSON"
    )
    valeurs_shap = serializers.JSONField(
        required=False,
        help_text="Valeurs SHAP au format JSON"
    )

    class Meta:
        model = ScoreRisque
        fields = [
            'id', 'demande_credit', 'demande_credit_info',
            'score', 'categorie_risque', 'categorie_risque_display',
            'facteurs_positifs', 'facteurs_negatifs', 'recommandation',
            'recommandation_display', 'seuil_approbation', 'seuil_rejet',
            'valeurs_shap', 'date_calcul', 'version_modele',
            'est_approuve', 'est_rejete', 'categorie_couleur'
        ]
        read_only_fields = ['date_calcul']

    def get_demande_credit_info(self, obj):
        """Retourne des informations sommaires sur la demande de crédit"""
        if obj.demande_credit:
            return {
                'id': obj.demande_credit.id,
                'client': str(obj.demande_credit.client),
                'montant': float(obj.demande_credit.montant_demande),
                'duree': obj.demande_credit.duree_mois
            }
        return None

    def get_est_approuve(self, obj):
        return obj.est_approuve()

    def get_est_rejete(self, obj):
        return obj.est_rejete()

    def get_categorie_couleur(self, obj):
        return obj.get_categorie_couleur()

    def validate_score(self, value):
        """Valide que le score est entre 0 et 100"""
        if not (0 <= value <= 100):
            raise serializers.ValidationError(
                "Le score de risque doit être compris entre 0 et 100."
            )
        return value

    def validate(self, data):
        """Validation croisée des seuils"""
        seuil_approbation = data.get('seuil_approbation', self.instance.seuil_approbation if self.instance else 30)
        seuil_rejet = data.get('seuil_rejet', self.instance.seuil_rejet if self.instance else 70)
        score = data.get('score')

        # Vérifier la cohérence des seuils
        if seuil_approbation >= seuil_rejet:
            raise serializers.ValidationError({
                'seuil_approbation': "Le seuil d'approbation doit être inférieur au seuil de rejet.",
                'seuil_rejet': "Le seuil de rejet doit être supérieur au seuil d'approbation."
            })

        # Si un score est fourni, vérifier la cohérence avec les recommandations
        if score is not None:
            if score <= seuil_approbation and data.get('recommandation') != 'approbation':
                raise serializers.ValidationError({
                    'recommandation': f"Un score de {score}% devrait normalement entraîner une approbation (seuil: {seuil_approbation}%)."
                })
            elif score >= seuil_rejet and data.get('recommandation') != 'rejet':
                raise serializers.ValidationError({
                    'recommandation': f"Un score de {score}% devrait normalement entraîner un rejet (seuil: {seuil_rejet}%)."
                })

        return data


# Serializers pour les requêtes spécifiques
class CalculScoreSerializer(serializers.Serializer):
    """
    Serializer pour le calcul de score de risque
    """

    demande_credit_id = serializers.IntegerField(
        required=True,
        help_text="ID de la demande de crédit à évaluer"
    )

    force_recalcul = serializers.BooleanField(
        default=False,
        help_text="Forcer le recalcul même si un score existe déjà"
    )

    inclure_explications = serializers.BooleanField(
        default=True,
        help_text="Inclure les explications SHAP dans le résultat"
    )


class SimulationCreditSerializer(serializers.Serializer):
    """
    Serializer pour les simulations de crédit
    """

    client_id = serializers.IntegerField(
        required=True,
        help_text="ID du client pour la simulation"
    )

    scenarios = serializers.ListField(
        child=serializers.DictField(),
        help_text="Liste des scénarios à simuler"
    )

    def validate_scenarios(self, value):
        """Valide la structure des scénarios"""
        for scenario in value:
            if 'nom' not in scenario:
                raise serializers.ValidationError("Chaque scénario doit avoir un 'nom'")
            if 'parametres' not in scenario:
                raise serializers.ValidationError("Chaque scénario doit avoir des 'parametres'")

        return value


class ExplicationScoreSerializer(serializers.Serializer):
    """
    Serializer pour les explications de score
    """

    score_id = serializers.IntegerField(
        required=True,
        help_text="ID du score à expliquer"
    )

    format = serializers.ChoiceField(
        choices=['texte', 'graphique', 'complet'],
        default='complet',
        help_text="Format de l'explication"
    )


# Serializer pour les données d'entrée du modèle ML
class DonneesModeleSerializer(serializers.Serializer):
    """
    Serializer pour les données d'entrée du modèle ML
    Utilisé pour les appels directs à l'API de prédiction
    """

    age = serializers.IntegerField(
        min_value=18,
        max_value=100,
        help_text="Âge du client"
    )

    profession = serializers.ChoiceField(
        choices=[c[0] for c in Client.TYPE_PROFESSION],
        help_text="Type de profession"
    )

    anciennete_emploi = serializers.IntegerField(
        min_value=0,
        help_text="Ancienneté dans l'emploi (mois)"
    )

    revenu_mensuel = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        help_text="Revenu mensuel net (€)"
    )

    dette_totale = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        help_text="Dette totale actuelle (€)"
    )

    defauts_paiement = serializers.IntegerField(
        min_value=0,
        help_text="Nombre de défauts de paiement antérieurs"
    )

    nombre_enfants = serializers.IntegerField(
        min_value=0,
        default=0,
        help_text="Nombre d'enfants à charge"
    )