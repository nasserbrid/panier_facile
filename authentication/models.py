from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.gis.db import models as gis_models

# Create your models here.

class User(AbstractUser):
    ADMIN = 'ADMIN'
    USER = 'USER'

    ROLE_CHOICES = (
        (ADMIN, 'Administrateur'),
        (USER, 'Utilisateur'),
    )

    role = models.CharField(max_length=30, choices=ROLE_CHOICES)

    # Champs de géolocalisation
    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Adresse complète",
        help_text="Adresse postale de l'utilisateur"
    )

    location = gis_models.PointField(
        blank=True,
        null=True,
        srid=4326,  # WGS84 (GPS standard)
        verbose_name="Coordonnées GPS",
        help_text="Position géographique (latitude, longitude)"
    )

    # Champs d'abonnement
    trial_end_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fin de la période d'essai",
        help_text="Date de fin des 3 mois gratuits"
    )

    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ('trial', 'Période d\'essai'),
            ('active', 'Abonnement actif'),
            ('expired', 'Expiré'),
            ('canceled', 'Annulé'),
        ],
        default='trial',
        verbose_name="Statut de l'abonnement"
    )

    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="ID Client Stripe"
    )

    stripe_subscription_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="ID Abonnement Stripe"
    )

    def __str__(self):
        return self.username

    @property
    def has_active_subscription(self):
        '''
        Vérifie si l'utilisateur a un accès actif (période d'essai ou abonnement payant).
        '''
        from django.utils import timezone

        if self.subscription_status == 'active':
            return True

        if self.subscription_status == 'trial' and self.trial_end_date:
            return timezone.now() < self.trial_end_date

        return False

    @property
    def days_remaining(self):
        '''
        Retourne le nombre de jours restants dans la période d'essai.
        '''
        from django.utils import timezone

        if self.subscription_status == 'trial' and self.trial_end_date:
            delta = self.trial_end_date - timezone.now()
            return max(0, delta.days)

        return 0
