"""
Base abstraite pour tous les scrapers de Drive (Intermarché, Carrefour, Auchan, etc.)

Design Pattern: Template Method + Strategy
- Template Method: define le flow commun (start_browser, search, extract, close)
- Strategy: chaque enseigne implémente sa propre logique de scraping
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import logging
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

logger = logging.getLogger(__name__)


class BaseDriveScraper(ABC):
    """
    Classe abstraite de base pour tous les scrapers Drive.

    Chaque enseigne (Carrefour, Intermarché, Auchan, etc.) doit hériter
    de cette classe et implémenter les méthodes abstraites.
    """

    # À surcharger par les classes filles
    RETAILER_NAME = "Generic"
    BASE_URL = ""
    SEARCH_URL = ""

    def __init__(self, headless: bool = True, timeout: int = 20000):
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
        """
        Démarre Playwright avec configuration anti-détection.
        Template method qui peut être surchargée pour des besoins spécifiques.
        """
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

            # Créer un contexte avec un user agent réaliste
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=self._get_user_agent(),
                locale='fr-FR',
                timezone_id='Europe/Paris',
                extra_http_headers={
                    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
                }
            )

            # Masquer les propriétés webdriver
            self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                delete navigator.__proto__.webdriver;

                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                Object.defineProperty(navigator, 'languages', {
                    get: () => ['fr-FR', 'fr', 'en-US', 'en']
                });

                window.chrome = {
                    runtime: {}
                };
            """)

            # Créer une page
            self.page = self.context.new_page()
            self.page.set_default_timeout(self.timeout)

            logger.info(f"Playwright démarré pour {self.RETAILER_NAME} (mode anti-détection)")

        except Exception as e:
            logger.error(f"Erreur lors du démarrage de Playwright pour {self.RETAILER_NAME}: {e}")
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
            logger.info(f"Playwright {self.RETAILER_NAME} fermé")
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture de Playwright {self.RETAILER_NAME}: {e}")

    def _get_user_agent(self) -> str:
        """
        Retourne le user agent à utiliser.
        Peut être surchargé par les classes filles si besoin.
        """
        return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    @abstractmethod
    def _get_search_url(self, query: str) -> str:
        """
        Construit l'URL de recherche pour une requête donnée.

        Args:
            query: Terme de recherche

        Returns:
            URL complète de recherche
        """
        pass

    @abstractmethod
    def _get_product_selectors(self) -> List[str]:
        """
        Retourne la liste des sélecteurs CSS possibles pour les produits.

        Returns:
            Liste de sélecteurs CSS à tester
        """
        pass

    @abstractmethod
    def _handle_cookie_popup(self):
        """
        Gère le popup de cookies spécifique à l'enseigne.
        """
        pass

    @abstractmethod
    def _extract_product_data(self, element) -> Optional[Dict]:
        """
        Extrait les données d'un élément produit.

        Args:
            element: ElementHandle Playwright représentant un produit

        Returns:
            Dictionnaire avec les données du produit ou None
        """
        pass

    def search_product(self, query: str) -> List[Dict]:
        """
        Recherche un produit sur l'enseigne.
        Template method qui orchestre le flow de recherche.

        Args:
            query: Terme de recherche (nom de l'ingrédient)

        Returns:
            Liste de dictionnaires contenant les informations produits
        """
        if not self.page:
            self.start_browser()

        products = []

        try:
            # Construire l'URL de recherche
            search_url = self._get_search_url(query)
            logger.info(f"Recherche {self.RETAILER_NAME} de '{query}' sur {search_url}")

            # Naviguer vers la page de recherche
            self.page.goto(search_url, wait_until='domcontentloaded')

            # Attendre de façon aléatoire pour simuler comportement humain
            import random
            import time
            random_wait = random.uniform(1.5, 3)
            time.sleep(random_wait)

            # Gérer le popup cookies si présent
            self._handle_cookie_popup()
            time.sleep(random.uniform(0.5, 1))

            logger.info(f"URL actuelle: {self.page.url}")
            logger.info(f"Titre: {self.page.title()}")

            # Sélecteurs possibles pour les produits
            possible_selectors = self._get_product_selectors()

            product_elements = None
            for selector in possible_selectors:
                try:
                    self.page.wait_for_selector(selector, timeout=8000)
                    product_elements = self.page.query_selector_all(selector)
                    if product_elements and len(product_elements) > 0:
                        logger.info(f"Sélecteur '{selector}' trouvé - {len(product_elements)} produits")
                        break
                except Exception:
                    continue

            if not product_elements:
                logger.warning(f"Aucun produit {self.RETAILER_NAME} trouvé pour '{query}'")
                return products

            # Extraire les données (limiter à 10)
            for element in product_elements[:10]:
                try:
                    product_data = self._extract_product_data(element)
                    if product_data:
                        # Ajouter la source (nom de l'enseigne)
                        product_data['source'] = f'{self.RETAILER_NAME.lower()}_playwright'
                        products.append(product_data)
                except Exception as e:
                    logger.error(f"Erreur extraction produit {self.RETAILER_NAME}: {e}")
                    continue

            logger.info(f"{len(products)} produits {self.RETAILER_NAME} extraits pour '{query}'")

        except Exception as e:
            logger.error(f"Erreur recherche {self.RETAILER_NAME} '{query}': {e}")

        return products

    def _parse_price(self, price_text: str) -> Optional[float]:
        """
        Parse une chaîne de prix en float.
        Logique commune à toutes les enseignes (peut être surchargée).

        Args:
            price_text: Texte du prix (ex: "3,99 €", "3.99€")

        Returns:
            Prix en float ou None
        """
        try:
            import re
            # Supprimer €, espaces, etc.
            clean_price = price_text.replace('€', '').replace(' ', '').strip()
            # Remplacer virgule par point
            clean_price = clean_price.replace(',', '.')
            # Extraire seulement les chiffres et le point
            match = re.search(r'(\d+\.?\d*)', clean_price)
            if match:
                return float(match.group(1))
            return None
        except (ValueError, AttributeError):
            logger.warning(f"Impossible de parser le prix {self.RETAILER_NAME}: {price_text}")
            return None
