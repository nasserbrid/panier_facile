"""
Modèles pour l'intégration Lidl.
"""
from django.db import models


class LidlProductMatch(models.Model):
    """
    Cache pour les produits Lidl matchés.
    Similaire à LeclercProductMatch mais pour Lidl.
    """
    ingredient = models.ForeignKey(
        'panier.Ingredient',
        on_delete=models.CASCADE,
        related_name='lidl_matches'
    )
    store_id = models.CharField(
        max_length=20,
        default='scraping',
        help_text="ID du magasin Lidl (ou 'scraping' pour recherche générale)"
    )
    product_name = models.CharField(max_length=255)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    product_url = models.URLField(blank=True, null=True)
    image_url = models.URLField(blank=True, null=True)
    is_available = models.BooleanField(default=True)
    match_score = models.FloatField(
        default=0.0,
        help_text="Score de correspondance avec l'ingrédient (0-1)"
    )
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'supermarkets_lidlproductmatch'
        indexes = [
            models.Index(fields=['ingredient', 'store_id']),
            models.Index(fields=['store_id', 'last_updated']),
        ]
        verbose_name = "Produit Lidl matché"
        verbose_name_plural = "Produits Lidl matchés"

    def __str__(self):
        return f"{self.ingredient.nom} -> {self.product_name} ({self.price}€)"
