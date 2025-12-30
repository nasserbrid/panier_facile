"""
Scraper pour récupérer les produits Intermarché et créer un panier automatique
Utilise Playwright pour contourner les protections anti-bot (DataDome)

Flow:
1. Cherche chaque ingrédient sur https://www.intermarche.com/recherche/{ingredient}
2. Extrait les produits de la page de résultats
3. Ajoute automatiquement les produits au panier
4. Retourne le lien du panier à l'utilisateur

Playwright est plus robuste que Selenium pour éviter la détection:
- Empreinte digitale du navigateur moins détectable
- Meilleure gestion des contextes
- Pas besoin de CAPTCHA solver externe (gratuit!)
"""

import logging
import time
import random
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

logger = logging.getLogger(__name__)


class IntermarcheScraper:
    """
    Scraper pour Intermarché Drive
    Automatise la recherche de produits et l'ajout au panier
    """

    BASE_URL = "https://www.intermarche.com"
    SEARCH_URL = f"{BASE_URL}/recherche"
    CART_URL = f"{BASE_URL}/commandes/panier"

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Initialise le scraper

        Args:
            headless: Si True, le navigateur s'exécute sans interface graphique
            timeout: Temps d'attente max pour les éléments (millisecondes)
        """
        self.headless = headless
        self.timeout = timeout
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def __enter__(self):
        """Context manager: démarre le navigateur"""
        self.start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager: ferme le navigateur"""
        self.close_browser()

    def start_browser(self):
        """Démarre Playwright avec configuration anti-détection"""
        try:
            self.playwright = sync_playwright().start()

            # Lancer Chromium avec des options anti-détection
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                ]
            )

            # Créer un contexte avec un user agent réaliste et des permissions
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='fr-FR',
                timezone_id='Europe/Paris',
                permissions=['geolocation'],
                geolocation={'latitude': 48.8566, 'longitude': 2.3522},  # Paris
                extra_http_headers={
                    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
                }
            )

            # Masquer les propriétés webdriver pour éviter la détection
            self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Masquer les propriétés d'automatisation
                delete navigator.__proto__.webdriver;

                // Simuler les plugins Chrome normaux
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // Langues réalistes
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['fr-FR', 'fr', 'en-US', 'en']
                });

                // Éviter la détection de headless
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32'
                });

                // Chrome runtime
                window.chrome = {
                    runtime: {}
                };
            """)

            # Créer une page
            self.page = self.context.new_page()
            self.page.set_default_timeout(self.timeout)

            logger.info("✅ Playwright démarré avec succès (mode anti-détection activé)")

        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage de Playwright: {e}")
            raise

    def close_browser(self):
        """Ferme le navigateur Playwright"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("Playwright fermé")
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture de Playwright: {e}")

    def search_product(self, query: str) -> List[Dict]:
        """
        Recherche un produit sur Intermarché via /recherche/{ingredient}

        Args:
            query: Terme de recherche (nom de l'ingrédient)

        Returns:
            Liste de dictionnaires contenant les informations produits
        """
        if not self.page:
            self.start_browser()

        products = []

        try:
            # URL de recherche: https://www.intermarche.com/recherche/{query}
            encoded_query = query.replace(' ', '%20')
            search_url = f"{self.SEARCH_URL}/{encoded_query}"
            logger.info(f"🔍 Recherche de '{query}' sur {search_url}")

            # Naviguer vers la page de recherche
            self.page.goto(search_url, wait_until='domcontentloaded')

            # Attendre de façon aléatoire pour simuler un comportement humain
            random_wait = random.uniform(2, 4)
            logger.info(f"⏳ Attente de {random_wait:.1f}s pour simuler un comportement humain")
            time.sleep(random_wait)

            # Gérer le popup cookies si présent
            self._handle_cookie_popup()

            # Attente supplémentaire après le cookie popup
            time.sleep(random.uniform(1, 2))

            # Logger l'URL actuelle pour vérifier les redirections
            logger.info(f"URL actuelle: {self.page.url}")
            logger.info(f"Titre de la page: {self.page.title()}")

            # Vérifier si on est bloqué par un CAPTCHA
            page_content = self.page.content()
            if 'geo.captcha-delivery.com' in page_content or 'datadome' in page_content.lower():
                logger.warning("⚠️  CAPTCHA DataDome détecté - mais Playwright devrait mieux le gérer que Selenium")
                # Attendre un peu plus pour que le challenge se résolve automatiquement
                time.sleep(5)

            # Attendre que les produits se chargent
            # Tester différents sélecteurs possibles
            possible_selectors = [
                '.product-item',
                '.product-card',
                '.ProductCard',
                '[class*="product"]',
                '[data-testid*="product"]',
                'article',
            ]

            product_elements = None
            for selector in possible_selectors:
                try:
                    # Attendre que les éléments soient présents
                    self.page.wait_for_selector(selector, timeout=10000)
                    product_elements = self.page.query_selector_all(selector)
                    if product_elements and len(product_elements) > 0:
                        logger.info(f"✅ Utilisation du sélecteur '{selector}' - {len(product_elements)} produits trouvés")
                        break
                except Exception:
                    continue

            if not product_elements:
                logger.warning(f"❌ Aucun produit trouvé pour '{query}' - aucun sélecteur n'a fonctionné")

                # DEBUG: Sauvegarder screenshot et HTML
                try:
                    screenshot_path = f"/tmp/intermarche_search_{query[:20].replace('/', '_')}.png"
                    self.page.screenshot(path=screenshot_path)
                    logger.info(f"📸 Screenshot sauvegardé: {screenshot_path}")

                    html_content = self.page.content()
                    logger.info(f"HTML de la page (premiers 1000 chars): {html_content[:1000]}")
                except Exception as e:
                    logger.error(f"Erreur lors du debug: {e}")

                return products

            logger.info(f"📦 Trouvé {len(product_elements)} produits pour '{query}'")

            # Extraire les données des produits (limiter à 10 pour performance)
            for element in product_elements[:10]:
                try:
                    product_data = self._extract_product_data(element)
                    if product_data:
                        products.append(product_data)
                except Exception as e:
                    logger.error(f"Erreur lors de l'extraction d'un produit: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ Erreur lors de la recherche de '{query}': {e}")

        return products

    def _handle_cookie_popup(self):
        """Gère le popup de cookies s'il apparaît"""
        try:
            # Chercher le bouton "Tout accepter" ou similaire
            cookie_button = self.page.query_selector('#didomi-notice-agree-button')
            if cookie_button and cookie_button.is_visible():
                cookie_button.click()
                logger.info("✅ Popup cookies accepté")
                time.sleep(1)
        except Exception as e:
            # Pas de popup ou erreur, on continue
            pass

    def _extract_product_data(self, element) -> Optional[Dict]:
        """
        Extrait les données d'un élément produit

        Args:
            element: ElementHandle Playwright représentant un produit

        Returns:
            Dictionnaire avec les données du produit ou None
        """
        try:
            # Nom du produit - essayer plusieurs sélecteurs
            name = None
            name_selectors = [
                '.product-title',
                '[class*="title"]',
                'h2',
                'h3',
                '[data-testid*="title"]'
            ]

            for selector in name_selectors:
                try:
                    name_el = element.query_selector(selector)
                    if name_el:
                        name = name_el.text_content().strip()
                        if name:
                            break
                except:
                    continue

            if not name:
                return None

            # Prix - essayer plusieurs sélecteurs
            price = None
            price_selectors = [
                '.product-price',
                '[class*="price"]',
                '[data-testid*="price"]'
            ]

            for selector in price_selectors:
                try:
                    price_el = element.query_selector(selector)
                    if price_el:
                        price_text = price_el.text_content().strip()
                        price = self._parse_price(price_text)
                        if price:
                            break
                except:
                    continue

            # URL du produit
            product_url = None
            try:
                link_el = element.query_selector('a')
                if link_el:
                    href = link_el.get_attribute('href')
                    if href:
                        product_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
            except:
                pass

            # Disponibilité (par défaut disponible)
            is_available = True
            try:
                out_of_stock = element.query_selector('[class*="out-of-stock"], [class*="indisponible"]')
                is_available = out_of_stock is None
            except:
                pass

            product_data = {
                'name': name,
                'price': price,
                'is_available': is_available,
                'url': product_url,
                'source': 'intermarche_playwright'
            }

            logger.debug(f"Produit extrait: {name} - {price}€")

            return product_data

        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des données produit: {e}")
            return None

    def _parse_price(self, price_text: str) -> Optional[float]:
        """
        Parse une chaîne de prix en float

        Args:
            price_text: Texte du prix (ex: "3,99 €", "3.99€")

        Returns:
            Prix en float ou None
        """
        try:
            # Supprimer le symbole €, espaces, etc.
            clean_price = price_text.replace('€', '').replace(' ', '').strip()
            # Remplacer virgule par point
            clean_price = clean_price.replace(',', '.')
            return float(clean_price)
        except (ValueError, AttributeError):
            logger.warning(f"Impossible de parser le prix: {price_text}")
            return None

    def add_product_to_cart(self, product_element) -> bool:
        """
        Ajoute un produit au panier en cliquant sur le bouton d'ajout

        Args:
            product_element: ElementHandle représentant le produit

        Returns:
            True si l'ajout a réussi, False sinon
        """
        try:
            # Chercher le bouton d'ajout au panier
            button_selectors = [
                '.add-to-cart',
                '.addToCart',
                '.btn-add',
                'button[class*="cart"]',
                'button[class*="ajouter"]'
            ]

            add_button = None
            for selector in button_selectors:
                try:
                    add_button = product_element.query_selector(selector)
                    if add_button and add_button.is_visible():
                        break
                except:
                    continue

            if not add_button:
                logger.warning("Bouton d'ajout au panier non trouvé pour ce produit")
                return False

            # Scroller vers l'élément
            add_button.scroll_into_view_if_needed()
            time.sleep(0.5)

            # Cliquer sur le bouton
            add_button.click()
            logger.info("✅ Produit ajouté au panier")

            # Attendre un peu pour que l'ajout soit effectif
            time.sleep(random.uniform(0.5, 1))

            return True

        except Exception as e:
            logger.error(f"Erreur lors de l'ajout au panier: {e}")
            return False

    def get_cart_url(self) -> str:
        """
        Retourne l'URL du panier Intermarché

        Returns:
            URL du panier
        """
        return self.CART_URL


def search_intermarche_products(ingredient_name: str) -> List[Dict]:
    """
    Fonction utilitaire pour rechercher des produits Intermarché

    Args:
        ingredient_name: Nom de l'ingrédient à rechercher

    Returns:
        Liste de produits trouvés
    """
    with IntermarcheScraper(headless=True) as scraper:
        products = scraper.search_product(ingredient_name)
    return products
