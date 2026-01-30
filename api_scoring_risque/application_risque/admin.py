"""
Configuration de l'interface d'administration Django
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Client, HistoriqueFinancier, DemandeCredit, ScoreRisque


class HistoriqueFinancierInline(admin.StackedInline):
    """Inline pour l'historique financier dans l'admin Client"""
    model = HistoriqueFinancier
    can_delete = False
    verbose_name_plural = "Historique Financier"
    fields = (
        'solde_compte', 'epargne', 'dette_cartes', 'dette_autres',
        'nb_credits_anterieurs', 'defauts_paiement', 'duree_relation_banque',
        'depenses_logement', 'depenses_autres'
    )


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Administration des clients"""

    list_display = ('nom_complet', 'age', 'profession', 'revenu_total', 'date_creation')
    list_filter = ('profession', 'etat_civil', 'date_creation')
    search_fields = ('nom', 'prenom', 'email')
    readonly_fields = ('date_creation', 'date_modification', 'age')
    inlines = [HistoriqueFinancierInline]

    fieldsets = (
        ('Informations Personnelles', {
            'fields': ('nom', 'prenom', 'email', 'telephone')
        }),
        ('Démographie', {
            'fields': ('date_naissance', 'age', 'etat_civil', 'nombre_enfants')
        }),
        ('Profession et Revenus', {
            'fields': ('profession', 'anciennete_emploi', 'revenu_mensuel', 'autres_revenus')
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )

    def nom_complet(self, obj):
        return f"{obj.prenom} {obj.nom}"

    nom_complet.short_description = "Nom complet"

    def revenu_total(self, obj):
        return f"{obj.revenu_total()} €"

    revenu_total.short_description = "Revenu total"


@admin.register(HistoriqueFinancier)
class HistoriqueFinancierAdmin(admin.ModelAdmin):
    """Administration des historiques financiers"""

    list_display = ('client', 'dette_totale', 'ratio_dette_revenu', 'solde_compte')
    list_filter = ('client__profession',)
    search_fields = ('client__nom', 'client__prenom')
    readonly_fields = ('date_creation', 'date_modification')

    fieldsets = (
        ('Client', {
            'fields': ('client',)
        }),
        ('Comptes et Épargne', {
            'fields': ('solde_compte', 'epargne')
        }),
        ('Dettes', {
            'fields': ('dette_cartes', 'dette_autres')
        }),
        ('Historique de Crédit', {
            'fields': ('nb_credits_anterieurs', 'defauts_paiement', 'duree_relation_banque')
        }),
        ('Dépenses', {
            'fields': ('depenses_logement', 'depenses_autres')
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )

    def ratio_dette_revenu(self, obj):
        return f"{obj.ratio_dette_revenu():.1f}%"

    ratio_dette_revenu.short_description = "Ratio dette/revenu"


class ScoreRisqueInline(admin.StackedInline):
    """Inline pour le score de risque dans l'admin DemandeCredit"""
    model = ScoreRisque
    can_delete = False
    verbose_name_plural = "Score de Risque"
    readonly_fields = ('score', 'categorie_risque', 'recommandation', 'date_calcul')
    fields = ('score', 'categorie_risque', 'recommandation', 'seuil_approbation', 'seuil_rejet')


@admin.register(DemandeCredit)
class DemandeCreditAdmin(admin.ModelAdmin):
    """Administration des demandes de crédit"""

    list_display = ('client', 'type_credit', 'montant_demande', 'duree_mois',
                    'statut_colore', 'date_demande')
    list_filter = ('type_credit', 'statut', 'date_demande')
    search_fields = ('client__nom', 'client__prenom', 'destination_credit')
    readonly_fields = ('date_demande', 'date_traitement', 'mensualite',
                       'montant_total', 'cout_total_interets')
    inlines = [ScoreRisqueInline]

    fieldsets = (
        ('Client', {
            'fields': ('client',)
        }),
        ('Détails du Crédit', {
            'fields': ('type_credit', 'montant_demande', 'duree_mois',
                       'taux_interet', 'destination_credit')
        }),
        ('Garanties', {
            'fields': ('avec_garantie', 'valeur_garantie')
        }),
        ('Statut', {
            'fields': ('statut', 'date_echeance', 'commentaires')
        }),
        ('Calculs', {
            'fields': ('mensualite', 'montant_total', 'cout_total_interets'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('date_demande', 'date_traitement'),
            'classes': ('collapse',)
        }),
    )

    def statut_colore(self, obj):
        """Affiche le statut avec une couleur"""
        couleurs = {
            'en_attente': 'orange',
            'en_cours': 'blue',
            'approuve': 'green',
            'rejete': 'red',
            'annule': 'gray',
        }
        couleur = couleurs.get(obj.statut, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            couleur,
            obj.get_statut_display()
        )

    statut_colore.short_description = "Statut"

    def mensualite(self, obj):
        return f"{obj.mensualite()} €"

    mensualite.short_description = "Mensualité"

    def montant_total(self, obj):
        return f"{obj.montant_total()} €"

    montant_total.short_description = "Montant total"

    def cout_total_interets(self, obj):
        return f"{obj.cout_total_interets()} €"

    cout_total_interets.short_description = "Coût des intérêts"


@admin.register(ScoreRisque)
class ScoreRisqueAdmin(admin.ModelAdmin):
    """Administration des scores de risque"""

    list_display = ('demande_credit', 'score_colore', 'categorie_risque_coloree',
                    'recommandation', 'date_calcul')
    list_filter = ('categorie_risque', 'recommandation', 'date_calcul')
    search_fields = ('demande_credit__client__nom', 'demande_credit__client__prenom')
    readonly_fields = ('date_calcul', 'score', 'categorie_risque', 'recommandation')

    fieldsets = (
        ('Demande de Crédit', {
            'fields': ('demande_credit',)
        }),
        ('Score et Catégorie', {
            'fields': ('score', 'categorie_risque', 'recommandation')
        }),
        ('Seuils de Décision', {
            'fields': ('seuil_approbation', 'seuil_rejet')
        }),
        ('Facteurs Contributifs', {
            'fields': ('facteurs_positifs', 'facteurs_negatifs'),
            'classes': ('collapse',)
        }),
        ('Explicabilité', {
            'fields': ('valeurs_shap',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('version_modele', 'date_calcul'),
            'classes': ('collapse',)
        }),
    )

    def score_colore(self, obj):
        """Affiche le score avec une couleur basée sur la catégorie"""
        couleurs = {
            'faible': 'green',
            'modere': 'orange',
            'eleve': 'red',
            'tres_eleve': 'darkred',
        }
        couleur = couleurs.get(obj.categorie_risque, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            couleur,
            obj.score
        )

    score_colore.short_description = "Score"

    def categorie_risque_coloree(self, obj):
        """Affiche la catégorie de risque avec une couleur"""
        couleurs = {
            'faible': 'green',
            'modere': 'orange',
            'eleve': 'red',
            'tres_eleve': 'darkred',
        }
        couleur = couleurs.get(obj.categorie_risque, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            couleur,
            obj.get_categorie_risque_display()
        )

    categorie_risque_coloree.short_description = "Catégorie de risque"