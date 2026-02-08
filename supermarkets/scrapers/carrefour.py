"""Scraper Carrefour - logique spécifique à carrefour.fr."""

import logging
import random
import re
from typing import Dict, List, Optional
from urllib.parse import quote_plus

from .base import BaseScraper, random_delay

logger = logging.getLogger(__name__)


class CarrefourScraper(BaseScraper):

    RETAILER_NAME = "Carrefour"
    BASE_URL = "https://www.carrefour.fr"
    SEARCH_URL = "https://www.carrefour.fr/s"

    # Carrefour utilise du SSR : les produits sont dans le HTML.
    # On garde l'interception API en bonus au cas où.
    API_PATTERNS = [
        r'/api/v\d+/search',
        r'/api/products',
        r'search.*products',
        r'graphql',
    ]

    # ── Recherche ───────────────────────────────────────────────

    def _perform_search(self, query: str) -> None:
        """Utilise la barre de recherche, fallback sur URL directe."""
        if not self._use_search_bar(query):
            logger.warning("[Carrefour] Barre introuvable, navigation directe")
            url = f"{self.SEARCH_URL}?q={quote_plus(query)}"
            self.page.goto(url, wait_until="domcontentloaded",
                           timeout=self.timeout)

    def _use_search_bar(self, query: str) -> bool:
        search_selectors = [
            'input[name="q"]',
            'input[type="search"]',
            'input[placeholder*="recherch" i]',
            '#search-input',
            '[data-testid="search-input"]',
        ]

        for sel in search_selectors:
            try:
                inp = self.page.query_selector(sel)
                if inp and inp.is_visible():
                    inp.click()
                    random_delay(200, 400)
                    inp.fill('')
                    random_delay(100, 200)

                    for char in query:
                        inp.type(char, delay=random.randint(50, 150))
                    random_delay(300, 600)

                    inp.press('Enter')
                    logger.info(f"[Carrefour] Recherche via barre: {query}")
                    return True
            except Exception:
                continue

        return False

    # ── Extraction API (bonus, Carrefour est SSR) ───────────────

    def _extract_products_from_json(self, data: dict) -> List[Dict]:
        products = []
        product_lists = []

        if isinstance(data, dict):
            attrs = data.get('data', {}).get('attributes', {})
            if 'products' in attrs:
                product_lists.append(attrs['products'])
            if 'products' in data:
                product_lists.append(data['products'])
            if isinstance(data.get('data'), list):
                product_lists.append(data['data'])
            results = data.get('results', data.get('result', {}))
            if isinstance(results, dict) and 'products' in results:
                product_lists.append(results['products'])
            if 'items' in data:
                product_lists.append(data['items'])

        for lst in product_lists:
            if not isinstance(lst, list):
                continue
            for item in lst:
                p = self._parse_api_product(item)
                if p:
                    products.append(p)

        return products

    def _parse_api_product(self, item: dict) -> Optional[Dict]:
        if not isinstance(item, dict):
            return None

        attrs = item.get('attributes', item)

        name = (attrs.get('name') or attrs.get('title')
                or attrs.get('productName') or attrs.get('label')
                or item.get('name'))
        if not name:
            return None

        price = None
        price_data = attrs.get('price', {})
        if isinstance(price_data, dict):
            price = (price_data.get('value') or price_data.get('amount')
                     or price_data.get('unitPrice'))
        elif isinstance(price_data, (int, float)):
            price = price_data
        else:
            price = attrs.get('price') or attrs.get('unitPrice')

        product_url = attrs.get('url') or attrs.get('productUrl') or item.get('url')
        if product_url and not product_url.startswith('http'):
            product_url = f"{self.BASE_URL}{product_url}"

        image_url = self._extract_image_from_json(attrs)
        brand = attrs.get('brand') or attrs.get('brandName') or ''

        avail = attrs.get('availability', {})
        if isinstance(avail, dict):
            is_available = avail.get('is_available', avail.get('available', True))
        else:
            is_available = attrs.get('available', attrs.get('inStock', True))

        return {
            'product_name': str(name).strip(),
            'price': float(price) if price else None,
            'product_url': product_url or '',
            'image_url': image_url or '',
            'brand': brand,
            'is_available': bool(is_available),
        }

    @staticmethod
    def _extract_image_from_json(attrs: dict) -> Optional[str]:
        img = attrs.get('image', attrs.get('images', []))
        if isinstance(img, dict):
            return img.get('url') or img.get('src')
        if isinstance(img, list) and img:
            first = img[0]
            if isinstance(first, dict):
                return first.get('url') or first.get('src')
            if isinstance(first, str):
                return first
        return None

    # ── Parsing HTML (méthode principale pour Carrefour) ────────

    def _fallback_html_parsing(self) -> List[Dict]:
        products = []

        # Sélecteur réel: <article class="product-list-card-plp-grid-new">
        elements = self.page.query_selector_all(
            'article.product-list-card-plp-grid-new'
        )

        if not elements:
            logger.warning("[Carrefour] Aucune carte produit trouvée dans le HTML")
            return products

        for el in elements[:10]:
            p = self._parse_html_card(el)
            if p:
                products.append(p)

        return products

    def _parse_html_card(self, el) -> Optional[Dict]:
        try:
            # Nom : <h3 class="product-card-title__text">
            name_el = el.query_selector('h3.product-card-title__text')
            if not name_el:
                return None
            name = name_el.text_content().strip()
            if not name:
                return None

            # Prix : <div data-testid="product-price__amount--main">
            # Contient plusieurs <p> : "1", ",49", "€" → on concatène
            price = None
            price_el = el.query_selector('[data-testid="product-price__amount--main"]')
            if price_el:
                raw = price_el.text_content()
                # "  1   ,49   €  " → "1,49€" → "1.49"
                cleaned = re.sub(r'\s+', '', raw)
                price = self._parse_price(cleaned)

            # URL : <a class="product-list-card-plp-grid-new__title-container">
            product_url = ''
            link = el.query_selector(
                'a.product-list-card-plp-grid-new__title-container'
            )
            if link:
                href = link.get_attribute('href')
                if href:
                    product_url = (href if href.startswith('http')
                                   else f"{self.BASE_URL}{href}")

            # Image : <img class="product-card-image-new__content">
            image_url = ''
            img = el.query_selector('img.product-card-image-new__content')
            if img:
                image_url = img.get_attribute('src') or ''

            # Marque : <a class="c-link--tone-accent">
            brand = ''
            brand_el = el.query_selector('a.c-link--tone-accent')
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
            logger.debug(f"[Carrefour] Erreur parsing carte HTML: {e}")
            return None
