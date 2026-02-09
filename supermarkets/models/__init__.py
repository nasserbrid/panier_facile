"""
Modèles pour les supermarchés.

Exporte les modèles ProductMatch pour le cache des prix
et le modèle PriceComparison pour les comparaisons.
"""
from .leclerc import LeclercProductMatch
from .aldi import AldiProductMatch
from .comparison import PriceComparison

__all__ = [
    'LeclercProductMatch',
    'AldiProductMatch',
    'PriceComparison',
]
