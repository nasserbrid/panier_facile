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
import os
import random
import re
import time
from datetime import datetime
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Response

logger = logging.getLogger(__name__)

# Dossier pour les captures de debug (en cas de 0 produits)
DEBUG_DIR = "/tmp/scraper_debug"


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
        self._session_established = False

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

        logger.info("Navigateur Carrefour démarré (anti-détection avancée)")

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

    def _is_blocked_by_datadome(self) -> bool:
        """Détecte si la page est bloquée par DataDome."""
        try:
            # Indicateurs de blocage DataDome
            page_content = self.page.content().lower()
            blocked_indicators = [
                'datadome',
                'captcha',
                'robot',
                'accès refusé',
                'access denied',
                'please verify',
                'vérification',
                'checking your browser',
                'just a moment',
            ]
            for indicator in blocked_indicators:
                if indicator in page_content:
                    logger.warning(f"Blocage DataDome détecté: '{indicator}' trouvé dans la page")
                    return True
            return False
        except Exception as e:
            logger.debug(f"Erreur vérification DataDome: {e}")
            return False

    def _save_debug_info(self, query: str, reason: str = "0_products"):
        """Sauvegarde screenshot et HTML pour debug quand 0 produits trouvés."""
        try:
            os.makedirs(DEBUG_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_query = re.sub(r'[^\w\-]', '_', query)[:30]

            # Screenshot
            screenshot_path = f"{DEBUG_DIR}/carrefour_{reason}_{safe_query}_{timestamp}.png"
            self.page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot sauvegardé: {screenshot_path}")

            # HTML content
            html_path = f"{DEBUG_DIR}/carrefour_{reason}_{safe_query}_{timestamp}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(self.page.content())
            logger.info(f"HTML sauvegardé: {html_path}")

            # Info supplémentaires
            logger.info(f"Debug - URL actuelle: {self.page.url}")
            logger.info(f"Debug - Titre page: {self.page.title()}")

        except Exception as e:
            logger.warning(f"Erreur sauvegarde debug: {e}")

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

    def _handle_location_popup(self):
        """Gère le popup de localisation si présent."""
        location_selectors = [
            'button:has-text("Plus tard")',
            'button:has-text("Ignorer")',
            'button:has-text("Non merci")',
            'button:has-text("Fermer")',
            '[data-testid="close-modal"]',
            '[aria-label="Fermer"]',
            '.modal-close',
            'button.close',
        ]

        for selector in location_selectors:
            try:
                button = self.page.query_selector(selector)
                if button and button.is_visible():
                    button.click()
                    logger.info("Popup localisation fermé")
                    self.page.wait_for_timeout(500)
                    return True
            except Exception:
                continue
        return False

    def _establish_session(self):
        """
        Établit une session de navigation naturelle.

        Flow naturel pour éviter la détection DataDome:
        1. Visiter la page d'accueil
        2. Accepter les cookies
        3. Gérer le popup de localisation
        4. Rester sur homepage pour utiliser la barre de recherche
        """
        if self._session_established:
            return

        logger.info("Établissement de la session Carrefour...")

        try:
            # Étape 1: Page d'accueil
            logger.info("  1/3 - Visite page d'accueil...")
            self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=self.timeout)
            random_delay(1500, 2500)

            # Vérifier si bloqué par DataDome dès la homepage
            if self._is_blocked_by_datadome():
                logger.error("BLOQUÉ par DataDome dès la page d'accueil!")
                self._save_debug_info("homepage", "datadome_blocked")
                return

            # Étape 2: Cookies
            logger.info("  2/3 - Gestion cookies...")
            self._accept_cookies()
            random_delay(800, 1200)

            # Simuler un scroll sur la homepage (comportement humain)
            self.page.evaluate("window.scrollTo(0, 300)")
            random_delay(500, 800)

            # Étape 3: Gérer le popup de localisation
            logger.info("  3/3 - Gestion popup localisation...")
            self._handle_location_popup()
            random_delay(500, 1000)

            # Remonter en haut pour accéder à la barre de recherche
            self.page.evaluate("window.scrollTo(0, 0)")
            random_delay(400, 700)

            self._session_established = True
            logger.info("Session Carrefour établie avec succès")
            logger.info(f"  URL actuelle: {self.page.url}")

        except Exception as e:
            logger.warning(f"Erreur établissement session: {e}")
            self._save_debug_info("session_error", "session_failed")

    def _use_search_bar(self, query: str) -> bool:
        """
        Utilise la barre de recherche de manière naturelle.

        Args:
            query: Terme à rechercher

        Returns:
            True si la recherche a été effectuée, False sinon
        """
        # Sélecteurs pour la barre de recherche Carrefour
        search_selectors = [
            'input[name="q"]',
            'input.c-base-input__input',
            'input[type="search"]',
            'input[placeholder*="recherch"]',
            'input[placeholder*="Recherch"]',
            '#search-input',
            '[data-testid="search-input"]',
        ]

        logger.info(f"Recherche de la barre de recherche sur {self.page.url}...")

        for selector in search_selectors:
            try:
                search_input = self.page.query_selector(selector)
                if search_input:
                    is_visible = search_input.is_visible()
                    logger.info(f"  Sélecteur '{selector}': trouvé, visible={is_visible}")
                    if is_visible:
                        # Cliquer sur le champ
                        search_input.click()
                        random_delay(200, 400)

                        # Effacer le contenu existant
                        search_input.fill('')
                        random_delay(100, 200)

                        # Taper le texte caractère par caractère (plus naturel)
                        for char in query:
                            search_input.type(char, delay=random.randint(50, 150))

                        random_delay(300, 600)

                        # Appuyer sur Entrée
                        search_input.press('Enter')
                        logger.info(f"Recherche via barre de recherche: {query}")
                        return True
                else:
                    logger.debug(f"  Sélecteur '{selector}': non trouvé")
            except Exception as e:
                logger.debug(f"  Sélecteur '{selector}' échoué: {e}")
                continue

        # Si aucune barre trouvée, logger le contenu de la page pour debug
        logger.warning("Aucune barre de recherche visible trouvée!")
        return False

    def search_product(self, query: str) -> List[Dict]:
        """
        Recherche des produits sur Carrefour.

        Args:
            query: Terme de recherche

        Returns:
            Liste de produits trouvés
        """
        self.found_products = []  # Reset

        # Établir la session si pas encore fait (flow naturel anti-DataDome)
        self._establish_session()

        # Activer l'interception des réponses
        self.page.on("response", self._handle_response)

        try:
            # Délai aléatoire entre les recherches (comportement humain)
            random_delay(800, 1500)

            logger.info(f"Recherche Carrefour: {query}")

            # Utiliser la barre de recherche (comportement naturel)
            if not self._use_search_bar(query):
                # Fallback: navigation directe vers l'URL de recherche
                logger.warning("Barre de recherche non trouvée, navigation directe...")
                search_url = f"{self.SEARCH_URL}?q={query.replace(' ', '+')}"
                self.page.goto(search_url, wait_until="domcontentloaded", timeout=self.timeout)

            # Accepter les cookies si popup réapparaît
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

            # Debug si 0 produits trouvés
            if not self.found_products:
                logger.warning(f"0 produits trouvés pour '{query}' - sauvegarde debug...")
                if self._is_blocked_by_datadome():
                    self._save_debug_info(query, "datadome_blocked")
                else:
                    self._save_debug_info(query, "no_products")

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
        Sélecteurs mis à jour pour Carrefour 2026.
        """
        products = []

        # Sélecteurs mis à jour pour le site Carrefour actuel
        selectors = [
            '[data-testid="product-card"]',
            'article[data-testid="product"]',
            'li[data-testid="product-item"]',
            '.product-card',
            '[class*="ProductCard"]',
            '[class*="product-grid-item"]',
            'article.product',
            'div[data-product-id]',
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
