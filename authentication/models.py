from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    ADMIN = 'ADMIN'
    USER = 'USER'
    
    ROLE_CHOICES = (
        (ADMIN, 'Administrateur'),
        (USER, 'Utilisateur'),
    )
    
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
