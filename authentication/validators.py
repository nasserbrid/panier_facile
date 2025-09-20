from django.core.exceptions import ValidationError


class ContainsLetterValidator:
    """
    Validateur personnalisé pour les mots de passe.
    
    Vérifie que le mot de passe contient au moins une lettre (majuscule ou minuscule).
    """
    def validate(self, password, user=None):
        """
        Valide que le mot de passe contient au moins une lettre.
        """
        if not any(char.isalpha() for char in password):
            raise ValidationError("Le mot de passe doit contenir une lettre", code='password_no_letters')
    
    def get_help_text(self):
        """
        Retourne le message d'aide pour le validateur.
        """
        return 'Votre mot de passe doit contenir au moins une lettre majuscule ou minuscule.'