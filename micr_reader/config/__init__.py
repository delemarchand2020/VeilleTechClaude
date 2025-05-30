# config/__init__.py
"""
Package de configuration pour MICR Reader
"""

from .prompts import get_micr_prompt, MICRPrompts

__all__ = ['get_micr_prompt', 'MICRPrompts']
