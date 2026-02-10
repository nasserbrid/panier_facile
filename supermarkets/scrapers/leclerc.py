"""Scraper E.Leclerc - logique spécifique à e.leclerc."""

import json
import logging
import random
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

    # ── Session ──────────────────────────────────────────────────

    def _establish_session(self):
        """Skip la homepage : la navigation directe vers /recherche fonctionne.

        La homepage E.Leclerc déclenche souvent une page anti-robot,
        mais l'URL de recherche passe sans problème.
        On accepte les cookies lors de la première recherche.
        """
        if self._session_established:
            return
        # Pas de navigation vers la homepage — _perform_search navigue
        # directement vers /recherche?q=... et les cookies sont acceptés
        # dans BaseScraper.search() après _perform_search.
        self._session_established = True
        logger.info(f"[{self.RETAILER_NAME}] Session initialisée (navigation directe)")

    # ── Recherche ───────────────────────────────────────────────

    def _perform_search(self, query: str) -> None:
        """Navigation directe vers l'URL de recherche E.Leclerc."""
        url = f"{self.SEARCH_URL}?q={quote_plus(query)}"
        self.page.goto(url, wait_until="domcontentloaded",
                       timeout=self.timeout)

        # E.Leclerc utilise des liens /fp/ (fiches produit) pour chaque produit.
        # Ce sélecteur est le seul qui fonctionne en prod — les autres
        # causaient 40s de timeout inutile par recherche.
        try:
            self.page.wait_for_selector('a[href*="/fp/"]', timeout=15000)
            logger.info(f"[Leclerc] Produits chargés pour: {query}")
        except Exception:
            logger.warning(f"[Leclerc] Timeout: aucun produit trouvé pour '{query}'")

    # ── Recherche (override) ─────────────────────────────────────

    def search(self, query: str) -> List[Dict]:
        """Override : parse le DOM IMMÉDIATEMENT après chargement.

        L'API E.Leclerc product-search est un catalogue sans prix
        (les prix dépendent du magasin sélectionné). Les prix sont
        visibles dans le DOM grâce au contexte navigateur. Il faut
        parser le DOM dès que les produits apparaissent, avant que
        la détection anti-robot ne remplace la page (~5-8s).
        """
        self.found_products = []
        self._establish_session()

        self.page.on("response", self._handle_response)
        try:
            random_delay(800, 1500)
            logger.info(f"[{self.RETAILER_NAME}] Recherche: {query}")

            self._perform_search(query)

            # Parser le DOM IMMÉDIATEMENT (avant que le robot ne prenne le relais)
            self._accept_cookies()
            self.page.wait_for_timeout(random.randint(500, 1000))

            dom_products = self._fallback_html_parsing()
            dom_priced = [p for p in dom_products if p.get('price')]

            if dom_priced:
                logger.info(f"[{self.RETAILER_NAME}] DOM: {len(dom_priced)} produits avec prix")
                self.found_products = dom_priced
            else:
                # Dernier recours : vérifier les données API (variants)
                priced = [p for p in self.found_products if p.get('price')]
                if priced:
                    self.found_products = priced
                elif self.found_products:
                    logger.info(f"[{self.RETAILER_NAME}] API: {len(self.found_products)} "
                                f"produits sans prix, DOM vide aussi")
                    self.found_products = []

            if not self.found_products:
                reason = "blocked" if self._is_blocked() else "no_products"
                self._save_debug(query, reason)

            logger.info(f"[{self.RETAILER_NAME}] {len(self.found_products)} produits "
                        f"trouvés pour '{query}'")
            return self.found_products

        except Exception as e:
            logger.error(f"[{self.RETAILER_NAME}] Erreur recherche '{query}': {e}")
            return []
        finally:
            self.page.remove_listener("response", self._handle_response)

    # ── Extraction API ─────────────────────────────────────────

    @staticmethod
    def _deep_find_price(obj, depth=0):
        """Cherche récursivement un prix dans un objet imbriqué."""
        if depth > 4:
            return None
        if isinstance(obj, (int, float)) and 0.01 < obj < 10000:
            return float(obj)
        if isinstance(obj, dict):
            # Clés prioritaires pour les prix
            for key in ('price', 'currentPrice', 'unitPrice', 'value',
                        'amount', 'sellingPrice', 'salePrice'):
                if key in obj:
                    val = obj[key]
                    if isinstance(val, (int, float)) and 0.01 < val < 10000:
                        return float(val)
                    if isinstance(val, dict):
                        found = LeclercScraper._deep_find_price(val, depth + 1)
                        if found:
                            return found
            # Explorer 'offers' qui contient souvent les prix par magasin
            if 'offers' in obj and isinstance(obj['offers'], list):
                for offer in obj['offers'][:3]:
                    found = LeclercScraper._deep_find_price(offer, depth + 1)
                    if found:
                        return found
        if isinstance(obj, list):
            for item in obj[:3]:
                found = LeclercScraper._deep_find_price(item, depth + 1)
                if found:
                    return found
        return None

    @staticmethod
    def _deep_find_image(obj, depth=0):
        """Cherche récursivement une URL d'image dans un objet imbriqué."""
        if depth > 3:
            return ''
        if isinstance(obj, str) and ('http' in obj) and any(
                ext in obj.lower() for ext in ('.jpg', '.png', '.webp', '.jpeg')):
            return obj
        if isinstance(obj, dict):
            for key in ('image', 'url', 'src', 'href', 'thumbnail', 'media'):
                if key in obj:
                    found = LeclercScraper._deep_find_image(obj[key], depth + 1)
                    if found:
                        return found
            if 'medias' in obj and isinstance(obj['medias'], list):
                for m in obj['medias'][:3]:
                    found = LeclercScraper._deep_find_image(m, depth + 1)
                    if found:
                        return found
        if isinstance(obj, list):
            for item in obj[:3]:
                found = LeclercScraper._deep_find_image(item, depth + 1)
                if found:
                    return found
        return ''

    def _extract_products_from_json(self, data: dict) -> List[Dict]:
        """Extrait les produits d'une réponse API JSON E.Leclerc.

        L'API product-search retourne un catalogue sans prix direct.
        Les prix sont parfois dans variants[].offers[].price ou
        attributeGroups. On cherche récursivement.
        """
        products = []

        items = []
        if isinstance(data, dict):
            for key in ('products', 'results', 'hits', 'items', 'data'):
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break

            if not items and 'results' in data and isinstance(data['results'], list):
                for result in data['results']:
                    if isinstance(result, dict) and 'hits' in result:
                        items = result['hits']
                        break
        elif isinstance(data, list):
            items = data

        # Log la structure du 1er produit pour debug (variants, attributeGroups)
        if items and isinstance(items[0], dict):
            first = items[0]
            if 'variants' in first and isinstance(first['variants'], list) and first['variants']:
                v0 = first['variants'][0]
                if isinstance(v0, dict):
                    logger.info(f"[{self.RETAILER_NAME}] variants[0] keys: "
                                f"{list(v0.keys())[:15]}")

        for item in items[:10]:
            if not isinstance(item, dict):
                continue

            name = (item.get('name') or item.get('title') or
                    item.get('product_name') or item.get('label') or '')
            if not name:
                continue

            # Chercher le prix : d'abord au top-level, puis dans variants
            price = None
            for price_key in ('price', 'currentPrice', 'unitPrice',
                              'selling_price', 'salePrice'):
                val = item.get(price_key)
                if val is not None:
                    if isinstance(val, (int, float)):
                        price = float(val)
                        break
                    if isinstance(val, dict):
                        price = self._deep_find_price(val)
                        if price:
                            break

            # Chercher dans variants si pas de prix au top-level
            if not price and 'variants' in item:
                price = self._deep_find_price(item['variants'])

            # URL produit
            product_url = ''
            slug = item.get('slug', '')
            if slug:
                product_url = f"{self.BASE_URL}/fp/{slug}" if not slug.startswith('http') else slug
            else:
                for url_key in ('url', 'href', 'link', 'productUrl'):
                    url_val = item.get(url_key, '')
                    if url_val:
                        product_url = (url_val if url_val.startswith('http')
                                       else f"{self.BASE_URL}{url_val}")
                        break

            # Image : chercher dans variants/medias
            image_url = self._deep_find_image(item.get('variants', []))
            if not image_url:
                image_url = self._deep_find_image(item.get('medias', []))
            if not image_url:
                for img_key in ('image', 'imageUrl', 'thumbnail', 'img'):
                    img_val = item.get(img_key, '')
                    if isinstance(img_val, str) and img_val:
                        image_url = img_val
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
