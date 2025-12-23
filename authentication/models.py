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

    def __str__(self):
        return self.username
