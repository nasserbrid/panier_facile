"""
Scraper pour récupérer les produits Intermarché et créer un panier automatique
Utilise undetected-chromedriver pour contourner les protections anti-bot

Flow:
1. Cherche chaque ingrédient sur https://www.intermarche.com/recherche/{ingredient}
2. Extrait les produits de la page de résultats
3. Ajoute automatiquement les produits au panier
4. Retourne le lien du panier à l'utilisateur
"""

import logging
import time
import random
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote_plus
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)


class IntermarcheScraper:
    """
    Scraper pour Intermarché Drive
    Automatise la recherche de produits et l'ajout au panier
    """

    BASE_URL = "https://www.intermarche.com"
    SEARCH_URL = f"{BASE_URL}/recherche"
    CART_URL = f"{BASE_URL}/commandes/panier"

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
        """Démarre le driver undetected-chromedriver avec anti-détection"""
        try:
            options = uc.ChromeOptions()

            # Options essentielles pour Docker/serveur
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')

            # IMPORTANT: En headless, on utilise le nouveau mode headless qui est moins détectable
            if self.headless:
                options.add_argument('--headless=new')

            # Désactiver les images pour aller plus vite
            prefs = {
                'profile.managed_default_content_settings.images': 2,
                'profile.default_content_setting_values.notifications': 2,  # Bloquer notifications
            }
            options.add_experimental_option('prefs', prefs)

            # Désactiver l'automatisation visible
            options.add_argument('--disable-blink-features=AutomationControlled')

            # User agent aléatoire parmi des vrais navigateurs
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]
            options.add_argument(f'user-agent={random.choice(user_agents)}')

            # Créer le driver avec undetected-chromedriver
            self.driver = uc.Chrome(
                options=options,
                version_main=None,  # Auto-détecte la version de Chrome
                use_subprocess=True,  # Meilleure compatibilité
            )

            # Timeout et configuration
            self.driver.set_page_load_timeout(30)  # Augmenter le timeout pour les pages lentes

            # Masquer les propriétés webdriver
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['fr-FR', 'fr', 'en-US', 'en']
                    });
                '''
            })

            logger.info("✅ Driver undetected-chromedriver démarré avec succès (anti-bot activé)")

        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage du driver: {e}")
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
        Recherche un produit sur Intermarché via /recherche/{ingredient}

        Args:
            query: Terme de recherche (nom de l'ingrédient)

        Returns:
            Liste de dictionnaires contenant les informations produits
        """
        if not self.driver:
            self.start_driver()

        products = []

        try:
            # URL de recherche: https://www.intermarche.com/recherche/{query}
            # Encoder l'URL correctement (espaces -> %20)
            encoded_query = query.replace(' ', '%20')
            search_url = f"{self.SEARCH_URL}/{encoded_query}"
            logger.info(f"🔍 Recherche de '{query}' sur {search_url}")

            self.driver.get(search_url)

            # Attendre de façon aléatoire pour simuler un comportement humain
            random_wait = random.uniform(2, 4)
            logger.info(f"⏳ Attente de {random_wait:.1f}s pour simuler un comportement humain")
            time.sleep(random_wait)

            # Gérer le popup cookies si présent (première visite)
            self._handle_cookie_popup()

            # Attente supplémentaire après le cookie popup
            time.sleep(random.uniform(1, 2))

            # Logger l'URL actuelle pour vérifier les redirections
            logger.info(f"URL actuelle: {self.driver.current_url}")
            logger.info(f"Titre de la page: {self.driver.title}")

            # DEBUG: Analyser la structure de la page
            try:
                # Screenshot pour debug
                screenshot_path = f"/tmp/intermarche_search_{query[:20].replace('/', '_')}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"📸 Screenshot sauvegardé: {screenshot_path}")

                # Extraire le HTML pour analyse
                body_html = self.driver.find_element(By.TAG_NAME, "body").get_attribute("innerHTML")
                logger.info(f"HTML de la page (premiers 1000 chars): {body_html[:1000]}")

                # Tester différents sélecteurs possibles
                possible_selectors = [
                    "product-item",
                    "product-card",
                    "ProductCard",
                    "product",
                    "item-product",
                    "search-result",
                    "result-item",
                    "product-list-item"
                ]

                logger.info("🔍 Test des sélecteurs CSS:")
                for selector in possible_selectors:
                    elements = self.driver.find_elements(By.CLASS_NAME, selector)
                    if elements:
                        logger.info(f"  ✅ Trouvé {len(elements)} éléments avec classe '{selector}'")
                    else:
                        logger.info(f"  ❌ Aucun élément avec classe '{selector}'")

            except Exception as e:
                logger.error(f"Erreur lors du debug HTML: {e}")

            # Attendre les produits (on testera différents sélecteurs)
            product_elements = []

            # Essayer de trouver les produits avec différents sélecteurs
            for selector in possible_selectors:
                try:
                    WebDriverWait(self.driver, self.timeout).until(
                        EC.presence_of_element_located((By.CLASS_NAME, selector))
                    )
                    product_elements = self.driver.find_elements(By.CLASS_NAME, selector)
                    if product_elements:
                        logger.info(f"✅ Utilisation du sélecteur '{selector}' - {len(product_elements)} produits trouvés")
                        break
                except TimeoutException:
                    continue

            if not product_elements:
                logger.warning(f"❌ Aucun produit trouvé pour '{query}' - aucun sélecteur n'a fonctionné")
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

    def add_product_to_cart(self, product_element) -> bool:
        """
        Ajoute un produit au panier en cliquant sur le bouton d'ajout

        Args:
            product_element: WebElement représentant le produit

        Returns:
            True si l'ajout a réussi, False sinon
        """
        try:
            # Chercher le bouton d'ajout au panier dans l'élément produit
            # Boutons possibles: "Ajouter", icône panier, bouton avec quantité, etc.
            add_button = None

            # Essayer différents sélecteurs pour le bouton d'ajout
            button_selectors = [
                (By.CLASS_NAME, "add-to-cart"),
                (By.CLASS_NAME, "addToCart"),
                (By.CLASS_NAME, "btn-add"),
                (By.XPATH, ".//button[contains(text(), 'Ajouter')]"),
                (By.XPATH, ".//button[contains(@class, 'cart')]"),
            ]

            for by, selector in button_selectors:
                try:
                    add_button = product_element.find_element(by, selector)
                    if add_button and add_button.is_displayed():
                        break
                except NoSuchElementException:
                    continue

            if not add_button:
                logger.warning("Bouton d'ajout au panier non trouvé pour ce produit")
                return False

            # Scroller vers l'élément pour s'assurer qu'il est visible
            self.driver.execute_script("arguments[0].scrollIntoView(true);", add_button)
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
