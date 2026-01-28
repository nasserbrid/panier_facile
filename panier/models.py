from django.conf import settings
from django.db import models


class Course(models.Model):
    titre = models.CharField(max_length=255)
    ingredient = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='courses_created',
        verbose_name="Cree par",
        help_text="Utilisateur qui a cree cette course"
    )

    def __str__(self):
        return self.titre


class Panier(models.Model):
    """
    Modele representant un panier de courses d'un utilisateur.

    Attributes:
        date_creation: Date et heure de creation du panier
        user: Utilisateur proprietaire du panier
        courses: Courses associees au panier (relation Many-to-Many)
        notification_sent: Indicateur si la notification de rappel a ete envoyee
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
        help_text="Indique si la notification de rappel (14 jours) a ete envoyee"
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
        """Retourne l'age du panier en jours."""
        from django.utils import timezone
        delta = timezone.now() - self.date_creation
        return delta.days


class Ingredient(models.Model):
    """
    Modele representant un ingredient dans un panier.
    """
    nom = models.CharField(max_length=255)
    quantite = models.CharField(max_length=50, blank=True)
    unite = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Ingredient"
        verbose_name_plural = "Ingredients"

    def __str__(self):
        return f"{self.nom} ({self.quantite} {self.unite})".strip()


class IngredientPanier(models.Model):
    """
    Modele de liaison entre Panier et Ingredient (Many-to-Many avec attributs).
    """
    panier = models.ForeignKey(Panier, on_delete=models.CASCADE, related_name='ingredient_paniers')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='ingredient_paniers')
    quantite = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    checked = models.BooleanField(default=False, help_text="Indique si l'ingredient a ete coche")

    class Meta:
        unique_together = [['panier', 'ingredient']]
        verbose_name = "Ingredient du panier"
        verbose_name_plural = "Ingredients du panier"

    def __str__(self):
        return f"{self.ingredient.nom} dans {self.panier}"
