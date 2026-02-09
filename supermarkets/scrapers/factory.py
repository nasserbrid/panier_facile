"""Factory pour instancier les scrapers par nom d'enseigne."""

from .aldi import AldiScraper
from .leclerc import LeclercScraper

_SCRAPERS = {
    'leclerc': LeclercScraper,
    'aldi': AldiScraper,
}


class ScraperFactory:

    @staticmethod
    def get(name: str, **kwargs):
        """Retourne une instance du scraper pour l'enseigne donnée.

        Usage:
            with ScraperFactory.get('leclerc') as scraper:
                results = scraper.search('lait')
        """
        key = name.lower()
        cls = _SCRAPERS.get(key)
        if cls is None:
            raise ValueError(f"Scraper inconnu: '{name}'. "
                             f"Disponibles: {list(_SCRAPERS.keys())}")
        return cls(**kwargs)

    @staticmethod
    def available() -> list[str]:
        return list(_SCRAPERS.keys())
