from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import User


@receiver(post_save, sender=User)
def assign_trial_period(sender, instance, created, **kwargs):
    """
    Assigne automatiquement une période d'essai de 3 mois (90 jours)
    à chaque nouvel utilisateur lors de sa création.

    Args:
        sender: Le modèle User
        instance: L'instance de l'utilisateur créé
        created: Boolean - True si c'est une nouvelle création
        **kwargs: Arguments supplémentaires
    """
    if created:
        # Calculer la date de fin de la période d'essai (90 jours à partir de maintenant)
        trial_duration = timedelta(days=90)
        trial_end = timezone.now() + trial_duration

        # Assigner la période d'essai à l'utilisateur
        instance.trial_end_date = trial_end
        instance.subscription_status = 'trial'

        # Sauvegarder les modifications
        # update_fields évite les boucles infinies de signaux
        instance.save(update_fields=['trial_end_date', 'subscription_status'])

        # Log pour le débogage (optionnel)
        print(f"✓ Période d'essai de 90 jours attribuée à {instance.username}")
        print(f"  Fin de l'essai: {trial_end.strftime('%d/%m/%Y')}")
