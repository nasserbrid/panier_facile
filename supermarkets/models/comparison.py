"""
Modèle pour la comparaison de prix entre supermarchés.
"""
from django.conf import settings
from django.db import models


class PriceComparison(models.Model):
    """
    Stocke une session de comparaison de prix pour un panier.

    Chaque comparaison enregistre les totaux calculés pour chaque supermarché
    et permet de retrouver facilement le moins cher.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='price_comparisons'
    )
    panier = models.ForeignKey(
        'panier.Panier',
        on_delete=models.CASCADE,
        related_name='price_comparisons'
    )

    # Localisation utilisée pour la comparaison
    latitude = models.FloatField(
        help_text="Latitude de l'utilisateur lors de la comparaison"
    )
    longitude = models.FloatField(
        help_text="Longitude de l'utilisateur lors de la comparaison"
    )

    # Totaux par supermarché (null si non disponible)
    leclerc_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total estimé chez E.Leclerc"
    )
    aldi_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total estimé chez Aldi"
    )

    # Compteurs de produits trouvés
    leclerc_found = models.IntegerField(
        default=0,
        help_text="Nombre de produits trouvés chez E.Leclerc"
    )
    aldi_found = models.IntegerField(
        default=0,
        help_text="Nombre de produits trouvés chez Aldi"
    )
    total_ingredients = models.IntegerField(
        default=0,
        help_text="Nombre total d'ingrédients dans le panier"
    )

    # Recommandation
    cheapest_supermarket = models.CharField(
        max_length=20,
        blank=True,
        help_text="Nom du supermarché le moins cher (leclerc, aldi)"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date de création de la comparaison"
    )

    class Meta:
        db_table = 'supermarkets_pricecomparison'
        ordering = ['-created_at']
        verbose_name = "Comparaison de prix"
        verbose_name_plural = "Comparaisons de prix"

    def __str__(self):
        return f"Comparaison #{self.id} - Panier #{self.panier_id} ({self.created_at.strftime('%d/%m/%Y')})"

    def calculate_cheapest(self):
        """Détermine le supermarché le moins cher et met à jour le champ."""
        totals = {}
        if self.leclerc_total is not None:
            totals['leclerc'] = self.leclerc_total
        if self.aldi_total is not None:
            totals['aldi'] = self.aldi_total

        if totals:
            self.cheapest_supermarket = min(totals, key=totals.get)
        else:
            self.cheapest_supermarket = ''

    def save(self, *args, **kwargs):
        """Calcule automatiquement le supermarché le moins cher avant la sauvegarde."""
        self.calculate_cheapest()
        super().save(*args, **kwargs)

    @property
    def savings(self):
        """Calcule l'économie potentielle entre le plus cher et le moins cher."""
        totals = []
        if self.leclerc_total is not None:
            totals.append(self.leclerc_total)
        if self.aldi_total is not None:
            totals.append(self.aldi_total)

        if len(totals) >= 2:
            return max(totals) - min(totals)
        return None
