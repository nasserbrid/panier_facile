"""
Scrapers pour les différentes enseignes de supermarchés.

Ce module fournit une factory pour créer le scraper approprié
selon l'enseigne demandée.
"""
from .base import BaseDriveScraper
from .carrefour import CarrefourDriveScraper
from .auchan import AuchanDriveScraper

__all__ = [
    'BaseDriveScraper',
    'CarrefourDriveScraper',
    'AuchanDriveScraper',
    'get_scraper',
]


def get_scraper(retailer: str, headless: bool = True):
    """
    Factory function pour obtenir le scraper approprié.

    Args:
        retailer: Nom de l'enseigne ('carrefour', 'auchan')
        headless: Mode sans interface graphique

    Returns:
        Instance du scraper approprié

    Raises:
        ValueError: Si l'enseigne n'est pas supportée
    """
    scrapers = {
        'carrefour': CarrefourDriveScraper,
        'auchan': AuchanDriveScraper,
    }

    retailer_lower = retailer.lower()
    if retailer_lower not in scrapers:
        raise ValueError(f"Enseigne '{retailer}' non supportée. "
                        f"Enseignes disponibles: {list(scrapers.keys())}")

    return scrapers[retailer_lower](headless=headless)
