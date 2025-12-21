from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

class Course(models.Model):
    titre = models.CharField(max_length=255)
    ingredient = models.TextField()  

    def __str__(self):
        return self.titre

class Panier(models.Model):
    """
    Modèle représentant un panier de courses d'un utilisateur.

    Attributes:
        date_creation: Date et heure de création du panier
        user: Utilisateur propriétaire du panier
        courses: Courses associées au panier (relation Many-to-Many)
        notification_sent: Indicateur si la notification de rappel a été envoyée
        notification_sent_date: Date d'envoi de la notification
    """
    date_creation = models.DateTimeField(auto_now_add=True)

    # relation 1-N avec User
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='paniers'
    )

    # relation N-N avec Course
    courses = models.ManyToManyField(Course, related_name='paniers', blank=True)

    # Suivi des notifications
    notification_sent = models.BooleanField(
        default=False,
        help_text="Indique si la notification de rappel (14 jours) a été envoyée"
    )
    notification_sent_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date et heure d'envoi de la notification"
    )

    class Meta:
        ordering = ['-date_creation']
        verbose_name = "Panier"
        verbose_name_plural = "Paniers"

    def __str__(self):
        return f"Panier {self.id} de {self.user.username}"

    @property
    def age_in_days(self):
        """Retourne l'âge du panier en jours."""
        from django.utils import timezone
        delta = timezone.now() - self.date_creation
        return delta.days