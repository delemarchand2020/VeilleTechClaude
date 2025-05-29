"""
Module des connecteurs pour la collecte de contenu.

Ce module expose tous les connecteurs disponibles pour collecter
du contenu depuis différentes sources.
"""

from .base_connector import BaseConnector, RawContent
from .medium_connector import MediumConnector
from .arxiv_connector import ArxivConnector

__all__ = [
    'BaseConnector',
    'RawContent', 
    'MediumConnector',
    'ArxivConnector'
]
