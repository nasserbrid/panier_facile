"""Scraper Lidl - logique spécifique à lidl.fr."""

import logging
from typing import Dict, List, Optional
from urllib.parse import quote_plus

from .base import BaseScraper, random_delay

logger = logging.getLogger(__name__)


class LidlScraper(BaseScraper):

    RETAILER_NAME = "Lidl"
    BASE_URL = "https://www.lidl.fr"
    SEARCH_URL = "https://www.lidl.fr/q/search"

    # Lidl charge les résultats côté client (Vue.js).
    # Pas d'API JSON connue à intercepter.
    API_PATTERNS = []

    # ── Session ──────────────────────────────────────────────────

    def _establish_session(self):
        """Skip la homepage : navigation directe vers /q/search."""
        if self._session_established:
            return
        self._session_established = True
        logger.info(f"[{self.RETAILER_NAME}] Session initialisée (navigation directe)")

    # ── Recherche ───────────────────────────────────────────────

    def _perform_search(self, query: str) -> None:
        """Navigation directe vers l'URL de recherche Lidl."""
        url = f"{self.SEARCH_URL}?q={quote_plus(query)}"
        self.page.goto(url, wait_until="domcontentloaded",
                       timeout=self.timeout)

        # Attendre que des produits apparaissent dans le DOM.
        # Lidl utilise un grid system ODS avec des cartes produits.
        selectors = [
            '.product-grid-box',
            '.product-item',
            '[data-grid-box]',
            'article',
            '.ods-grid__item a[href*="/p/"]',
        ]

        for selector in selectors:
            try:
                self.page.wait_for_selector(selector, timeout=5000)
                logger.info(f"[Lidl] Produits chargés avec: {selector}")
                return
            except Exception:
                continue

        logger.warning(f"[Lidl] Timeout: aucun produit trouvé pour '{query}'")

    # ── Extraction API (non utilisée pour Lidl) ──────────────────

    def _extract_products_from_json(self, data: dict) -> List[Dict]:
        return []

    # ── Parsing HTML (méthode principale pour Lidl) ──────────────

    def _fallback_html_parsing(self) -> List[Dict]:
        """Parse le DOM rendu pour extraire les produits Lidl."""
        products_data = self.page.evaluate("""
        () => {
            const products = [];
            const seen = new Set();

            // Stratégie 1: Chercher les cartes produit avec prix
            const allCards = document.querySelectorAll(
                '.product-grid-box, [class*="product"], article, [data-grid-box]'
            );

            for (const card of allCards) {
                // Chercher un lien vers une page produit
                const link = card.querySelector('a[href]');
                if (!link) continue;

                const href = link.getAttribute('href') || '';
                if (seen.has(href)) continue;

                // Chercher le nom du produit
                const nameEl = card.querySelector(
                    'h2, h3, h4, ' +
                    '[class*="name"], [class*="title"], [class*="Name"], [class*="Title"], ' +
                    '.product-grid-box__title, .product-title'
                );
                const name = nameEl ? nameEl.textContent.trim() : '';
                if (!name || name.length < 2) continue;

                seen.add(href);

                // Chercher le prix
                let price = null;
                const priceEls = card.querySelectorAll(
                    '[class*="price"], [class*="Price"], ' +
                    '.m-price, .product-price, .tag__label--price, ' +
                    '[data-price]'
                );
                for (const priceEl of priceEls) {
                    const text = priceEl.textContent
                        .replace(/\\s+/g, '')
                        .replace(',', '.')
                        .replace('€', '')
                        .replace('*', '');
                    const match = text.match(/(\\d+\\.?\\d*)/);
                    if (match) {
                        price = parseFloat(match[1]);
                        break;
                    }
                }

                // Image
                const imgEl = card.querySelector('img');
                const imageUrl = imgEl
                    ? (imgEl.src || imgEl.dataset.src || imgEl.getAttribute('loading') === 'lazy' ? imgEl.dataset.src || imgEl.src : '')
                    : '';

                // Marque
                const brandEl = card.querySelector(
                    '[class*="brand"], [class*="Brand"], .product-brand'
                );
                const brand = brandEl ? brandEl.textContent.trim() : '';

                const fullUrl = href.startsWith('http')
                    ? href
                    : 'https://www.lidl.fr' + href;

                products.push({
                    product_name: name,
                    price: price,
                    product_url: fullUrl,
                    image_url: imageUrl || '',
                    brand: brand,
                    is_available: true
                });

                if (products.length >= 10) break;
            }

            // Stratégie 2: Si rien trouvé, chercher tout élément avec prix
            if (products.length === 0) {
                const links = document.querySelectorAll('a[href*="/p/"]');
                for (const link of links) {
                    const href = link.getAttribute('href') || '';
                    if (seen.has(href)) continue;
                    seen.add(href);

                    const container = link.closest('div, article, section') || link;
                    const name = link.textContent.trim() ||
                        (container.querySelector('h2, h3, h4') || {}).textContent || '';
                    if (!name || name.length < 2) continue;

                    let price = null;
                    const priceEl = container.querySelector('[class*="price"]');
                    if (priceEl) {
                        const text = priceEl.textContent
                            .replace(/\\s+/g, '')
                            .replace(',', '.')
                            .replace('€', '');
                        const match = text.match(/(\\d+\\.?\\d*)/);
                        if (match) price = parseFloat(match[1]);
                    }

                    products.push({
                        product_name: name.substring(0, 200),
                        price: price,
                        product_url: href.startsWith('http')
                            ? href
                            : 'https://www.lidl.fr' + href,
                        image_url: '',
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
            logger.warning("[Lidl] Aucun produit trouvé dans le DOM")
            return []

        logger.info(f"[Lidl] {len(products_data)} produits extraits du DOM")
        return products_data
