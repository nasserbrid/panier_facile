"""
Scraper Auchan Drive avec interception d'API.

Cette version utilise l'interception des appels réseau pour récupérer
les données JSON directement depuis l'API interne d'Auchan.

Avantages:
- Résistant aux changements CSS/HTML
- Données plus riches (prix au kilo, EAN, images HD)
- Plus rapide (pas besoin d'attendre le rendu complet)
- Contourne mieux les anti-bots
"""

import logging
import random
import re
import time
from typing import List, Dict, Optional
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright, Response

logger = logging.getLogger(__name__)


def random_delay(min_ms: int = 500, max_ms: int = 1500) -> None:
    """Pause aléatoire pour simuler un comportement humain."""
    time.sleep(random.randint(min_ms, max_ms) / 1000)

# Import conditionnel de playwright-stealth
try:
    from playwright_stealth import stealth_sync
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False
    logger.warning("playwright-stealth non installé. Le scraper sera plus détectable.")


class AuchanScraper:
    """
    Scraper Auchan utilisant l'interception d'API.

    Au lieu de parser le HTML, on écoute les réponses réseau
    et on capture le JSON retourné par l'API interne.
    """

    RETAILER_NAME = "Auchan"
    BASE_URL = "https://www.auchan.fr"
    SEARCH_URL = f"{BASE_URL}/recherche"

    # Patterns d'URL pour détecter les réponses API contenant des produits
    API_PATTERNS = [
        r'/api/v\d+/search',
        r'/api/products',
        r'search.*products',
        r'graphql',
        r'/search\?',
        r'algolia',
    ]

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Initialise le scraper Auchan.

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
        """Démarre Playwright avec les options anti-détection avancées."""
        self.playwright = sync_playwright().start()

        # Arguments Chrome anti-détection avancés
        chrome_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-infobars',
            '--disable-extensions',
            '--disable-gpu',
            '--disable-setuid-sandbox',
            f'--window-position={random.randint(0, 100)},{random.randint(0, 100)}',
        ]

        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=chrome_args
        )

        # User-Agent récent (Chrome 131 - Janvier 2026)
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        ]

        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=random.choice(user_agents),
            locale='fr-FR',
            timezone_id='Europe/Paris',
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
                'Cache-Control': 'no-cache',
                'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            },
        )

        self.page = self.context.new_page()

        # Appliquer stealth si disponible
        if STEALTH_AVAILABLE:
            stealth_sync(self.page)
            logger.info("Playwright-stealth activé")

        # Scripts anti-détection avancés
        self.page.add_init_script("""
            // Masquer webdriver
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            delete navigator.__proto__.webdriver;

            // Simuler plugins réalistes
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const plugins = [
                        {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                        {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                        {name: 'Native Client', filename: 'internal-nacl-plugin'},
                    ];
                    plugins.item = (i) => plugins[i];
                    plugins.namedItem = (n) => plugins.find(p => p.name === n);
                    plugins.refresh = () => {};
                    return plugins;
                }
            });

            // Languages réalistes
            Object.defineProperty(navigator, 'languages', {get: () => ['fr-FR', 'fr', 'en-US', 'en']});

            // Hardware réaliste
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});

            // Chrome runtime
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };

            // Permissions API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // Écran réaliste
            Object.defineProperty(screen, 'availWidth', {get: () => 1920});
            Object.defineProperty(screen, 'availHeight', {get: () => 1040});
        """)

        logger.info("Navigateur Auchan démarré (anti-détection avancée)")

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

        Auchan peut avoir plusieurs structures de données,
        cette méthode gère les cas les plus courants.
        """
        products = []

        # Essayer différentes structures possibles
        product_lists = []

        # Structure 1: data.products
        if isinstance(data, dict) and 'products' in data:
            product_lists.append(data['products'])

        # Structure 2: hits (Algolia)
        if isinstance(data, dict) and 'hits' in data:
            product_lists.append(data['hits'])

        # Structure 3: data.data (liste directe)
        if isinstance(data, dict) and isinstance(data.get('data'), list):
            product_lists.append(data['data'])

        # Structure 4: results.products
        if isinstance(data, dict):
            results = data.get('results', data.get('result', {}))
            if isinstance(results, dict) and 'products' in results:
                product_lists.append(results['products'])
            elif isinstance(results, list):
                product_lists.append(results)

        # Structure 5: items
        if isinstance(data, dict) and 'items' in data:
            product_lists.append(data['items'])

        # Structure 6: content.products
        if isinstance(data, dict):
            content = data.get('content', {})
            if isinstance(content, dict) and 'products' in content:
                product_lists.append(content['products'])

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

        # Les données peuvent être dans différents endroits
        attrs = item.get('attributes', item)

        # Nom du produit
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

        # Prix
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

        # URL du produit
        product_url = attrs.get('url') or attrs.get('productUrl') or attrs.get('slug') or item.get('url')
        if product_url and not product_url.startswith('http'):
            product_url = f"{self.BASE_URL}{product_url}" if product_url.startswith('/') else f"{self.BASE_URL}/{product_url}"

        # Image
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

        # Disponibilité
        availability = attrs.get('availability', attrs.get('disponibilite', {}))
        if isinstance(availability, dict):
            is_available = availability.get('is_available', availability.get('available', True))
        else:
            is_available = attrs.get('available', attrs.get('inStock', attrs.get('disponible', True)))

        # Marque
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
        """
        Sélectionne un magasin Auchan Drive pour obtenir les prix locaux.

        Cette méthode navigue vers la page de sélection de magasin,
        entre le code postal et sélectionne le premier Drive disponible.

        Args:
            postal_code: Code postal pour la recherche de magasin
            store_name: Nom du magasin à sélectionner (optionnel)

        Returns:
            True si un magasin a été sélectionné, False sinon
        """
        if not postal_code:
            logger.info("Pas de code postal fourni, recherche sans magasin spécifique")
            return False

        try:
            logger.info(f"Sélection du magasin Auchan pour le code postal {postal_code}")

            # Aller sur la page d'accueil pour accéder au sélecteur de magasin
            self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=self.timeout)
            self._accept_cookies()
            self.page.wait_for_timeout(2000)

            # Chercher le bouton/lien de sélection de magasin
            store_selector_buttons = [
                '[data-testid="store-selector"]',
                'button:has-text("Choisir mon magasin")',
                'button:has-text("Mon magasin")',
                'a:has-text("Choisir mon magasin")',
                '[class*="store-selector"]',
                '[class*="StoreSelector"]',
                'button[aria-label*="magasin"]',
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

                # Chercher le champ de saisie du code postal
                postal_input_selectors = [
                    'input[placeholder*="code postal"]',
                    'input[placeholder*="Code postal"]',
                    'input[name*="postal"]',
                    'input[name*="zipcode"]',
                    'input[type="text"][class*="search"]',
                    'input[aria-label*="code postal"]',
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

                    # Appuyer sur Entrée ou chercher un bouton de recherche
                    postal_input.press("Enter")
                    self.page.wait_for_timeout(3000)

                    # Sélectionner le premier magasin Drive disponible
                    drive_selectors = [
                        'button:has-text("Drive")',
                        '[class*="drive"]',
                        'button:has-text("Choisir")',
                        'button:has-text("Sélectionner")',
                        '[data-testid="store-select-button"]',
                    ]

                    for selector in drive_selectors:
                        try:
                            drive_btn = self.page.query_selector(selector)
                            if drive_btn and drive_btn.is_visible():
                                drive_btn.click()
                                logger.info(f"Magasin Auchan Drive sélectionné pour {postal_code}")
                                self.page.wait_for_timeout(2000)
                                return True
                        except Exception:
                            continue

            logger.warning(f"Impossible de sélectionner un magasin Auchan pour {postal_code}")
            return False

        except Exception as e:
            logger.error(f"Erreur lors de la sélection du magasin Auchan: {e}")
            return False

    def search_product(self, query: str) -> List[Dict]:
        """
        Recherche des produits sur Auchan.

        Args:
            query: Terme de recherche

        Returns:
            Liste de produits trouvés
        """
        self.found_products = []  # Reset

        # Activer l'interception des réponses
        self.page.on("response", self._handle_response)

        try:
            # Délai aléatoire entre les recherches (comportement humain)
            random_delay(300, 800)

            # Construire l'URL de recherche
            encoded_query = quote_plus(query)
            search_url = f"{self.SEARCH_URL}?text={encoded_query}"
            logger.info(f"Recherche Auchan: {query}")

            # Naviguer vers la page
            self.page.goto(search_url, wait_until="domcontentloaded", timeout=self.timeout)

            # Accepter les cookies
            self._accept_cookies()

            # Attendre que les données arrivent (délai variable)
            self.page.wait_for_timeout(random.randint(2500, 4000))

            # Scroll progressif pour simuler un comportement humain
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
            random_delay(500, 1000)
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            self.page.wait_for_timeout(random.randint(1500, 2500))

            # Si on n'a pas trouvé via API, essayer le fallback HTML
            if not self.found_products:
                logger.info("Pas de données API, tentative fallback HTML...")
                self.found_products = self._fallback_html_parsing()

            logger.info(f"{len(self.found_products)} produits trouvés pour '{query}'")
            return self.found_products

        except Exception as e:
            logger.error(f"Erreur recherche Auchan '{query}': {e}")
            return []
        finally:
            # Désactiver l'écoute pour éviter les doublons
            self.page.remove_listener("response", self._handle_response)

    def _fallback_html_parsing(self) -> List[Dict]:
        """
        Fallback: Parse le HTML si l'interception API échoue.
        Sélecteurs mis à jour pour Auchan 2026.
        """
        products = []

        # Sélecteurs mis à jour pour le site Auchan actuel
        selectors = [
            '[data-testid="product-card"]',
            '[data-test-id="product-card"]',
            'li[data-testid="product-item"]',
            '.product-item',
            '.productListItem',
            '[class*="ProductCard"]',
            '[class*="product-grid-item"]',
            'article[data-product-id]',
            '.product-card',
            'div[data-product-sku]',
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

            # Prix
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

            # Image
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
            # Nettoyer: "12,99 €" -> "12.99"
            cleaned = price_text.replace('€', '').replace(',', '.').strip()
            # Extraire le premier nombre
            match = re.search(r'(\d+\.?\d*)', cleaned)
            if match:
                return float(match.group(1))
        except Exception:
            pass

        return None


def search_auchan_products(ingredient_name: str) -> List[Dict]:
    """
    Fonction utilitaire pour rechercher des produits Auchan.

    Args:
        ingredient_name: Nom de l'ingrédient à rechercher

    Returns:
        Liste de produits trouvés
    """
    with AuchanScraper(headless=True) as scraper:
        products = scraper.search_product(ingredient_name)
    return products
