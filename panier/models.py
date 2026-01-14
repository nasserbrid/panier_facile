from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

class Course(models.Model):
    titre = models.CharField(max_length=255)
    ingredient = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='courses_created',
        verbose_name="Créé par",
        help_text="Utilisateur qui a créé cette course"
    )

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


class Ingredient(models.Model):
    """
    Modèle représentant un ingrédient dans un panier.
    """
    nom = models.CharField(max_length=255)
    quantite = models.CharField(max_length=50, blank=True)
    unite = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Ingrédient"
        verbose_name_plural = "Ingrédients"

    def __str__(self):
        return f"{self.nom} ({self.quantite} {self.unite})".strip()


class IngredientPanier(models.Model):
    """
    Modèle de liaison entre Panier et Ingredient (Many-to-Many avec attributs).
    """
    panier = models.ForeignKey(Panier, on_delete=models.CASCADE, related_name='ingredient_paniers')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='ingredient_paniers')
    quantite = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    checked = models.BooleanField(default=False, help_text="Indique si l'ingrédient a été coché")

    class Meta:
        unique_together = [['panier', 'ingredient']]
        verbose_name = "Ingrédient du panier"
        verbose_name_plural = "Ingrédients du panier"

    def __str__(self):
        return f"{self.ingredient.nom} dans {self.panier}"


class IntermarcheProductMatch(models.Model):
    """
    Modèle représentant la correspondance entre un ingrédient PanierFacile
    et un produit Intermarché.

    Ce modèle sert de cache pour les produits récupérés via API ou scraping.
    """
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='intermarche_matches'
    )
    store_id = models.CharField(
        max_length=20,
        default='scraping',
        help_text="Identifiant du magasin Intermarché (ex: 08177) ou 'scraping'"
    )

    # Informations produit Intermarché
    intermarche_product_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="ID unique du produit Intermarché (API uniquement)"
    )
    intermarche_product_ean13 = models.CharField(
        max_length=13,
        blank=True,
        help_text="Code-barres EAN13 du produit"
    )
    intermarche_item_parent_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="ID parent de l'item (pour les produits avec variantes)"
    )

    # Détails du produit (cache)
    product_name = models.CharField(
        max_length=255,
        help_text="Nom du produit (scraping)"
    )
    product_label = models.CharField(
        max_length=255,
        blank=True,
        help_text="Libellé du produit (API)"
    )
    product_brand = models.CharField(
        max_length=100,
        blank=True,
        help_text="Marque du produit"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Prix unitaire du produit"
    )
    product_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Prix unitaire du produit (API - deprecated, use price)"
    )
    product_url = models.URLField(
        blank=True,
        null=True,
        help_text="URL du produit sur le site Intermarché"
    )
    product_image_url = models.URLField(
        blank=True,
        help_text="URL de l'image du produit"
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
        indexes = [
            models.Index(fields=['ingredient', 'store_id']),
            models.Index(fields=['store_id', 'last_updated']),
        ]
        verbose_name = "Correspondance produit Intermarché"
        verbose_name_plural = "Correspondances produits Intermarché"

    def __str__(self):
        name = self.product_name or self.product_label
        return f"{self.ingredient.nom} → {name} (Magasin {self.store_id})"

    @property
    def display_name(self):
        """Retourne le nom du produit (compatible API et scraper)."""
        return self.product_name or self.product_label or "Produit inconnu"

    @property
    def display_price(self):
        """Retourne le prix du produit (compatible API et scraper)."""
        return self.price or self.product_price or 0


class IntermarcheCart(models.Model):
    """
    Modèle représentant un panier Intermarché créé depuis PanierFacile.

    Ce modèle stocke les informations de synchronisation avec l'API
    Intermarché pour permettre le suivi des paniers exportés.
    """
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé à Intermarché'),
        ('completed', 'Commande finalisée'),
        ('failed', 'Échec'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='intermarche_carts'
    )
    panier = models.ForeignKey(
        Panier,
        on_delete=models.CASCADE,
        related_name='intermarche_carts'
    )

    # Informations magasin
    store_id = models.CharField(
        max_length=20,
        help_text="Identifiant du magasin Intermarché"
    )
    store_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nom du magasin Intermarché"
    )

    # Identifiant du panier anonyme Intermarché
    anonymous_cart_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="UUID du panier anonyme côté Intermarché"
    )

    # Informations panier
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Montant total du panier en euros"
    )
    items_count = models.IntegerField(
        default=0,
        help_text="Nombre d'articles dans le panier"
    )

    # Statut et suivi
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    sync_response = models.JSONField(
        blank=True,
        null=True,
        help_text="Réponse complète de l'API Intermarché lors de la synchronisation"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Message d'erreur en cas d'échec"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date de création du panier Intermarché"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date de dernière mise à jour"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['store_id', 'created_at']),
        ]
        verbose_name = "Panier Intermarché"
        verbose_name_plural = "Paniers Intermarché"

    def __str__(self):
        return f"Panier Intermarché {self.id} - {self.user.username} (Magasin {self.store_id})"

    @property
    def intermarche_url(self):
        """
        Retourne l'URL du panier sur le site Intermarché Drive.
        """
        return f"https://www.intermarche.com/drive/panier?anonymousId={self.anonymous_cart_id}&storeId={self.store_id}"


