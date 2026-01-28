"""
Scraper Auchan Drive avec interception d'API.

Cette version utilise l'interception des appels réseau pour récupérer
les données JSON directement depuis l'API interne d'Auchan.
"""
import logging
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright, Response

logger = logging.getLogger(__name__)

# Import conditionnel de playwright-stealth
try:
    from playwright_stealth import stealth_sync
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    logger.warning("playwright-stealth non installé.")


class AuchanDriveScraper:
    """
    Scraper Auchan utilisant l'interception d'API.
    """

    RETAILER_NAME = "Auchan"
    BASE_URL = "https://www.auchan.fr"
    SEARCH_URL = f"{BASE_URL}/recherche"

    API_PATTERNS = [
        r'/api/v\d+/search',
        r'/api/products',
        r'search.*products',
        r'graphql',
        r'/search\?',
        r'algolia',
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

        logger.info("Navigateur Auchan démarré")

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
        logger.info("Navigateur Auchan fermé")

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
                logger.info(f"Intercepté {len(products)} produits Auchan")

        except Exception as e:
            logger.debug(f"Erreur parsing réponse: {e}")

    def _extract_products_from_json(self, data: dict) -> List[Dict]:
        """Extrait les produits d'une réponse JSON."""
        products = []
        product_lists = []

        if isinstance(data, dict) and 'products' in data:
            product_lists.append(data['products'])

        if isinstance(data, dict) and 'hits' in data:
            product_lists.append(data['hits'])

        if isinstance(data, dict) and isinstance(data.get('data'), list):
            product_lists.append(data['data'])

        if isinstance(data, dict):
            results = data.get('results', data.get('result', {}))
            if isinstance(results, dict) and 'products' in results:
                product_lists.append(results['products'])
            elif isinstance(results, list):
                product_lists.append(results)

        if isinstance(data, dict) and 'items' in data:
            product_lists.append(data['items'])

        if isinstance(data, dict):
            content = data.get('content', {})
            if isinstance(content, dict) and 'products' in content:
                product_lists.append(content['products'])

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
            attrs.get('libelle') or
            item.get('name')
        )

        if not name:
            return None

        price = None
        price_data = attrs.get('price', attrs.get('prix', {}))
        if isinstance(price_data, dict):
            price = (
                price_data.get('value') or
                price_data.get('amount') or
                price_data.get('unitPrice') or
                price_data.get('selling')
            )
        elif isinstance(price_data, (int, float)):
            price = price_data
        else:
            price = attrs.get('price') or attrs.get('prix') or attrs.get('unitPrice')

        product_url = attrs.get('url') or attrs.get('productUrl') or attrs.get('slug') or item.get('url')
        if product_url and not product_url.startswith('http'):
            product_url = f"{self.BASE_URL}{product_url}" if product_url.startswith('/') else f"{self.BASE_URL}/{product_url}"

        image_url = None
        image_data = attrs.get('image', attrs.get('images', attrs.get('media', [])))
        if isinstance(image_data, dict):
            image_url = image_data.get('url') or image_data.get('src')
        elif isinstance(image_data, list) and image_data:
            first_img = image_data[0]
            if isinstance(first_img, dict):
                image_url = first_img.get('url') or first_img.get('src')
            elif isinstance(first_img, str):
                image_url = first_img
        elif isinstance(image_data, str):
            image_url = image_data

        availability = attrs.get('availability', attrs.get('disponibilite', {}))
        if isinstance(availability, dict):
            is_available = availability.get('is_available', availability.get('available', True))
        else:
            is_available = attrs.get('available', attrs.get('inStock', attrs.get('disponible', True)))

        brand = attrs.get('brand') or attrs.get('brandName') or attrs.get('marque') or ''

        return {
            'product_name': str(name).strip(),
            'price': float(price) if price else None,
            'is_available': bool(is_available),
            'product_url': product_url or '',
            'image_url': image_url or '',
            'brand': brand,
            'source': 'auchan_api'
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
            'button:has-text("J\'accepte")',
        ]

        for selector in cookie_selectors:
            try:
                button = self.page.query_selector(selector)
                if button and button.is_visible():
                    button.click()
                    logger.info("Cookies Auchan acceptés")
                    self.page.wait_for_timeout(1000)
                    return
            except Exception:
                continue

    def select_store(self, postal_code: str = None, store_name: str = None) -> bool:
        """Sélectionne un magasin Auchan Drive."""
        if not postal_code:
            return False

        try:
            logger.info(f"Sélection du magasin Auchan pour {postal_code}")

            self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=self.timeout)
            self._accept_cookies()
            self.page.wait_for_timeout(2000)

            store_selector_buttons = [
                '[data-testid="store-selector"]',
                'button:has-text("Choisir mon magasin")',
                'button:has-text("Mon magasin")',
                'a:has-text("Choisir mon magasin")',
                '[class*="store-selector"]',
                '[class*="StoreSelector"]',
            ]

            store_btn = None
            for selector in store_selector_buttons:
                try:
                    btn = self.page.query_selector(selector)
                    if btn and btn.is_visible():
                        store_btn = btn
                        break
                except Exception:
                    continue

            if store_btn:
                store_btn.click()
                self.page.wait_for_timeout(2000)

                postal_input_selectors = [
                    'input[placeholder*="code postal"]',
                    'input[placeholder*="Code postal"]',
                    'input[name*="postal"]',
                    'input[name*="zipcode"]',
                ]

                postal_input = None
                for selector in postal_input_selectors:
                    try:
                        inp = self.page.query_selector(selector)
                        if inp and inp.is_visible():
                            postal_input = inp
                            break
                    except Exception:
                        continue

                if postal_input:
                    postal_input.fill(postal_code)
                    self.page.wait_for_timeout(1000)
                    postal_input.press("Enter")
                    self.page.wait_for_timeout(3000)

                    drive_selectors = [
                        'button:has-text("Drive")',
                        '[class*="drive"]',
                        'button:has-text("Choisir")',
                        'button:has-text("Sélectionner")',
                    ]

                    for selector in drive_selectors:
                        try:
                            drive_btn = self.page.query_selector(selector)
                            if drive_btn and drive_btn.is_visible():
                                drive_btn.click()
                                logger.info(f"Magasin Auchan Drive sélectionné")
                                self.page.wait_for_timeout(2000)
                                return True
                        except Exception:
                            continue

            return False

        except Exception as e:
            logger.error(f"Erreur sélection magasin Auchan: {e}")
            return False

    def search_product(self, query: str) -> List[Dict]:
        """Recherche des produits sur Auchan."""
        self.found_products = []

        self.page.on("response", self._handle_response)

        try:
            encoded_query = quote_plus(query)
            search_url = f"{self.SEARCH_URL}?text={encoded_query}"
            logger.info(f"Recherche Auchan: {query}")

            self.page.goto(search_url, wait_until="domcontentloaded", timeout=self.timeout)
            self._accept_cookies()
            self.page.wait_for_timeout(3000)

            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            self.page.wait_for_timeout(2000)

            if not self.found_products:
                logger.info("Fallback HTML Auchan...")
                self.found_products = self._fallback_html_parsing()

            logger.info(f"{len(self.found_products)} produits trouvés")
            return self.found_products

        except Exception as e:
            logger.error(f"Erreur recherche Auchan: {e}")
            return []
        finally:
            self.page.remove_listener("response", self._handle_response)

    def _fallback_html_parsing(self) -> List[Dict]:
        """Fallback: Parse le HTML si l'interception API échoue."""
        products = []

        selectors = [
            '[data-test-id="product-card"]',
            '.product-item',
            '.productListItem',
            '[class*="ProductCard"]',
            'article[data-product-id]',
            '.product-card',
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
            for selector in ['h2', 'h3', '[data-test-id="product-name"]', '.product-name', '.product-title']:
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
            for selector in ['[data-test-id="product-price"]', '.product-price', '[class*="price"]', '.price']:
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

            image_url = None
            try:
                img = element.query_selector('img')
                if img:
                    image_url = img.get_attribute('src')
                    if image_url and image_url.startswith('/'):
                        image_url = f"{self.BASE_URL}{image_url}"
            except Exception:
                pass

            return {
                'product_name': name,
                'price': price,
                'is_available': True,
                'product_url': url or '',
                'image_url': image_url or '',
                'source': 'auchan_html_fallback'
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


def search_auchan_products(ingredient_name: str) -> List[Dict]:
    """Fonction utilitaire pour rechercher des produits Auchan."""
    with AuchanDriveScraper(headless=True) as scraper:
        products = scraper.search_product(ingredient_name)
    return products
