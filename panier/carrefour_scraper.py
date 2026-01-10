"""
Scraper pour récupérer les produits Carrefour Drive
Hérite de BaseDriveScraper pour réutiliser la logique commune.
"""

import logging
from typing import List, Dict, Optional
from .base_scraper import BaseDriveScraper

logger = logging.getLogger(__name__)


class CarrefourScraper(BaseDriveScraper):
    """
    Scraper optimisé pour Carrefour Drive
    """

    RETAILER_NAME = "Carrefour"
    BASE_URL = "https://www.carrefour.fr"
    SEARCH_URL = f"{BASE_URL}/s"

    def _get_search_url(self, query: str) -> str:
        """Construit l'URL de recherche Carrefour"""
        return f"{self.SEARCH_URL}?q={query.replace(' ', '+')}"

    def _get_product_selectors(self) -> List[str]:
        """Retourne les sélecteurs CSS pour les produits Carrefour"""
        return [
            'article[data-testid="product"]',
            '.product-card',
            '[class*="ProductCard"]',
            'article.product',
            '[data-test*="product"]',
        ]

    def _handle_cookie_popup(self):
        """Gère le popup de cookies Carrefour"""
        try:
            cookie_selectors = [
                '#didomi-notice-agree-button',
                'button[id*="accept"]',
                'button[class*="accept"]',
                '#footer_tc_privacy_button_2',
            ]

            for selector in cookie_selectors:
                try:
                    button = self.page.query_selector(selector)
                    if button and button.is_visible():
                        button.click()
                        logger.info("✅ Popup cookies Carrefour accepté")
                        return
                except:
                    continue
        except Exception:
            pass

    def _extract_product_data(self, element) -> Optional[Dict]:
        """
        Extrait les données d'un élément produit Carrefour

        Args:
            element: ElementHandle Playwright

        Returns:
            Dictionnaire avec les données du produit ou None
        """
        try:
            # Nom
            name = None
            name_selectors = [
                'h2',
                'h3',
                '[data-testid="product-name"]',
                '.product-name',
                '[class*="title"]',
            ]

            for selector in name_selectors:
                try:
                    name_el = element.query_selector(selector)
                    if name_el:
                        name = name_el.text_content().strip()
                        if name:
                            break
                except:
                    continue

            if not name:
                return None

            # Prix
            price = None
            price_selectors = [
                '[data-testid="product-price"]',
                '.product-price',
                '[class*="price"]',
                'span[class*="Price"]',
            ]

            for selector in price_selectors:
                try:
                    price_el = element.query_selector(selector)
                    if price_el:
                        price_text = price_el.text_content().strip()
                        price = self._parse_price(price_text)
                        if price:
                            break
                except:
                    continue

            # URL
            product_url = None
            try:
                link_el = element.query_selector('a')
                if link_el:
                    href = link_el.get_attribute('href')
                    if href:
                        product_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
            except:
                pass

            # Disponibilité
            is_available = True
            try:
                out_of_stock = element.query_selector('[class*="out-of-stock"], [class*="indisponible"]')
                is_available = out_of_stock is None
            except:
                pass

            product_data = {
                'name': name,
                'price': price,
                'is_available': is_available,
                'url': product_url,
                'source': 'carrefour_playwright'
            }

            logger.debug(f"Produit Carrefour: {name} - {price}€")
            return product_data

        except Exception as e:
            logger.error(f"Erreur extraction données Carrefour: {e}")
            return None


def search_carrefour_products(ingredient_name: str) -> List[Dict]:
    """
    Fonction utilitaire pour rechercher des produits Carrefour

    Args:
        ingredient_name: Nom de l'ingrédient à rechercher

    Returns:
        Liste de produits trouvés
    """
    with CarrefourScraper(headless=True) as scraper:
        products = scraper.search_product(ingredient_name)
    return products
