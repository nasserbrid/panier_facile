"""Scraper E.Leclerc - logique spécifique à e.leclerc."""

import json
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import quote_plus

from .base import BaseScraper, random_delay

logger = logging.getLogger(__name__)


class LeclercScraper(BaseScraper):

    RETAILER_NAME = "Leclerc"
    BASE_URL = "https://www.e.leclerc"
    SEARCH_URL = "https://www.e.leclerc/recherche"

    # E.Leclerc charge les résultats côté client.
    # Intercepter les appels API internes pour récupérer les données JSON.
    API_PATTERNS = [
        r'/api.*search',
        r'/api.*product',
        r'algolia',
        r'elasticsearch',
        r'search.*query',
    ]

    # ── Recherche ───────────────────────────────────────────────

    def _perform_search(self, query: str) -> None:
        """Navigation directe vers l'URL de recherche E.Leclerc."""
        url = f"{self.SEARCH_URL}?q={quote_plus(query)}"
        self.page.goto(url, wait_until="domcontentloaded",
                       timeout=self.timeout)

        # E.Leclerc charge les produits côté client.
        # Attendre que des éléments produits apparaissent dans le DOM.
        # On essaie plusieurs sélecteurs courants.
        selectors_to_try = [
            '[data-testid*="product"]',
            '.product-card',
            '.product-tile',
            '.product-item',
            '.product-list-item',
            'article[class*="product"]',
            'div[class*="product-card"]',
            'div[class*="ProductCard"]',
            'a[href*="/fp/"]',
        ]

        for selector in selectors_to_try:
            try:
                self.page.wait_for_selector(selector, timeout=5000)
                logger.info(f"[Leclerc] Produits chargés avec: {selector}")
                return
            except Exception:
                continue

        logger.warning(f"[Leclerc] Timeout: aucun sélecteur produit trouvé pour '{query}'")

    # ── Extraction API ─────────────────────────────────────────

    def _extract_products_from_json(self, data: dict) -> List[Dict]:
        """Extrait les produits d'une réponse API JSON E.Leclerc."""
        products = []

        # Chercher les produits dans différentes structures possibles
        items = []
        if isinstance(data, dict):
            # Structure type: {products: [...]} ou {results: [...]} ou {hits: [...]}
            for key in ('products', 'results', 'hits', 'items', 'data'):
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break

            # Structure Algolia: {results: [{hits: [...]}]}
            if not items and 'results' in data and isinstance(data['results'], list):
                for result in data['results']:
                    if isinstance(result, dict) and 'hits' in result:
                        items = result['hits']
                        break

        elif isinstance(data, list):
            items = data

        for item in items[:10]:
            if not isinstance(item, dict):
                continue

            name = (item.get('name') or item.get('title') or
                    item.get('product_name') or item.get('label') or '')
            if not name:
                continue

            price = None
            for price_key in ('price', 'currentPrice', 'unitPrice',
                              'selling_price', 'salePrice'):
                val = item.get(price_key)
                if val is not None:
                    try:
                        price = float(val)
                        break
                    except (ValueError, TypeError):
                        # Peut être un dict {amount: ..., currency: ...}
                        if isinstance(val, dict):
                            amount = val.get('amount') or val.get('value')
                            if amount is not None:
                                try:
                                    price = float(amount)
                                    break
                                except (ValueError, TypeError):
                                    pass

            product_url = ''
            for url_key in ('url', 'href', 'link', 'slug', 'productUrl'):
                url_val = item.get(url_key, '')
                if url_val:
                    product_url = (url_val if url_val.startswith('http')
                                   else f"{self.BASE_URL}{url_val}")
                    break

            image_url = ''
            for img_key in ('image', 'imageUrl', 'thumbnail', 'img',
                            'picture', 'image_url', 'media'):
                img_val = item.get(img_key, '')
                if isinstance(img_val, str) and img_val:
                    image_url = img_val
                    break
                elif isinstance(img_val, dict):
                    image_url = img_val.get('url', '') or img_val.get('src', '')
                    if image_url:
                        break
                elif isinstance(img_val, list) and img_val:
                    first = img_val[0]
                    if isinstance(first, str):
                        image_url = first
                    elif isinstance(first, dict):
                        image_url = first.get('url', '') or first.get('src', '')
                    if image_url:
                        break

            brand = (item.get('brand') or item.get('brandName') or
                     item.get('manufacturer') or '')
            if isinstance(brand, dict):
                brand = brand.get('name', '')

            products.append({
                'product_name': name,
                'price': price,
                'product_url': product_url,
                'image_url': image_url,
                'brand': brand,
                'is_available': True,
            })

        return products

    # ── Parsing HTML (fallback) ────────────────────────────────

    def _fallback_html_parsing(self) -> List[Dict]:
        """Parse le DOM rendu pour extraire les produits."""
        # Utiliser page.evaluate() pour extraire les produits via JavaScript
        # car le DOM est rendu côté client
        products_data = self.page.evaluate("""
        () => {
            const products = [];

            // Stratégie 1: Chercher des liens vers des fiches produit (/fp/)
            const productLinks = document.querySelectorAll('a[href*="/fp/"]');
            const seen = new Set();

            for (const link of productLinks) {
                const href = link.getAttribute('href') || '';
                if (seen.has(href)) continue;
                seen.add(href);

                // Remonter jusqu'au conteneur parent du produit
                let container = link.closest('article, [class*="product"], [class*="Product"], [data-testid*="product"]');
                if (!container) container = link.parentElement?.parentElement || link;

                // Extraire le nom
                const nameEl = container.querySelector('h2, h3, h4, [class*="name"], [class*="title"], [class*="Name"], [class*="Title"]');
                const name = nameEl ? nameEl.textContent.trim() : '';
                if (!name || name.length < 3) continue;

                // Extraire le prix
                let price = null;
                const priceEls = container.querySelectorAll('[class*="price"], [class*="Price"], [data-testid*="price"]');
                for (const priceEl of priceEls) {
                    const text = priceEl.textContent.replace(/\\s+/g, '').replace(',', '.').replace('€', '');
                    const match = text.match(/(\\d+\\.?\\d*)/);
                    if (match) {
                        price = parseFloat(match[1]);
                        break;
                    }
                }

                // Extraire l'image
                const imgEl = container.querySelector('img');
                const imageUrl = imgEl ? (imgEl.src || imgEl.dataset.src || '') : '';

                // Extraire la marque
                const brandEl = container.querySelector('[class*="brand"], [class*="Brand"]');
                const brand = brandEl ? brandEl.textContent.trim() : '';

                products.push({
                    product_name: name,
                    price: price,
                    product_url: href.startsWith('http') ? href : 'https://www.e.leclerc' + href,
                    image_url: imageUrl,
                    brand: brand,
                    is_available: true
                });

                if (products.length >= 10) break;
            }

            // Stratégie 2: Si pas de liens /fp/, chercher par structure de prix
            if (products.length === 0) {
                const allElements = document.querySelectorAll('[class*="product"], [class*="Product"], article');
                for (const el of allElements) {
                    const nameEl = el.querySelector('h2, h3, h4, [class*="name"], [class*="title"]');
                    const priceEl = el.querySelector('[class*="price"], [class*="Price"]');

                    if (!nameEl || !priceEl) continue;

                    const name = nameEl.textContent.trim();
                    if (!name || name.length < 3) continue;

                    const priceText = priceEl.textContent.replace(/\\s+/g, '').replace(',', '.').replace('€', '');
                    const priceMatch = priceText.match(/(\\d+\\.?\\d*)/);
                    const price = priceMatch ? parseFloat(priceMatch[1]) : null;

                    const linkEl = el.querySelector('a[href]');
                    const href = linkEl ? linkEl.getAttribute('href') : '';

                    const imgEl = el.querySelector('img');
                    const imageUrl = imgEl ? (imgEl.src || '') : '';

                    products.push({
                        product_name: name,
                        price: price,
                        product_url: href && href.startsWith('http') ? href : (href ? 'https://www.e.leclerc' + href : ''),
                        image_url: imageUrl,
                        brand: '',
                        is_available: true
                    });

                    if (products.length >= 10) break;
                }
            }

            return products;
        }
        """)

        if not products_data:
            logger.warning("[Leclerc] Aucun produit trouvé dans le DOM")
            return []

        logger.info(f"[Leclerc] {len(products_data)} produits extraits du DOM")
        return products_data
