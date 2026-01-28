"""
Modeles pour les messages de contact et les avis clients.
"""
from django.db import models


class ContactMessage(models.Model):
    """
    Modele pour stocker les messages de contact des utilisateurs.
    """
    name = models.CharField(max_length=100, verbose_name="Nom")
    email = models.EmailField(verbose_name="Email")
    subject = models.CharField(max_length=200, verbose_name="Sujet")
    message = models.TextField(verbose_name="Message")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'envoi")
    is_read = models.BooleanField(default=False, verbose_name="Lu")
    is_replied = models.BooleanField(default=False, verbose_name="Repondu")

    class Meta:
        db_table = 'panier_contactmessage'  # Garde la table existante
        ordering = ['-created_at']
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"

    def __str__(self):
        return f"{self.name} - {self.subject} ({self.created_at.strftime('%d/%m/%Y')})"


class CustomerReview(models.Model):
    """
    Modele pour stocker les avis clients.
    """
    RATING_CHOICES = [
        (1, '1 etoile'),
        (2, '2 etoiles'),
        (3, '3 etoiles'),
        (4, '4 etoiles'),
        (5, '5 etoiles'),
    ]

    name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nom",
        help_text="Nom du client (peut etre anonyme)"
    )
    email = models.EmailField(
        blank=True,
        verbose_name="Email",
        help_text="Email du client (non publie)"
    )
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        verbose_name="Note"
    )
    title = models.CharField(max_length=200, verbose_name="Titre")
    review = models.TextField(verbose_name="Avis")
    would_recommend = models.BooleanField(default=False, verbose_name="Recommande")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de creation")
    is_approved = models.BooleanField(default=False, verbose_name="Approuve")
    is_featured = models.BooleanField(default=False, verbose_name="Mis en avant")

    class Meta:
        db_table = 'panier_customerreview'  # Garde la table existante
        ordering = ['-created_at']
        verbose_name = "Avis client"
        verbose_name_plural = "Avis clients"

    def __str__(self):
        author = self.name if self.name else "Anonyme"
        return f"{author} - {self.rating}/5 etoiles ({self.created_at.strftime('%d/%m/%Y')})"

    @property
    def stars_display(self):
        """Retourne l'affichage en etoiles"""
        return '*' * self.rating
