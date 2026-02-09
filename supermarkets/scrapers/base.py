"""
Base scraper avec Playwright + anti-détection.

Toute la logique commune (navigateur, cookies, debug)
est factorisée ici. Utilisé par les scrapers qui nécessitent
un navigateur complet (ex: Lidl avec rendu JS côté client).
"""

import logging
import os
import random
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from playwright.sync_api import Response, sync_playwright

logger = logging.getLogger(__name__)

DEBUG_DIR = "/tmp/scraper_debug"


def random_delay(min_ms: int = 500, max_ms: int = 1500) -> None:
    time.sleep(random.randint(min_ms, max_ms) / 1000)


class BaseScraper(ABC):
    """Classe abstraite pour les scrapers de supermarchés."""

    # À définir dans les sous-classes
    RETAILER_NAME: str = ""
    BASE_URL: str = ""
    SEARCH_URL: str = ""
    API_PATTERNS: List[str] = []

    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.found_products: List[Dict] = []
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._session_established = False

    def __enter__(self):
        self._start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close_browser()

    # ── Navigateur ──────────────────────────────────────────────

    def _start_browser(self):
        self.playwright = sync_playwright().start()

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
            args=chrome_args,
        )

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        ]

        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=random.choice(user_agents),
            locale='fr-FR',
            timezone_id='Europe/Paris',
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                          'image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
                'Cache-Control': 'no-cache',
                'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", '
                             '"Not_A Brand";v="24"',
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

        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            delete navigator.__proto__.webdriver;
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const p = [
                        {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                        {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                        {name: 'Native Client', filename: 'internal-nacl-plugin'},
                    ];
                    p.item = i => p[i];
                    p.namedItem = n => p.find(x => x.name === n);
                    p.refresh = () => {};
                    return p;
                }
            });
            Object.defineProperty(navigator, 'languages', {get: () => ['fr-FR','fr','en-US','en']});
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            window.chrome = {runtime:{}, loadTimes:function(){}, csi:function(){}, app:{}};
            const oq = window.navigator.permissions.query;
            window.navigator.permissions.query = p =>
                p.name === 'notifications'
                    ? Promise.resolve({state: Notification.permission})
                    : oq(p);
            Object.defineProperty(screen, 'availWidth', {get: () => 1920});
            Object.defineProperty(screen, 'availHeight', {get: () => 1040});
        """)

        logger.info(f"Navigateur {self.RETAILER_NAME} démarré")

    def _close_browser(self):
        for obj in (self.page, self.context, self.browser):
            if obj:
                try:
                    obj.close()
                except Exception:
                    pass
        if self.playwright:
            try:
                self.playwright.stop()
            except Exception:
                pass
        logger.info(f"Navigateur {self.RETAILER_NAME} fermé")

    # ── Anti-bot / debug ────────────────────────────────────────

    def _is_blocked(self) -> bool:
        try:
            content = self.page.content().lower()
            indicators = [
                'datadome', 'captcha', 'robot', 'accès refusé',
                'access denied', 'please verify', 'checking your browser',
            ]
            for ind in indicators:
                if ind in content:
                    logger.warning(f"[{self.RETAILER_NAME}] Blocage détecté: '{ind}'")
                    return True
            return False
        except Exception:
            return False

    def _save_debug(self, query: str, reason: str = "no_products"):
        try:
            os.makedirs(DEBUG_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            tag = re.sub(r'[^\w\-]', '_', query)[:30]
            prefix = f"{DEBUG_DIR}/{self.RETAILER_NAME.lower()}_{reason}_{tag}_{ts}"

            self.page.screenshot(path=f"{prefix}.png")
            with open(f"{prefix}.html", 'w', encoding='utf-8') as f:
                f.write(self.page.content())

            logger.info(f"Debug sauvegardé: {prefix} | URL: {self.page.url}")
        except Exception as e:
            logger.warning(f"Erreur sauvegarde debug: {e}")

    # ── Popups communs ──────────────────────────────────────────

    def _accept_cookies(self):
        selectors = [
            '#didomi-notice-agree-button',
            'button[id*="accept"]',
            '#onetrust-accept-btn-handler',
            'button:has-text("Accepter")',
            'button:has-text("Tout accepter")',
        ]
        for sel in selectors:
            try:
                btn = self.page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    logger.info(f"[{self.RETAILER_NAME}] Cookies acceptés")
                    self.page.wait_for_timeout(1000)
                    return
            except Exception:
                continue

    def _dismiss_popups(self):
        selectors = [
            'button:has-text("Plus tard")',
            'button:has-text("Non merci")',
            'button:has-text("Fermer")',
            '[data-testid="close-modal"]',
            '[aria-label="Fermer"]',
            'button.close',
        ]
        for sel in selectors:
            try:
                btn = self.page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    logger.info(f"[{self.RETAILER_NAME}] Popup fermé")
                    self.page.wait_for_timeout(500)
                    return
            except Exception:
                continue

    # ── Session ─────────────────────────────────────────────────

    def _establish_session(self):
        if self._session_established:
            return

        logger.info(f"[{self.RETAILER_NAME}] Établissement session...")

        try:
            self.page.goto(self.BASE_URL, wait_until="domcontentloaded",
                           timeout=self.timeout)
            random_delay(1500, 2500)

            if self._is_blocked():
                logger.error(f"[{self.RETAILER_NAME}] Bloqué dès la homepage!")
                self._save_debug("homepage", "blocked")
                return

            self._accept_cookies()
            random_delay(800, 1200)

            self.page.evaluate("window.scrollTo(0, 300)")
            random_delay(500, 800)

            self._dismiss_popups()
            random_delay(500, 1000)

            self.page.evaluate("window.scrollTo(0, 0)")
            random_delay(400, 700)

            self._session_established = True
            logger.info(f"[{self.RETAILER_NAME}] Session établie - {self.page.url}")

        except Exception as e:
            logger.warning(f"[{self.RETAILER_NAME}] Erreur session: {e}")
            self._save_debug("session", "error")

    # ── Interception API ────────────────────────────────────────

    def _handle_response(self, response: Response):
        url = response.url
        if not any(re.search(p, url, re.IGNORECASE) for p in self.API_PATTERNS):
            return
        if response.status != 200:
            return
        try:
            if 'application/json' not in response.headers.get('content-type', ''):
                return
            data = response.json()
            # Log un échantillon de la structure pour debug
            if isinstance(data, dict):
                sample_keys = list(data.keys())[:10]
                logger.debug(f"[{self.RETAILER_NAME}] API keys: {sample_keys}")
                # Log le premier produit brut pour comprendre la structure des prix
                for key in ('products', 'results', 'hits', 'items', 'data'):
                    if key in data and isinstance(data[key], list) and data[key]:
                        first = data[key][0]
                        if isinstance(first, dict):
                            logger.info(f"[{self.RETAILER_NAME}] API sample "
                                        f"({key}[0] keys): {list(first.keys())[:15]}")
                        break
            products = self._extract_products_from_json(data)
            if products:
                self.found_products.extend(products)
                logger.info(f"[{self.RETAILER_NAME}] Intercepté {len(products)} "
                            f"produits via {url[:80]}")
        except Exception as e:
            logger.debug(f"[{self.RETAILER_NAME}] Erreur parsing réponse: {e}")

    # ── Parse prix ──────────────────────────────────────────────

    @staticmethod
    def _parse_price(text: str) -> Optional[float]:
        if not text:
            return None
        try:
            cleaned = text.replace('€', '').replace(',', '.').strip()
            m = re.search(r'(\d+\.?\d*)', cleaned)
            return float(m.group(1)) if m else None
        except Exception:
            return None

    # ── Interface publique ──────────────────────────────────────

    def search(self, query: str) -> List[Dict]:
        """
        Recherche un produit et retourne les résultats.

        Chaque résultat est un dict avec les clés unifiées :
            product_name, price, product_url, image_url, brand, is_available
        """
        self.found_products = []
        self._establish_session()

        self.page.on("response", self._handle_response)
        try:
            random_delay(800, 1500)
            logger.info(f"[{self.RETAILER_NAME}] Recherche: {query}")

            self._perform_search(query)

            self._accept_cookies()
            self.page.wait_for_timeout(random.randint(2500, 4000))

            # Scroll humain
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
            random_delay(500, 1000)
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            self.page.wait_for_timeout(random.randint(1500, 2500))

            # Garder uniquement les produits avec un prix valide
            priced = [p for p in self.found_products if p.get('price')]

            # Si l'API n'a pas retourné assez de produits avec prix,
            # basculer sur le parsing DOM (qui affiche les vrais résultats)
            if len(priced) < 3:
                if self.found_products:
                    logger.info(f"[{self.RETAILER_NAME}] API: {len(priced)} produits "
                                f"avec prix sur {len(self.found_products)}, fallback DOM...")
                else:
                    logger.info(f"[{self.RETAILER_NAME}] Pas de données API, fallback DOM...")
                html_products = self._fallback_html_parsing()
                html_priced = [p for p in html_products if p.get('price')]
                if html_priced:
                    self.found_products = html_priced
                elif priced:
                    self.found_products = priced
                else:
                    self.found_products = html_products
            else:
                self.found_products = priced

            if not self.found_products:
                reason = "blocked" if self._is_blocked() else "no_products"
                self._save_debug(query, reason)

            logger.info(f"[{self.RETAILER_NAME}] {len(self.found_products)} produits "
                        f"trouvés pour '{query}'")
            return self.found_products

        except Exception as e:
            logger.error(f"[{self.RETAILER_NAME}] Erreur recherche '{query}': {e}")
            return []
        finally:
            self.page.remove_listener("response", self._handle_response)

    # ── Méthodes abstraites ─────────────────────────────────────

    @abstractmethod
    def _perform_search(self, query: str) -> None:
        """Exécute la recherche (navigation URL ou barre de recherche)."""

    @abstractmethod
    def _extract_products_from_json(self, data: dict) -> List[Dict]:
        """Extrait les produits d'une réponse API JSON."""

    @abstractmethod
    def _fallback_html_parsing(self) -> List[Dict]:
        """Parse le HTML quand l'interception API échoue."""
