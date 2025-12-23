from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ImproperlyConfigured

# Import GeoDjango pour la production
try:
    from django.contrib.gis.db import models as gis_models
    HAS_GIS = True
except (ImportError, ImproperlyConfigured):
    HAS_GIS = False

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

# Ajouter le champ location selon la disponibilité de GeoDjango
if HAS_GIS:
    # Production avec PostGIS
    User.add_to_class(
        'location',
        gis_models.PointField(
            blank=True,
            null=True,
            srid=4326,
            verbose_name="Coordonnées GPS",
            help_text="Position géographique (latitude, longitude)"
        )
    )
else:
    # Développement local sans GeoDjango
    User.add_to_class(
        'location',
        models.CharField(
            max_length=100,
            blank=True,
            null=True,
            verbose_name="Coordonnées GPS",
            help_text="Format: 'latitude,longitude'"
        )
    )
