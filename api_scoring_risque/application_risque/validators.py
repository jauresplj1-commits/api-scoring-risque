"""
Validateurs personnalisés pour les données sensibles
"""

import re
from django.core.validators import ValidationError
from django.utils.translation import gettext_lazy as _
from datetime import date
import phonenumbers


class ValidateurDonneesSensibles:
    """
    Classe de validation pour les données financières sensibles
    """

    @staticmethod
    def valider_email(email):
        """Valide l'email avec des règles spécifiques"""
        if not email:
            raise ValidationError(_("L'email est requis."))

        # Vérifier le format de l'email
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValidationError(_("Format d'email invalide."))

        # Vérifier les domaines suspects
        domaines_suspects = ['example.com', 'test.com', 'mailinator.com']
        domaine = email.split('@')[1]
        if domaine in domaines_suspects:
            raise ValidationError(_("Les emails temporaires ne sont pas acceptés."))

        return email

    @staticmethod
    def valider_telephone(telephone):
        """Valide le numéro de téléphone"""
        if not telephone:
            raise ValidationError(_("Le numéro de téléphone est requis."))

        try:
            # Essayer de parser le numéro avec phonenumbers
            numero_parse = phonenumbers.parse(telephone, "FR")

            if not phonenumbers.is_valid_number(numero_parse):
                raise ValidationError(_("Numéro de téléphone invalide."))

            # Formater le numéro
            return phonenumbers.format_number(numero_parse, phonenumbers.PhoneNumberFormat.E164)

        except phonenumbers.NumberParseException:
            # Si phonenumbers échoue, utiliser une validation basique
            pattern = r'^\+?[0-9\s\-\(\)]{10,15}$'
            if not re.match(pattern, telephone):
                raise ValidationError(_("Format de téléphone invalide. Utilisez le format international."))

            return telephone

    @staticmethod
    def valider_date_naissance(date_naissance):
        """Valide la date de naissance"""
        if not date_naissance:
            raise ValidationError(_("La date de naissance est requise."))

        aujourdhui = date.today()

        # Vérifier que la date n'est pas dans le futur
        if date_naissance > aujourdhui:
            raise ValidationError(_("La date de naissance ne peut pas être dans le futur."))

        # Calculer l'âge
        age = aujourdhui.year - date_naissance.year

        # Ajuster si l'anniversaire n'est pas encore passé cette année
        if (aujourdhui.month, aujourdhui.day) < (date_naissance.month, date_naissance.day):
            age -= 1

        # Vérifier l'âge minimum
        if age < 18:
            raise ValidationError(_("Le client doit avoir au moins 18 ans."))

        # Vérifier l'âge maximum raisonnable
        if age > 120:
            raise ValidationError(_("L'âge semble invalide."))

        return date_naissance

    @staticmethod
    def valider_revenu(revenu):
        """Valide le revenu"""
        if revenu is None:
            raise ValidationError(_("Le revenu est requis."))

        if revenu < 0:
            raise ValidationError(_("Le revenu ne peut pas être négatif."))

        # Vérifier les valeurs extrêmes
        if revenu > 1000000:  # 1 million € par mois
            raise ValidationError(_("Le revenu semble excessivement élevé."))

        return revenu

    @staticmethod
    def valider_dette(dette):
        """Valide le montant de la dette"""
        if dette is None:
            raise ValidationError(_("Le montant de la dette est requis."))

        if dette < 0:
            raise ValidationError(_("La dette ne peut pas être négative."))

        # Vérifier les valeurs extrêmes
        if dette > 10000000:  # 10 millions €
            raise ValidationError(_("Le montant de la dette semble excessivement élevé."))

        return dette

    @staticmethod
    def valider_montant_credit(montant):
        """Valide le montant du crédit demandé"""
        if montant is None:
            raise ValidationError(_("Le montant du crédit est requis."))

        if montant <= 0:
            raise ValidationError(_("Le montant du crédit doit être positif."))

        # Vérifier les valeurs extrêmes
        if montant > 5000000:  # 5 millions €
            raise ValidationError(_("Le montant du crédit semble excessivement élevé."))

        # Vérifier le minimum
        if montant < 100:
            raise ValidationError(_("Le montant du crédit est trop faible."))

        return montant

    @staticmethod
    def valider_taux_interet(taux):
        """Valide le taux d'intérêt"""
        if taux is None:
            raise ValidationError(_("Le taux d'intérêt est requis."))

        if taux < 0:
            raise ValidationError(_("Le taux d'intérêt ne peut pas être négatif."))

        if taux > 50:  # 50% maximum
            raise ValidationError(_("Le taux d'intérêt semble excessivement élevé."))

        return taux

    @staticmethod
    def valider_ratio_dette_revenu(dette, revenu):
        """Valide le ratio dette/revenu"""
        if revenu == 0:
            return float('inf')

        ratio = (dette / revenu) * 100

        # Avertissement pour les ratios élevés
        if ratio > 500:  # 500% du revenu
            raise ValidationError(
                _(f"Le ratio dette/revenu ({ratio:.1f}%) est excessivement élevé.")
            )

        return ratio

    @staticmethod
    def valider_coherence_donnees_client(client_data):
        """Valide la cohérence globale des données client"""
        erreurs = {}

        # Vérifier la cohérence âge/ancienneté emploi
        age = client_data.get('age')
        anciennete_emploi = client_data.get('anciennete_emploi', 0)  # en mois

        if age and anciennete_emploi:
            # L'ancienneté ne peut pas dépasser l'âge - 16 ans (âge d'entrée sur le marché du travail)
            anciennete_max = (age - 16) * 12  # en mois
            if anciennete_emploi > anciennete_max:
                erreurs['anciennete_emploi'] = _(
                    f"L'ancienneté ({anciennete_emploi} mois) semble incompatible avec l'âge ({age} ans)."
                )

        # Vérifier la cohérence revenu/profession
        revenu = client_data.get('revenu_mensuel')
        profession = client_data.get('profession')

        if revenu and profession:
            # Revenus typiques par profession (en €/mois)
            revenus_typiques = {
                'sans_emploi': (0, 2000),
                'non_qualifie': (1000, 3000),
                'qualifie': (2000, 5000),
                'cadre': (3000, 10000),
                'independant': (0, 20000),  # Large fourchette
                'fonctionnaire': (1500, 6000),
            }

            if profession in revenus_typiques:
                min_typique, max_typique = revenus_typiques[profession]
                if revenu < min_typique or revenu > max_typique:
                    erreurs['revenu_mensuel'] = _(
                        f"Le revenu ({revenu}€) semble atypique pour la profession '{profession}'."
                    )

        if erreurs:
            raise ValidationError(erreurs)

        return True