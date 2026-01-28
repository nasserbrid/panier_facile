"""
Modèles pour les supermarchés.

Exporte les modèles ProductMatch pour le cache des prix
et le modèle PriceComparison pour les comparaisons.
"""
from .carrefour import CarrefourProductMatch
from .auchan import AuchanProductMatch
from .comparison import PriceComparison

__all__ = [
    'CarrefourProductMatch',
    'AuchanProductMatch',
    'PriceComparison',
]
