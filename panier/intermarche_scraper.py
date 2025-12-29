"""
Scraper pour récupérer les produits Intermarché
Utilise Selenium pour gérer le JavaScript du site
"""

import logging
import time
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

logger = logging.getLogger(__name__)


class IntermarcheScraper:
    """
    Scraper pour Intermarché Drive
    """

    BASE_URL = "https://www.intermarche.com"
    SEARCH_URL = f"{BASE_URL}/drive/recherche"

    def __init__(self, headless: bool = True, timeout: int = 10):
        """
        Initialise le scraper

        Args:
            headless: Si True, le navigateur s'exécute sans interface graphique
            timeout: Temps d'attente max pour les éléments (secondes)
        """
        self.headless = headless
        self.timeout = timeout
        self.driver = None

    def __enter__(self):
        """Context manager: démarre le navigateur"""
        self.start_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager: ferme le navigateur"""
        self.close_driver()

    def start_driver(self):
        """Démarre le driver Selenium Chrome"""
        try:
            options = Options()

            if self.headless:
                options.add_argument('--headless=new')

            # Options pour compatibilité Docker/serveur
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')

            # User agent pour éviter la détection
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            # Désactiver les images pour aller plus vite
            prefs = {'profile.managed_default_content_settings.images': 2}
            options.add_experimental_option('prefs', prefs)

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(self.timeout)

            logger.info("Driver Selenium démarré avec succès")

        except Exception as e:
            logger.error(f"Erreur lors du démarrage du driver: {e}")
            raise

    def close_driver(self):
        """Ferme le driver Selenium"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Driver Selenium fermé")
            except Exception as e:
                logger.error(f"Erreur lors de la fermeture du driver: {e}")

    def search_product(self, query: str) -> List[Dict]:
        """
        Recherche un produit sur Intermarché

        Args:
            query: Terme de recherche

        Returns:
            Liste de dictionnaires contenant les informations produits
        """
        if not self.driver:
            self.start_driver()

        products = []

        try:
            # Construire l'URL de recherche
            search_url = f"{self.SEARCH_URL}?search={query.replace(' ', '+')}"
            logger.info(f"Recherche de '{query}' sur {search_url}")

            self.driver.get(search_url)

            # Attendre que les résultats se chargent
            time.sleep(3)  # Temps pour le chargement initial

            # Gérer le popup cookies si présent
            self._handle_cookie_popup()

            # DEBUG: Logger l'URL actuelle et le titre de la page
            logger.info(f"URL actuelle: {self.driver.current_url}")
            logger.info(f"Titre de la page: {self.driver.title}")

            # DEBUG: Chercher les classes CSS présentes sur la page
            try:
                body_html = self.driver.find_element(By.TAG_NAME, "body").get_attribute("innerHTML")
                # Logger les 500 premiers caractères du HTML
                logger.debug(f"HTML de la page (extrait): {body_html[:500]}")

                # Chercher différentes variantes possibles de sélecteurs
                possible_selectors = [
                    "product-item",
                    "product-card",
                    "product",
                    "item-product",
                    "search-result",
                    "result-item"
                ]

                for selector in possible_selectors:
                    elements = self.driver.find_elements(By.CLASS_NAME, selector)
                    if elements:
                        logger.info(f"✓ Trouvé {len(elements)} éléments avec classe '{selector}'")
                    else:
                        logger.debug(f"✗ Aucun élément avec classe '{selector}'")

            except Exception as e:
                logger.error(f"Erreur lors du debug HTML: {e}")

            # Attendre les produits
            try:
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "product-item"))
                )
            except TimeoutException:
                logger.warning(f"Timeout en attendant les produits pour '{query}'")
                logger.warning(f"Le sélecteur 'product-item' n'existe pas sur la page")
                return products

            # Récupérer les produits
            product_elements = self.driver.find_elements(By.CLASS_NAME, "product-item")

            logger.info(f"Trouvé {len(product_elements)} produits pour '{query}'")

            for element in product_elements[:10]:  # Limiter à 10 produits
                try:
                    product_data = self._extract_product_data(element)
                    if product_data:
                        products.append(product_data)
                except Exception as e:
                    logger.error(f"Erreur lors de l'extraction d'un produit: {e}")
                    continue

        except Exception as e:
            logger.error(f"Erreur lors de la recherche de '{query}': {e}")

        return products

    def _handle_cookie_popup(self):
        """Gère le popup de cookies s'il apparaît"""
        try:
            # Chercher le bouton "Tout accepter" ou similaire
            accept_button = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.ID, "didomi-notice-agree-button"))
            )
            accept_button.click()
            logger.info("Popup cookies accepté")
            time.sleep(1)
        except (TimeoutException, NoSuchElementException):
            # Pas de popup, on continue
            pass
        except Exception as e:
            logger.warning(f"Erreur lors de la gestion du popup cookies: {e}")

    def _extract_product_data(self, element) -> Optional[Dict]:
        """
        Extrait les données d'un élément produit

        Args:
            element: WebElement Selenium représentant un produit

        Returns:
            Dictionnaire avec les données du produit ou None
        """
        try:
            # Nom du produit
            try:
                name_element = element.find_element(By.CLASS_NAME, "product-title")
                name = name_element.text.strip()
            except NoSuchElementException:
                name = None

            if not name:
                return None

            # Prix
            try:
                price_element = element.find_element(By.CLASS_NAME, "product-price")
                price_text = price_element.text.strip()
                # Nettoyer le prix: "3,99 €" -> 3.99
                price = self._parse_price(price_text)
            except NoSuchElementException:
                price = None

            # Disponibilité
            try:
                # Vérifier s'il y a un indicateur "rupture" ou "indisponible"
                out_of_stock = element.find_elements(By.CLASS_NAME, "out-of-stock")
                is_available = len(out_of_stock) == 0
            except:
                is_available = True  # Par défaut, on suppose disponible

            # URL du produit (optionnel)
            try:
                link_element = element.find_element(By.TAG_NAME, "a")
                product_url = link_element.get_attribute("href")
            except NoSuchElementException:
                product_url = None

            product_data = {
                'name': name,
                'price': price,
                'is_available': is_available,
                'url': product_url,
                'source': 'intermarche_scraper'
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
