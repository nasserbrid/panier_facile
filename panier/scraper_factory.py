"""
Factory Pattern pour créer dynamiquement des scrapers Drive.

Permet de gérer facilement plusieurs enseignes (Carrefour, Intermarché, Leclerc, Lidl, Super U, etc.)
sans dupliquer le code.

Usage:
    scraper = DriveScraperFactory.create_scraper('carrefour')
    products = scraper.search_product('tomates')
"""

import logging
from typing import Dict, Type, Optional
from .base_scraper import BaseDriveScraper
from .carrefour_scraper import CarrefourScraper
from .intermarche_scraper import IntermarcheScraper
from .auchan_scraper import AuchanScraper

logger = logging.getLogger(__name__)


class DriveScraperFactory:
    """
    Factory pour créer des instances de scrapers Drive.

    Design Pattern: Factory Method
    - Encapsule la logique de création des scrapers
    - Permet d'ajouter facilement de nouvelles enseignes
    - Centralise la configuration des scrapers
    """

    # Registre des scrapers disponibles
    # Format: {'retailer_id': ScraperClass}
    _scrapers: Dict[str, Type[BaseDriveScraper]] = {
        'carrefour': CarrefourScraper,
        'intermarche': IntermarcheScraper,
        'auchan': AuchanScraper,
        # Prêt pour les futures enseignes:
        # 'leclerc': LeclercScraper,
        # 'lidl': LidlScraper,
        # 'superu': SuperUScraper,
        # 'cora': CoraScraper,
    }

    # Métadonnées des enseignes (pour l'UI)
    _retailer_metadata: Dict[str, dict] = {
        'carrefour': {
            'name': 'Carrefour',
            'display_name': 'Carrefour Drive',
            'icon': 'fa-shopping-cart',
            'color': 'primary',
            'status': 'blocked',  # Bloqué par anti-bot
            'description': 'Actuellement bloqué par anti-bot',
        },
        'intermarche': {
            'name': 'Intermarché',
            'display_name': 'Intermarché Drive',
            'icon': 'fa-store',
            'color': 'success',
            'status': 'blocked',  # Bloqué par DataDome
            'description': 'Actuellement bloqué par anti-bot DataDome',
        },
        'auchan': {
            'name': 'Auchan',
            'display_name': 'Auchan Drive',
            'icon': 'fa-shopping-basket',
            'color': 'info',
            'status': 'active',
            'description': 'Recherche automatique de vos produits',
        },
        # Prêt pour les futures enseignes:
        # 'leclerc': {
        #     'name': 'Leclerc',
        #     'display_name': 'E.Leclerc Drive',
        #     'icon': 'fa-shopping-basket',
        #     'color': 'info',
        #     'status': 'coming_soon',
        #     'description': 'Bientôt disponible',
        # },
    }

    @classmethod
    def create_scraper(
        cls,
        retailer: str,
        headless: bool = True,
        timeout: int = 20000
    ) -> Optional[BaseDriveScraper]:
        """
        Crée une instance de scraper pour une enseigne donnée.

        Args:
            retailer: Identifiant de l'enseigne ('carrefour', 'intermarche', etc.)
            headless: Si True, le navigateur s'exécute sans interface graphique
            timeout: Temps d'attente max pour les éléments (millisecondes)

        Returns:
            Instance du scraper ou None si l'enseigne n'existe pas

        Raises:
            ValueError: Si l'enseigne n'est pas supportée
        """
        retailer = retailer.lower()

        if retailer not in cls._scrapers:
            available = ', '.join(cls._scrapers.keys())
            raise ValueError(
                f"Enseigne '{retailer}' non supportée. "
                f"Enseignes disponibles: {available}"
            )

        scraper_class = cls._scrapers[retailer]
        logger.info(f"🏭 Factory: Création du scraper {scraper_class.RETAILER_NAME}")

        return scraper_class(headless=headless, timeout=timeout)

    @classmethod
    def get_available_retailers(cls, include_inactive: bool = False) -> Dict[str, dict]:
        """
        Retourne la liste des enseignes disponibles avec leurs métadonnées.

        Args:
            include_inactive: Si True, inclut les enseignes inactives/bloquées

        Returns:
            Dictionnaire {retailer_id: metadata}
        """
        if include_inactive:
            return cls._retailer_metadata.copy()

        # Filtrer uniquement les enseignes actives
        return {
            retailer_id: metadata
            for retailer_id, metadata in cls._retailer_metadata.items()
            if metadata.get('status') == 'active'
        }

    @classmethod
    def is_retailer_available(cls, retailer: str) -> bool:
        """
        Vérifie si une enseigne est disponible et active.

        Args:
            retailer: Identifiant de l'enseigne

        Returns:
            True si l'enseigne est active, False sinon
        """
        retailer = retailer.lower()
        if retailer not in cls._retailer_metadata:
            return False

        return cls._retailer_metadata[retailer].get('status') == 'active'

    @classmethod
    def get_retailer_info(cls, retailer: str) -> Optional[dict]:
        """
        Récupère les métadonnées d'une enseigne.

        Args:
            retailer: Identifiant de l'enseigne

        Returns:
            Métadonnées de l'enseigne ou None si non trouvée
        """
        return cls._retailer_metadata.get(retailer.lower())

    @classmethod
    def register_scraper(
        cls,
        retailer_id: str,
        scraper_class: Type[BaseDriveScraper],
        metadata: dict
    ):
        """
        Enregistre un nouveau scraper dynamiquement.

        Utile pour les plugins ou extensions futures.

        Args:
            retailer_id: Identifiant unique de l'enseigne
            scraper_class: Classe du scraper (doit hériter de BaseDriveScraper)
            metadata: Métadonnées de l'enseigne (name, icon, color, etc.)
        """
        if not issubclass(scraper_class, BaseDriveScraper):
            raise ValueError(
                f"La classe {scraper_class.__name__} doit hériter de BaseDriveScraper"
            )

        cls._scrapers[retailer_id.lower()] = scraper_class
        cls._retailer_metadata[retailer_id.lower()] = metadata

        logger.info(f"✅ Nouveau scraper enregistré: {retailer_id} ({metadata.get('name')})")
