"""
Module des connecteurs pour la collecte de contenu.

Ce module expose tous les connecteurs disponibles pour collecter
du contenu depuis différentes sources.

SOLUTION APPLIQUÉE: Utilise ArxivConnectorUnlimited qui fonctionne.
"""

from .base_connector import BaseConnector, RawContent
from .medium_connector import MediumConnector

# SOLUTION: Utiliser ArxivConnectorUnlimited qui fonctionne
from .arxiv_unlimited import ArxivConnectorUnlimited as ArxivConnector

__all__ = [
    'BaseConnector',
    'RawContent', 
    'MediumConnector',
    'ArxivConnector'
]
