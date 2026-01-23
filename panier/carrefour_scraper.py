"""
Scraper Carrefour Drive avec interception d'API.

Cette version utilise l'interception des appels réseau pour récupérer
les données JSON directement depuis l'API interne de Carrefour.

Avantages:
- Résistant aux changements CSS/HTML
- Données plus riches (prix au kilo, EAN, images HD)
- Plus rapide (pas besoin d'attendre le rendu complet)
- Contourne mieux les anti-bots
"""

import logging
import re
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Response

logger = logging.getLogger(__name__)

# Import conditionnel de playwright-stealth
try:
    from playwright_stealth import stealth_sync
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    logger.warning("playwright-stealth non installé. Le scraper sera plus détectable.")


class CarrefourScraper:
    """
    Scraper Carrefour utilisant l'interception d'API.

    Au lieu de parser le HTML, on écoute les réponses réseau
    et on capture le JSON retourné par l'API interne.
    """

    RETAILER_NAME = "Carrefour"
    BASE_URL = "https://www.carrefour.fr"
    SEARCH_URL = f"{BASE_URL}/s"

    # Patterns d'URL pour détecter les réponses API contenant des produits
    API_PATTERNS = [
        r'/api/v\d+/search',
        r'/api/products',
        r'search.*products',
        r'graphql',
    ]

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Initialise le scraper Carrefour.

        Args:
            headless: Si True, le navigateur s'exécute sans interface
            timeout: Temps d'attente max en millisecondes
        """
        self.headless = headless
        self.timeout = timeout
        self.found_products: List[Dict] = []
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def __enter__(self):
        """Context manager - démarre le navigateur."""
        self.start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager - ferme le navigateur."""
        self.close_browser()

    def start_browser(self):
        """Démarre Playwright avec les options anti-détection."""
        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )

        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale='fr-FR',
            timezone_id='Europe/Paris',
        )

        self.page = self.context.new_page()

        # Appliquer stealth si disponible
        if STEALTH_AVAILABLE:
            stealth_sync(self.page)
            logger.info("Playwright-stealth activé")

        # Masquer webdriver
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        """)

        logger.info("Navigateur Carrefour démarré")

    def close_browser(self):
        """Ferme proprement le navigateur."""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logger.info("Navigateur Carrefour fermé")

    def _handle_response(self, response: Response):
        """
        Callback pour intercepter les réponses réseau.

        Examine chaque réponse et capture les données produits si trouvées.
        """
        url = response.url

        # Vérifier si c'est une réponse API potentielle
        is_api_response = any(re.search(pattern, url, re.IGNORECASE) for pattern in self.API_PATTERNS)

        if not is_api_response:
            return

        if response.status != 200:
            return

        try:
            content_type = response.headers.get('content-type', '')
            if 'application/json' not in content_type:
                return

            data = response.json()
            products = self._extract_products_from_json(data)

            if products:
                self.found_products.extend(products)
                logger.info(f"Intercepté {len(products)} produits via API: {url[:80]}...")

        except Exception as e:
            logger.debug(f"Erreur parsing réponse {url[:50]}: {e}")

    def _extract_products_from_json(self, data: dict) -> List[Dict]:
        """
        Extrait les produits d'une réponse JSON.

        Carrefour peut avoir plusieurs structures de données,
        cette méthode gère les cas les plus courants.
        """
        products = []

        # Essayer différentes structures possibles
        product_lists = []

        # Structure 1: data.attributes.products
        if isinstance(data, dict):
            attrs = data.get('data', {}).get('attributes', {})
            if 'products' in attrs:
                product_lists.append(attrs['products'])

        # Structure 2: data.products
        if isinstance(data, dict) and 'products' in data:
            product_lists.append(data['products'])

        # Structure 3: data.data (liste directe)
        if isinstance(data, dict) and isinstance(data.get('data'), list):
            product_lists.append(data['data'])

        # Structure 4: results.products
        if isinstance(data, dict):
            results = data.get('results', data.get('result', {}))
            if isinstance(results, dict) and 'products' in results:
                product_lists.append(results['products'])

        # Structure 5: items
        if isinstance(data, dict) and 'items' in data:
            product_lists.append(data['items'])

        # Parcourir toutes les listes trouvées
        for product_list in product_lists:
            if not isinstance(product_list, list):
                continue

            for item in product_list:
                product = self._parse_product_item(item)
                if product:
                    products.append(product)

        return products

    def _parse_product_item(self, item: dict) -> Optional[Dict]:
        """
        Parse un item produit individuel.

        Args:
            item: Dictionnaire représentant un produit

        Returns:
            Dictionnaire normalisé ou None
        """
        if not isinstance(item, dict):
            return None

        # Les données peuvent être dans 'attributes' ou directement dans l'item
        attrs = item.get('attributes', item)

        # Nom du produit
        name = (
            attrs.get('name') or
            attrs.get('title') or
            attrs.get('productName') or
            attrs.get('label') or
            item.get('name')
        )

        if not name:
            return None

        # Prix
        price = None
        price_data = attrs.get('price', {})
        if isinstance(price_data, dict):
            price = price_data.get('value') or price_data.get('amount') or price_data.get('unitPrice')
        elif isinstance(price_data, (int, float)):
            price = price_data
        else:
            price = attrs.get('price') or attrs.get('unitPrice')

        # URL du produit
        product_url = attrs.get('url') or attrs.get('productUrl') or item.get('url')
        if product_url and not product_url.startswith('http'):
            product_url = f"{self.BASE_URL}{product_url}"

        # Image
        image_url = None
        image_data = attrs.get('image', attrs.get('images', []))
        if isinstance(image_data, dict):
            image_url = image_data.get('url') or image_data.get('src')
        elif isinstance(image_data, list) and image_data:
            first_img = image_data[0]
            if isinstance(first_img, dict):
                image_url = first_img.get('url') or first_img.get('src')
            elif isinstance(first_img, str):
                image_url = first_img

        # Disponibilité
        availability = attrs.get('availability', {})
        if isinstance(availability, dict):
            is_available = availability.get('is_available', availability.get('available', True))
        else:
            is_available = attrs.get('available', attrs.get('inStock', True))

        # Marque
        brand = attrs.get('brand') or attrs.get('brandName') or ''

        return {
            'name': str(name).strip(),
            'price': float(price) if price else None,
            'is_available': bool(is_available),
            'url': product_url,
            'image_url': image_url,
            'brand': brand,
            'source': 'carrefour_api'
        }

    def _accept_cookies(self):
        """Accepte le popup de cookies si présent."""
        cookie_selectors = [
            '#didomi-notice-agree-button',
            'button[id*="accept"]',
            'button[id*="cookie"]',
            '#onetrust-accept-btn-handler',
            'button:has-text("Accepter")',
            'button:has-text("Tout accepter")',
        ]

        for selector in cookie_selectors:
            try:
                button = self.page.query_selector(selector)
                if button and button.is_visible():
                    button.click()
                    logger.info("Cookies Carrefour acceptés")
                    self.page.wait_for_timeout(1000)
                    return
            except Exception:
                continue

    def search_product(self, query: str) -> List[Dict]:
        """
        Recherche des produits sur Carrefour.

        Args:
            query: Terme de recherche

        Returns:
            Liste de produits trouvés
        """
        self.found_products = []  # Reset

        # Activer l'interception des réponses
        self.page.on("response", self._handle_response)

        try:
            # Construire l'URL de recherche
            search_url = f"{self.SEARCH_URL}?q={query.replace(' ', '+')}"
            logger.info(f"Recherche Carrefour: {query}")

            # Naviguer vers la page
            self.page.goto(search_url, wait_until="domcontentloaded", timeout=self.timeout)

            # Accepter les cookies
            self._accept_cookies()

            # Attendre que les données arrivent
            self.page.wait_for_timeout(3000)

            # Scroll pour déclencher le chargement lazy
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            self.page.wait_for_timeout(2000)

            # Si on n'a pas trouvé via API, essayer le fallback HTML
            if not self.found_products:
                logger.info("Pas de données API, tentative fallback HTML...")
                self.found_products = self._fallback_html_parsing()

            logger.info(f"{len(self.found_products)} produits trouvés pour '{query}'")
            return self.found_products

        except Exception as e:
            logger.error(f"Erreur recherche Carrefour '{query}': {e}")
            return []
        finally:
            # Désactiver l'écoute pour éviter les doublons
            self.page.remove_listener("response", self._handle_response)

    def _fallback_html_parsing(self) -> List[Dict]:
        """
        Fallback: Parse le HTML si l'interception API échoue.
        """
        products = []

        selectors = [
            'article[data-testid="product"]',
            '.product-card',
            '[class*="ProductCard"]',
            'article.product',
        ]

        for selector in selectors:
            try:
                elements = self.page.query_selector_all(selector)
                if elements:
                    for el in elements[:10]:  # Limiter à 10 produits
                        product = self._parse_html_element(el)
                        if product:
                            products.append(product)
                    break
            except Exception:
                continue

        return products

    def _parse_html_element(self, element) -> Optional[Dict]:
        """Parse un élément HTML produit (fallback)."""
        try:
            # Nom
            name = None
            for selector in ['h2', 'h3', '[data-testid="product-name"]', '.product-name']:
                try:
                    el = element.query_selector(selector)
                    if el:
                        name = el.text_content().strip()
                        if name:
                            break
                except Exception:
                    continue

            if not name:
                return None

            # Prix
            price = None
            for selector in ['[data-testid="product-price"]', '.product-price', '[class*="price"]']:
                try:
                    el = element.query_selector(selector)
                    if el:
                        price_text = el.text_content()
                        price = self._parse_price(price_text)
                        if price:
                            break
                except Exception:
                    continue

            # URL
            url = None
            try:
                link = element.query_selector('a')
                if link:
                    href = link.get_attribute('href')
                    if href:
                        url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
            except Exception:
                pass

            return {
                'name': name,
                'price': price,
                'is_available': True,
                'url': url,
                'source': 'carrefour_html_fallback'
            }

        except Exception as e:
            logger.debug(f"Erreur parsing HTML: {e}")
            return None

    def _parse_price(self, price_text: str) -> Optional[float]:
        """Extrait le prix d'une chaîne de caractères."""
        if not price_text:
            return None

        try:
            # Nettoyer: "12,99 €" -> "12.99"
            cleaned = price_text.replace('€', '').replace(',', '.').strip()
            # Extraire le premier nombre
            match = re.search(r'(\d+\.?\d*)', cleaned)
            if match:
                return float(match.group(1))
        except Exception:
            pass

        return None


def search_carrefour_products(ingredient_name: str) -> List[Dict]:
    """
    Fonction utilitaire pour rechercher des produits Carrefour.

    Args:
        ingredient_name: Nom de l'ingrédient à rechercher

    Returns:
        Liste de produits trouvés
    """
    with CarrefourScraper(headless=True) as scraper:
        products = scraper.search_product(ingredient_name)
    return products
