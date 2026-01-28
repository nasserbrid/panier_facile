"""
Modèles pour l'intégration Carrefour.
"""
from django.db import models


class CarrefourProductMatch(models.Model):
    """
    Modèle représentant la correspondance entre un ingrédient PanierFacile
    et un produit Carrefour.

    Ce modèle sert de cache pour les produits récupérés via scraping.
    """
    ingredient = models.ForeignKey(
        'panier.Ingredient',
        on_delete=models.CASCADE,
        related_name='carrefour_matches'
    )
    store_id = models.CharField(
        max_length=20,
        default='scraping',
        help_text="Identifiant du magasin Carrefour ou 'scraping'"
    )

    # Détails du produit (cache)
    product_name = models.CharField(
        max_length=255,
        help_text="Nom du produit"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Prix unitaire du produit"
    )
    product_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL du produit sur le site Carrefour"
    )
    is_available = models.BooleanField(
        default=True,
        help_text="Disponibilité du produit"
    )

    # Métadonnées du matching
    match_score = models.FloatField(
        default=0.0,
        help_text="Score de pertinence du matching (0.0 à 1.0)"
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text="Date de dernière mise à jour du match"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date de création du match"
    )

    class Meta:
        db_table = 'panier_carrefourproductmatch'
        indexes = [
            models.Index(fields=['ingredient', 'store_id']),
            models.Index(fields=['store_id', 'last_updated']),
        ]
        verbose_name = "Correspondance produit Carrefour"
        verbose_name_plural = "Correspondances produits Carrefour"

    def __str__(self):
        return f"{self.ingredient.nom} → {self.product_name} (Magasin {self.store_id})"

    @property
    def display_name(self):
        """Retourne le nom du produit."""
        return self.product_name or "Produit inconnu"

    @property
    def display_price(self):
        """Retourne le prix du produit."""
        return self.price or 0
