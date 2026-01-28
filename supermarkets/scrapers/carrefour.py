"""
Scraper Carrefour Drive avec interception d'API.

Cette version utilise l'interception des appels réseau pour récupérer
les données JSON directement depuis l'API interne de Carrefour.
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
    logger.warning("playwright-stealth non installé.")


class CarrefourDriveScraper:
    """
    Scraper Carrefour utilisant l'interception d'API.
    """

    RETAILER_NAME = "Carrefour"
    BASE_URL = "https://www.carrefour.fr"
    SEARCH_URL = f"{BASE_URL}/s"

    API_PATTERNS = [
        r'/api/v\d+/search',
        r'/api/products',
        r'search.*products',
        r'graphql',
    ]

    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.found_products: List[Dict] = []
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def __enter__(self):
        self.start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
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

        if STEALTH_AVAILABLE:
            stealth_sync(self.page)

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
        """Intercepte les réponses réseau."""
        url = response.url

        is_api_response = any(re.search(pattern, url, re.IGNORECASE) for pattern in self.API_PATTERNS)

        if not is_api_response or response.status != 200:
            return

        try:
            content_type = response.headers.get('content-type', '')
            if 'application/json' not in content_type:
                return

            data = response.json()
            products = self._extract_products_from_json(data)

            if products:
                self.found_products.extend(products)
                logger.info(f"Intercepté {len(products)} produits Carrefour")

        except Exception as e:
            logger.debug(f"Erreur parsing réponse: {e}")

    def _extract_products_from_json(self, data: dict) -> List[Dict]:
        """Extrait les produits d'une réponse JSON."""
        products = []
        product_lists = []

        if isinstance(data, dict):
            attrs = data.get('data', {}).get('attributes', {})
            if 'products' in attrs:
                product_lists.append(attrs['products'])

        if isinstance(data, dict) and 'products' in data:
            product_lists.append(data['products'])

        if isinstance(data, dict) and isinstance(data.get('data'), list):
            product_lists.append(data['data'])

        if isinstance(data, dict):
            results = data.get('results', data.get('result', {}))
            if isinstance(results, dict) and 'products' in results:
                product_lists.append(results['products'])

        if isinstance(data, dict) and 'items' in data:
            product_lists.append(data['items'])

        for product_list in product_lists:
            if not isinstance(product_list, list):
                continue

            for item in product_list:
                product = self._parse_product_item(item)
                if product:
                    products.append(product)

        return products

    def _parse_product_item(self, item: dict) -> Optional[Dict]:
        """Parse un item produit individuel."""
        if not isinstance(item, dict):
            return None

        attrs = item.get('attributes', item)

        name = (
            attrs.get('name') or
            attrs.get('title') or
            attrs.get('productName') or
            attrs.get('label') or
            item.get('name')
        )

        if not name:
            return None

        price = None
        price_data = attrs.get('price', {})
        if isinstance(price_data, dict):
            price = price_data.get('value') or price_data.get('amount') or price_data.get('unitPrice')
        elif isinstance(price_data, (int, float)):
            price = price_data
        else:
            price = attrs.get('price') or attrs.get('unitPrice')

        product_url = attrs.get('url') or attrs.get('productUrl') or item.get('url')
        if product_url and not product_url.startswith('http'):
            product_url = f"{self.BASE_URL}{product_url}"

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

        availability = attrs.get('availability', {})
        if isinstance(availability, dict):
            is_available = availability.get('is_available', availability.get('available', True))
        else:
            is_available = attrs.get('available', attrs.get('inStock', True))

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
        """Recherche des produits sur Carrefour."""
        self.found_products = []

        self.page.on("response", self._handle_response)

        try:
            search_url = f"{self.SEARCH_URL}?q={query.replace(' ', '+')}"
            logger.info(f"Recherche Carrefour: {query}")

            self.page.goto(search_url, wait_until="domcontentloaded", timeout=self.timeout)
            self._accept_cookies()
            self.page.wait_for_timeout(3000)

            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            self.page.wait_for_timeout(2000)

            if not self.found_products:
                logger.info("Fallback HTML Carrefour...")
                self.found_products = self._fallback_html_parsing()

            logger.info(f"{len(self.found_products)} produits trouvés")
            return self.found_products

        except Exception as e:
            logger.error(f"Erreur recherche Carrefour: {e}")
            return []
        finally:
            self.page.remove_listener("response", self._handle_response)

    def _fallback_html_parsing(self) -> List[Dict]:
        """Fallback: Parse le HTML si l'interception API échoue."""
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
                    for el in elements[:10]:
                        product = self._parse_html_element(el)
                        if product:
                            products.append(product)
                    break
            except Exception:
                continue

        return products

    def _parse_html_element(self, element) -> Optional[Dict]:
        """Parse un élément HTML produit."""
        try:
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
            cleaned = price_text.replace('€', '').replace(',', '.').strip()
            match = re.search(r'(\d+\.?\d*)', cleaned)
            if match:
                return float(match.group(1))
        except Exception:
            pass

        return None


def search_carrefour_products(ingredient_name: str) -> List[Dict]:
    """Fonction utilitaire pour rechercher des produits Carrefour."""
    with CarrefourDriveScraper(headless=True) as scraper:
        products = scraper.search_product(ingredient_name)
    return products
