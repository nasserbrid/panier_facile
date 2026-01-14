"""
Scraper spécifique pour Auchan Drive.

Hérite de BaseDriveScraper pour réutiliser la logique commune.
Implémente les méthodes abstraites spécifiques à Auchan.
"""

import logging
from typing import List, Dict, Optional
from urllib.parse import quote_plus
from .base_scraper import BaseDriveScraper

logger = logging.getLogger(__name__)


class AuchanScraper(BaseDriveScraper):
    """
    Scraper pour Auchan Drive.

    Auchan a généralement moins de protection anti-bot que Carrefour/Intermarché,
    ce qui le rend plus facile à scraper de manière fiable.

    Architecture:
    - Site principal: auchan.fr
    - URL de recherche: auchan.fr/recherche?text=query
    - Structure de produits: divs avec classes spécifiques
    """

    RETAILER_NAME = "Auchan"
    BASE_URL = "https://www.auchan.fr"
    SEARCH_URL = f"{BASE_URL}/recherche"

    def _get_search_url(self, query: str) -> str:
        """
        Construit l'URL de recherche Auchan.

        Args:
            query: Terme de recherche

        Returns:
            URL complète de recherche

        Example:
            "tomates" -> "https://www.auchan.fr/recherche?text=tomates"
        """
        encoded_query = quote_plus(query)
        return f"{self.SEARCH_URL}?text={encoded_query}"

    def _get_product_selectors(self) -> List[str]:
        """
        Sélecteurs CSS possibles pour les produits Auchan.

        Auchan utilise généralement des classes comme:
        - .product-item
        - .productListItem
        - [data-test-id="product-card"]

        Returns:
            Liste de sélecteurs CSS à tester par ordre de priorité
        """
        return [
            '[data-test-id="product-card"]',
            '.product-item',
            '.productListItem',
            '[class*="ProductCard"]',
            'article[data-product-id]',
            '.product-card',
        ]

    def _handle_cookie_popup(self):
        """
        Gère le popup de cookies Auchan.

        Auchan utilise généralement un popup avec bouton "Accepter" ou "J'accepte".
        """
        cookie_selectors = [
            'button[id*="accept"]',
            'button[id*="cookie"]',
            '#didomi-notice-agree-button',
            'button:has-text("Accepter")',
            'button:has-text("J\'accepte")',
            '.cookie-consent-accept',
        ]

        for selector in cookie_selectors:
            try:
                cookie_button = self.page.query_selector(selector)
                if cookie_button and cookie_button.is_visible():
                    cookie_button.click()
                    logger.info(f"✅ Cookie popup Auchan fermé avec sélecteur: {selector}")
                    self.page.wait_for_timeout(1000)
                    return
            except Exception as e:
                logger.debug(f"Sélecteur cookie {selector} non trouvé: {e}")
                continue

        logger.info("Aucun popup cookie Auchan détecté (ou déjà fermé)")

    def _extract_product_data(self, element) -> Optional[Dict]:
        """
        Extrait les données d'un élément produit Auchan.

        Args:
            element: ElementHandle Playwright représentant un produit

        Returns:
            Dictionnaire avec:
            - product_name: Nom du produit
            - price: Prix en float
            - product_url: URL complète du produit
            - is_available: Disponibilité
            - image_url: URL de l'image (optionnel)
        """
        try:
            # Nom du produit
            name_selectors = [
                '[data-test-id="product-name"]',
                '.product-title',
                '.product-name',
                'h3',
                'h2',
                '[class*="ProductName"]',
            ]

            product_name = None
            for selector in name_selectors:
                try:
                    name_element = element.query_selector(selector)
                    if name_element:
                        product_name = name_element.inner_text().strip()
                        if product_name:
                            break
                except Exception:
                    continue

            if not product_name:
                logger.debug("Nom produit Auchan non trouvé")
                return None

            # Prix
            price_selectors = [
                '[data-test-id="product-price"]',
                '.product-price',
                '.price',
                '[class*="Price"]',
                'span[class*="price"]',
            ]

            price = None
            for selector in price_selectors:
                try:
                    price_element = element.query_selector(selector)
                    if price_element:
                        price_text = price_element.inner_text()
                        price = self._parse_price(price_text)
                        if price:
                            break
                except Exception:
                    continue

            # URL du produit
            product_url = None
            try:
                link_element = element.query_selector('a[href]')
                if link_element:
                    href = link_element.get_attribute('href')
                    if href:
                        # URL relative -> absolue
                        if href.startswith('/'):
                            product_url = f"{self.BASE_URL}{href}"
                        elif href.startswith('http'):
                            product_url = href
                        else:
                            product_url = f"{self.BASE_URL}/{href}"
            except Exception as e:
                logger.debug(f"URL produit Auchan non trouvée: {e}")

            # Disponibilité
            is_available = True
            try:
                unavailable_indicators = [
                    '.out-of-stock',
                    '[data-test-id="out-of-stock"]',
                    '.indisponible',
                    '[class*="unavailable"]',
                ]

                for selector in unavailable_indicators:
                    unavailable = element.query_selector(selector)
                    if unavailable:
                        is_available = False
                        break
            except Exception:
                pass

            # Image (optionnel)
            image_url = None
            try:
                img_element = element.query_selector('img[src]')
                if img_element:
                    image_url = img_element.get_attribute('src')
                    # Si URL relative, la rendre absolue
                    if image_url and image_url.startswith('/'):
                        image_url = f"{self.BASE_URL}{image_url}"
            except Exception:
                pass

            logger.debug(f"✅ Auchan: {product_name} - {price}€ - Dispo: {is_available}")

            return {
                'product_name': product_name,
                'price': price,
                'product_url': product_url or '',
                'is_available': is_available,
                'image_url': image_url or '',
            }

        except Exception as e:
            logger.error(f"Erreur extraction produit Auchan: {e}")
            return None
