"""
Modèles pour les supermarchés.

Exporte les modèles ProductMatch pour le cache des prix
et le modèle PriceComparison pour les comparaisons.
"""
from .leclerc import LeclercProductMatch
from .lidl import LidlProductMatch
from .comparison import PriceComparison

__all__ = [
    'LeclercProductMatch',
    'LidlProductMatch',
    'PriceComparison',
]
