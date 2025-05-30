# interface/__init__.py
"""
Interface package for MICR Reader
Interface utilisateur web avec Gradio pour les démonstrations
"""

from .gradio_interface import MICRGradioInterface

__all__ = [
    'MICRGradioInterface'
]
