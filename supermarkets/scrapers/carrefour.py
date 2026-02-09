"""
Scraper Carrefour - requêtes HTTP avec curl_cffi + parsing BeautifulSoup.

Carrefour est SSR (Server-Side Rendered) : les produits sont dans le HTML,
pas besoin d'un navigateur complet. curl_cffi imite le TLS fingerprint
de Chrome pour contourner la détection DataDome.
"""

import logging
import random
import re
import time
from typing import Dict, List, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

logger = logging.getLogger(__name__)

BASE_URL = "https://www.carrefour.fr"
SEARCH_URL = "https://www.carrefour.fr/s"

# User-agents Chrome récents
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


def _random_delay(min_ms: int = 800, max_ms: int = 2000) -> None:
    time.sleep(random.randint(min_ms, max_ms) / 1000)


class CarrefourScraper:
    """Scraper Carrefour basé sur curl_cffi (HTTP) au lieu de Playwright."""

    def __init__(self, **kwargs):
        # kwargs acceptés pour compatibilité avec ScraperFactory (headless, timeout)
        self.session: Optional[curl_requests.Session] = None

    def __enter__(self):
        self.session = curl_requests.Session(
            impersonate="chrome131",
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;"
                          "q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
                "Cache-Control": "no-cache",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        # Établir la session (cookies DataDome) en visitant la homepage
        try:
            resp = self.session.get(BASE_URL, timeout=15)
            logger.info(f"[Carrefour] Session établie (status {resp.status_code})")
            _random_delay(1000, 2000)
        except Exception as e:
            logger.warning(f"[Carrefour] Erreur session initiale: {e}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()
            self.session = None

    def search(self, query: str) -> List[Dict]:
        """Recherche un produit sur carrefour.fr et retourne les résultats."""
        if not self.session:
            logger.error("[Carrefour] Session non initialisée")
            return []

        url = f"{SEARCH_URL}?q={quote_plus(query)}"
        logger.info(f"[Carrefour] Recherche: {query}")

        for attempt in range(2):
            try:
                _random_delay(500, 1500)
                resp = self.session.get(url, timeout=15)

                if resp.status_code != 200:
                    logger.warning(
                        f"[Carrefour] Status {resp.status_code} pour '{query}'"
                    )
                    if attempt == 0:
                        _random_delay(2000, 4000)
                        continue
                    return []

                html = resp.text

                # Vérifier si on est bloqué
                if self._is_blocked(html):
                    logger.warning(f"[Carrefour] Blocage détecté pour '{query}'")
                    if attempt == 0:
                        _random_delay(3000, 5000)
                        continue
                    return []

                products = self._parse_html(html)
                logger.info(
                    f"[Carrefour] {len(products)} produits trouvés pour '{query}'"
                )
                return products

            except Exception as e:
                logger.error(f"[Carrefour] Erreur recherche '{query}': {e}")
                if attempt == 0:
                    _random_delay(2000, 4000)
                    continue
                return []

        return []

    @staticmethod
    def _is_blocked(html: str) -> bool:
        lower = html.lower()
        indicators = [
            "datadome", "captcha", "robot", "accès refusé",
            "access denied", "please verify", "checking your browser",
        ]
        for ind in indicators:
            if ind in lower:
                logger.warning(f"[Carrefour] Indicateur blocage: '{ind}'")
                return True
        return False

    def _parse_html(self, html: str) -> List[Dict]:
        """Parse le HTML de la page de résultats Carrefour."""
        soup = BeautifulSoup(html, "html.parser")
        products = []

        # Sélecteur réel : <article class="product-list-card-plp-grid-new">
        cards = soup.select("article.product-list-card-plp-grid-new")

        if not cards:
            logger.warning("[Carrefour] Aucune carte produit dans le HTML")
            return products

        for card in cards[:10]:
            p = self._parse_card(card)
            if p:
                products.append(p)

        return products

    def _parse_card(self, card) -> Optional[Dict]:
        """Parse une carte produit BeautifulSoup."""
        try:
            # Nom : <h3 class="product-card-title__text">
            name_el = card.select_one("h3.product-card-title__text")
            if not name_el:
                return None
            name = name_el.get_text(strip=True)
            if not name:
                return None

            # Prix : <div data-testid="product-price__amount--main">
            price = None
            price_el = card.select_one('[data-testid="product-price__amount--main"]')
            if price_el:
                raw = price_el.get_text()
                cleaned = re.sub(r"\s+", "", raw)
                price = self._parse_price(cleaned)

            # URL : <a class="product-list-card-plp-grid-new__title-container">
            product_url = ""
            link = card.select_one(
                "a.product-list-card-plp-grid-new__title-container"
            )
            if link and link.get("href"):
                href = link["href"]
                product_url = href if href.startswith("http") else f"{BASE_URL}{href}"

            # Image : <img class="product-card-image-new__content">
            image_url = ""
            img = card.select_one("img.product-card-image-new__content")
            if img:
                image_url = img.get("src", "") or img.get("data-src", "")

            # Marque : <a class="c-link--tone-accent">
            brand = ""
            brand_el = card.select_one("a.c-link--tone-accent")
            if brand_el:
                brand = brand_el.get_text(strip=True)

            return {
                "product_name": name,
                "price": price,
                "product_url": product_url,
                "image_url": image_url,
                "brand": brand,
                "is_available": True,
            }
        except Exception as e:
            logger.debug(f"[Carrefour] Erreur parsing carte: {e}")
            return None

    @staticmethod
    def _parse_price(text: str) -> Optional[float]:
        if not text:
            return None
        try:
            cleaned = text.replace("€", "").replace(",", ".").strip()
            m = re.search(r"(\d+\.?\d*)", cleaned)
            return float(m.group(1)) if m else None
        except Exception:
            return None