class ContactMessage(models.Model):
    """
    Modèle pour stocker les messages de contact des utilisateurs.
    """
    name = models.CharField(max_length=100, verbose_name="Nom")
    email = models.EmailField(verbose_name="Email")
    subject = models.CharField(max_length=200, verbose_name="Sujet")
    message = models.TextField(verbose_name="Message")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date d'envoi")
    is_read = models.BooleanField(default=False, verbose_name="Lu")
    is_replied = models.BooleanField(default=False, verbose_name="Répondu")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"

    def __str__(self):
        return f"{self.name} - {self.subject} ({self.created_at.strftime('%d/%m/%Y')})"


class CarrefourProductMatch(models.Model):
    """
    Modèle représentant la correspondance entre un ingrédient PanierFacile
    et un produit Carrefour.

    Ce modèle sert de cache pour les produits récupérés via scraping.
    """
    ingredient = models.ForeignKey(
        Ingredient,
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


class CarrefourCart(models.Model):
    """
    Modèle représentant un panier Carrefour créé depuis PanierFacile.
    """
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé à Carrefour'),
        ('completed', 'Commande finalisée'),
        ('failed', 'Échec'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='carrefour_carts'
    )
    panier = models.ForeignKey(
        Panier,
        on_delete=models.CASCADE,
        related_name='carrefour_carts'
    )

    # Informations magasin
    store_id = models.CharField(
        max_length=20,
        help_text="Identifiant du magasin Carrefour"
    )
    store_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Nom du magasin Carrefour"
    )

    # Informations panier
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Montant total du panier en euros"
    )
    items_count = models.IntegerField(
        default=0,
        help_text="Nombre d'articles dans le panier"
    )

    # Statut et suivi
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    error_message = models.TextField(
        blank=True,
        help_text="Message d'erreur en cas d'échec"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date de création du panier Carrefour"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date de dernière mise à jour"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['store_id', 'created_at']),
        ]
        verbose_name = "Panier Carrefour"
        verbose_name_plural = "Paniers Carrefour"

    def __str__(self):
        return f"Panier Carrefour {self.id} - {self.user.username} (Magasin {self.store_id})"


class AuchanProductMatch(models.Model):
    """
    Cache pour les produits Auchan matchés.
    Similaire à CarrefourProductMatch mais pour Auchan Drive.
    """
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='auchan_matches'
    )
    store_id = models.CharField(
        max_length=20,
        default='scraping',
        help_text="ID du magasin Auchan (ou 'scraping' pour recherche générale)"
    )
    product_name = models.CharField(max_length=255)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    product_url = models.URLField(blank=True, null=True)
    is_available = models.BooleanField(default=True)
    match_score = models.FloatField(
        default=0.0,
        help_text="Score de correspondance avec l'ingrédient (0-1)"
    )
    image_url = models.URLField(blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['ingredient', 'store_id']),
            models.Index(fields=['store_id', 'last_updated']),
        ]
        verbose_name = "Produit Auchan matché"
        verbose_name_plural = "Produits Auchan matchés"

    def __str__(self):
        return f"{self.ingredient.nom} -> {self.product_name} ({self.price}€)"


class AuchanCart(models.Model):
    """
    Panier Auchan créé depuis PanierFacile.
    Similaire à CarrefourCart mais pour Auchan Drive.
    """
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('completed', 'Complété'),
        ('exported', 'Exporté'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='auchan_carts'
    )
    panier = models.ForeignKey(
        Panier,
        on_delete=models.CASCADE,
        related_name='auchan_carts'
    )
    store_id = models.CharField(max_length=20)
    store_name = models.CharField(max_length=255, blank=True)
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    items_count = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Panier Auchan"
        verbose_name_plural = "Paniers Auchan"

    def __str__(self):
        return f"Panier Auchan {self.id} - {self.user.username} (Magasin {self.store_id})"


class CustomerReview(models.Model):
    """
    Modèle pour stocker les avis clients.
    """
    RATING_CHOICES = [
        (1, '1 étoile'),
        (2, '2 étoiles'),
        (3, '3 étoiles'),
        (4, '4 étoiles'),
        (5, '5 étoiles'),
    ]

    name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nom",
        help_text="Nom du client (peut être anonyme)"
    )
    email = models.EmailField(
        blank=True,
        verbose_name="Email",
        help_text="Email du client (non publié)"
    )
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        verbose_name="Note"
    )
    title = models.CharField(max_length=200, verbose_name="Titre")
    review = models.TextField(verbose_name="Avis")
    would_recommend = models.BooleanField(default=False, verbose_name="Recommande")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    is_approved = models.BooleanField(default=False, verbose_name="Approuvé")
    is_featured = models.BooleanField(default=False, verbose_name="Mis en avant")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Avis client"
        verbose_name_plural = "Avis clients"

    def __str__(self):
        author = self.name if self.name else "Anonyme"
        return f"{author} - {self.rating}/5 étoiles ({self.created_at.strftime('%d/%m/%Y')})"

    @property
    def stars_display(self):
        """Retourne l'affichage en étoiles"""
        return '⭐' * self.rating