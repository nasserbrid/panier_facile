"""Scraper Aldi - logique spécifique à aldi.fr."""

import logging
from typing import Dict, List, Optional
from urllib.parse import quote_plus

from .base import BaseScraper, random_delay

logger = logging.getLogger(__name__)


class AldiScraper(BaseScraper):

    RETAILER_NAME = "Aldi"
    BASE_URL = "https://www.aldi.fr"
    SEARCH_URL = "https://www.aldi.fr/recherche.html"

    # Aldi charge les résultats côté client (JS).
    # Pas d'API JSON connue à intercepter.
    API_PATTERNS = []

    # ── Session ──────────────────────────────────────────────────

    def _establish_session(self):
        """Skip la homepage : la navigation directe vers /recherche fonctionne.

        La homepage Aldi déclenche souvent une page anti-robot,
        mais l'URL de recherche passe sans problème.
        """
        if self._session_established:
            return
        self._session_established = True
        logger.info(f"[{self.RETAILER_NAME}] Session initialisée (navigation directe)")

    # ── Recherche ───────────────────────────────────────────────

    def _perform_search(self, query: str) -> None:
        """Navigation directe vers l'URL de recherche Aldi."""
        url = f"{self.SEARCH_URL}?query={quote_plus(query)}"
        self.page.goto(url, wait_until="domcontentloaded",
                       timeout=self.timeout)

        # Aldi charge les produits côté client (Next.js).
        # Attendre que les cartes produits apparaissent dans le DOM.
        try:
            self.page.wait_for_selector(
                'div.product-tile', timeout=10000
            )
            logger.info(f"[Aldi] Produits chargés pour: {query}")
        except Exception:
            logger.warning(f"[Aldi] Timeout: aucun produit chargé pour '{query}'")

    # ── Extraction API (non utilisée pour Aldi) ─────────────────

    def _extract_products_from_json(self, data: dict) -> List[Dict]:
        # Aldi n'a pas d'API JSON interceptable connue.
        return []

    # ── Parsing HTML (méthode principale pour Aldi) ─────────────

    def _fallback_html_parsing(self) -> List[Dict]:
        products = []

        # Sélecteur réel: <div class="product-tile">
        elements = self.page.query_selector_all('div.product-tile')

        if not elements:
            logger.warning("[Aldi] Aucune carte produit trouvée dans le HTML")
            return products

        for el in elements[:10]:
            p = self._parse_html_card(el)
            if p:
                products.append(p)

        return products

    def _parse_html_card(self, el) -> Optional[Dict]:
        try:
            # Nom : <h2 class="product-tile__content__upper__product-name">
            name_el = el.query_selector('.product-tile__content__upper__product-name')
            if not name_el:
                return None
            name = name_el.text_content().strip()
            if not name:
                return None

            # Prix : <span class="tag__label--price"> → "1.05"
            price = None
            price_el = el.query_selector('.tag__label--price')
            if price_el:
                try:
                    price = float(price_el.text_content().strip())
                except (ValueError, TypeError):
                    price = self._parse_price(price_el.text_content())

            # URL : <a class="product-tile__action" href="/fiches-produits/...">
            product_url = ''
            link = el.query_selector('a.product-tile__action')
            if link:
                href = link.get_attribute('href')
                if href:
                    product_url = (href if href.startswith('http')
                                   else f"{self.BASE_URL}{href}")

            # Image : <img class="product-tile__image-section__picture">
            image_url = ''
            img = el.query_selector('img.product-tile__image-section__picture')
            if img:
                image_url = img.get_attribute('src') or ''

            # Marque : <p class="product-tile__content__upper__brand-name">
            brand = ''
            brand_el = el.query_selector('.product-tile__content__upper__brand-name')
            if brand_el:
                brand = brand_el.text_content().strip()

            return {
                'product_name': name,
                'price': price,
                'product_url': product_url,
                'image_url': image_url,
                'brand': brand,
                'is_available': True,
            }
        except Exception as e:
            logger.debug(f"[Aldi] Erreur parsing carte HTML: {e}")
            return None
