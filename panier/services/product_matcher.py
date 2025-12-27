"""
Service de matching entre les ingrédients PanierFacile et les produits Intermarché.

Ce module implémente la logique de correspondance automatique entre les ingrédients
saisis par l'utilisateur et les produits disponibles dans les magasins Intermarché.
"""

import logging
from typing import List, Dict, Optional, Tuple
from django.core.cache import cache
from django.db import transaction
from datetime import timedelta

from panier.models import Ingredient, IngredientPanier, IntermarcheProductMatch
from panier.intermarche_api import IntermarcheAPIClient, IntermarcheAPIException

logger = logging.getLogger(__name__)


class ProductMatcher:
    """
    Service de matching intelligent entre ingrédients et produits Intermarché.

    Ce service utilise une stratégie de cache multi-niveaux:
    1. Redis (cache Django) - 1 heure
    2. Base de données (IntermarcheProductMatch) - 7 jours
    3. API Intermarché - Temps réel
    """

    # Durées de cache
    REDIS_CACHE_DURATION = 3600  # 1 heure
    DB_CACHE_DURATION_DAYS = 7   # 7 jours

    def __init__(self, store_id: str):
        """
        Initialise le matcher pour un magasin spécifique.

        Args:
            store_id: ID du magasin Intermarché (ex: "08177" ou "scraping")
        """
        self.store_id = store_id
        # Plus besoin de l'API client, on utilise le scraper maintenant
        # self.api_client = IntermarcheAPIClient()

    def _get_cache_key(self, ingredient_id: int) -> str:
        """
        Génère une clé de cache Redis pour un ingrédient.

        Args:
            ingredient_id: ID de l'ingrédient

        Returns:
            Clé de cache (ex: "intermarche_match_08177_123")
        """
        return f"intermarche_match_{self.store_id}_{ingredient_id}"

    def _normalize_keyword(self, text: str) -> str:
        """
        Normalise un texte pour la recherche de produits.

        Args:
            text: Texte à normaliser (ex: "500g de tomates cerises")

        Returns:
            Texte nettoyé (ex: "tomates cerises")
        """
        # Enlever les quantités courantes
        import re
        text = re.sub(r'\d+\s*(g|kg|l|ml|cl|unités?|pièces?)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(de|d\'|du|des|le|la|les|un|une)\b', '', text, flags=re.IGNORECASE)

        # Nettoyer les espaces multiples
        text = ' '.join(text.split())

        return text.strip()

    def _calculate_match_score(self, ingredient_name: str, product: Dict) -> float:
        """
        Calcule un score de pertinence entre un ingrédient et un produit.

        Args:
            ingredient_name: Nom de l'ingrédient
            product: Données du produit Intermarché

        Returns:
            Score entre 0.0 et 1.0
        """
        product_label = product.get('label', '').lower()
        ingredient_lower = ingredient_name.lower()

        # Score de base: correspondance exacte des mots
        ingredient_words = set(ingredient_lower.split())
        product_words = set(product_label.split())
        common_words = ingredient_words & product_words

        if not ingredient_words:
            return 0.0

        score = len(common_words) / len(ingredient_words)

        # Bonus si le produit contient l'ingrédient dans l'ordre
        if ingredient_lower in product_label:
            score += 0.2

        # Pénalité si le produit a beaucoup de mots supplémentaires (trop spécifique)
        if len(product_words) > len(ingredient_words) * 3:
            score *= 0.8

        return min(score, 1.0)

    def match_ingredient(
        self,
        ingredient: Ingredient,
        use_cache: bool = True
    ) -> Optional[IntermarcheProductMatch]:
        """
        Trouve le meilleur produit Intermarché pour un ingrédient.

        Stratégie de cache:
        1. Vérifier Redis (1h)
        2. Vérifier DB (7 jours)
        3. Appeler API et mettre en cache

        Args:
            ingredient: Instance d'Ingredient à matcher
            use_cache: Si False, force l'appel API (défaut: True)

        Returns:
            IntermarcheProductMatch ou None si aucun match trouvé

        Example:
            >>> matcher = ProductMatcher("08177")
            >>> ingredient = Ingredient.objects.get(nom="Tomates cerises")
            >>> match = matcher.match_ingredient(ingredient)
            >>> print(f"Produit trouvé: {match.product_label} - {match.product_price}€")
        """
        cache_key = self._get_cache_key(ingredient.id)

        # Niveau 1: Redis Cache
        if use_cache:
            cached_match_id = cache.get(cache_key)
            if cached_match_id:
                try:
                    match = IntermarcheProductMatch.objects.get(id=cached_match_id)
                    logger.debug(f"Redis cache hit for ingredient {ingredient.id}")
                    return match
                except IntermarcheProductMatch.DoesNotExist:
                    cache.delete(cache_key)

        # Niveau 2: Database Cache
        if use_cache:
            from django.utils import timezone
            cache_cutoff = timezone.now() - timedelta(days=self.DB_CACHE_DURATION_DAYS)

            db_match = IntermarcheProductMatch.objects.filter(
                ingredient=ingredient,
                store_id=self.store_id,
                last_updated__gte=cache_cutoff
            ).order_by('-match_score').first()

            if db_match:
                logger.debug(f"DB cache hit for ingredient {ingredient.id}")
                # Stocker dans Redis pour les prochaines fois
                cache.set(cache_key, db_match.id, self.REDIS_CACHE_DURATION)
                return db_match

        # Niveau 3: Scraper Call (plus d'API disponible)
        try:
            logger.info(f"Searching Intermarché products for: {ingredient.nom}")

            # Normaliser le nom de l'ingrédient pour la recherche
            search_keyword = self._normalize_keyword(ingredient.nom)
            if not search_keyword:
                search_keyword = ingredient.nom

            # Rechercher les produits via scraping
            from panier.intermarche_scraper import search_intermarche_products

            products = search_intermarche_products(search_keyword)

            if not products:
                logger.warning(f"No products found for ingredient: {ingredient.nom}")
                return None

            # Le scraper retourne déjà les produits triés par pertinence
            # On prend le premier (le plus pertinent)
            best_product = products[0]

            # Créer ou mettre à jour le match en DB
            with transaction.atomic():
                match, created = IntermarcheProductMatch.objects.update_or_create(
                    ingredient=ingredient,
                    store_id=self.store_id,  # 'scraping' par défaut
                    defaults={
                        # Données du scraper (différent de l'API)
                        'product_name': best_product['name'],
                        'price': best_product.get('price'),
                        'is_available': best_product.get('is_available', True),
                        'product_url': best_product.get('url'),
                        'match_score': 1.0,  # Score parfait car déjà filtré par le scraper
                        # Compatibilité backward avec les anciens champs API
                        'product_label': best_product['name'],  # Même valeur pour compatibilité
                        'product_price': best_product.get('price'),  # Même valeur pour compatibilité
                    }
                )

            # Stocker dans Redis
            cache.set(cache_key, match.id, self.REDIS_CACHE_DURATION)

            action = "created" if created else "updated"
            logger.info(f"Match {action} for {ingredient.nom}: {match.product_name} (price: {match.price}€)")

            return match

        except Exception as e:
            logger.error(f"Scraper error while matching ingredient {ingredient.nom}: {str(e)}")
            return None

    def match_panier_ingredients(
        self,
        ingredient_paniers: List[IngredientPanier],
        use_cache: bool = True
    ) -> Dict[int, Optional[IntermarcheProductMatch]]:
        """
        Matche tous les ingrédients d'un panier avec des produits Intermarché.

        Args:
            ingredient_paniers: Liste des IngredientPanier à matcher
            use_cache: Si False, force l'appel API pour tous (défaut: True)

        Returns:
            Dict mapping {ingredient_panier_id: IntermarcheProductMatch}
            Le match peut être None si aucun produit n'a été trouvé

        Example:
            >>> matcher = ProductMatcher("08177")
            >>> panier = Panier.objects.get(id=1)
            >>> ingredient_paniers = panier.ingredient_paniers.all()
            >>> matches = matcher.match_panier_ingredients(ingredient_paniers)
            >>> for ing_panier_id, match in matches.items():
            ...     if match:
            ...         print(f"Match: {match.product_label}")
        """
        matches = {}

        for ing_panier in ingredient_paniers:
            match = self.match_ingredient(ing_panier.ingredient, use_cache=use_cache)
            matches[ing_panier.id] = match

        # Statistiques de matching
        total = len(matches)
        successful = sum(1 for m in matches.values() if m is not None)
        logger.info(f"Matched {successful}/{total} ingredients for store {self.store_id}")

        return matches

    def get_cart_items_from_matches(
        self,
        matches: Dict[int, Optional[IntermarcheProductMatch]],
        ingredient_paniers: List[IngredientPanier]
    ) -> List[Dict[str, any]]:
        """
        Convertit les matches en items de panier pour l'API Intermarché.

        Args:
            matches: Dict des matches (de match_panier_ingredients)
            ingredient_paniers: Liste des IngredientPanier correspondants

        Returns:
            Liste d'items formatés pour l'API Carts
            Format: [{"itemId": "12345", "quantity": 2}, ...]

        Example:
            >>> matcher = ProductMatcher("08177")
            >>> matches = matcher.match_panier_ingredients(ingredient_paniers)
            >>> items = matcher.get_cart_items_from_matches(matches, ingredient_paniers)
            >>> # Utiliser items pour créer un panier Intermarché
        """
        items = []
        ing_panier_dict = {ing.id: ing for ing in ingredient_paniers}

        for ing_panier_id, match in matches.items():
            if match is None:
                continue

            ing_panier = ing_panier_dict.get(ing_panier_id)
            if not ing_panier:
                continue

            # Utiliser la quantité de l'IngredientPanier
            quantity = int(ing_panier.quantite) if ing_panier.quantite else 1
            if quantity < 1:
                quantity = 1

            item = {
                "itemId": match.intermarche_product_id,
                "quantity": quantity,
                "catalog": "PDV"
            }
            items.append(item)

        return items

    def refresh_matches(self, ingredient_paniers: List[IngredientPanier]) -> None:
        """
        Force le rafraîchissement de tous les matches (ignore le cache).

        Args:
            ingredient_paniers: Liste des IngredientPanier à rafraîchir

        Example:
            >>> matcher = ProductMatcher("08177")
            >>> matcher.refresh_matches(panier.ingredient_paniers.all())
        """
        logger.info(f"Refreshing matches for {len(ingredient_paniers)} ingredients")
        self.match_panier_ingredients(ingredient_paniers, use_cache=False)
