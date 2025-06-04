"""
Gestionnaire de prompts centralisé pour le système de veille.

Ce module fournit un loader pour charger et formatter les prompts
depuis les fichiers externes avec support du templating.
"""
import os
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger


class PromptLoader:
    """
    Gestionnaire centralisé pour charger et formatter les prompts.
    
    Fonctionnalités:
    - Chargement depuis fichiers .md
    - Templating avec variables
    - Cache pour performance
    - Validation des prompts
    """
    
    def __init__(self, prompts_dir: str = "prompts"):
        """
        Initialise le loader de prompts.
        
        Args:
            prompts_dir: Dossier racine des prompts
        """
        self.prompts_dir = Path(prompts_dir)
        self.cache: Dict[str, str] = {}
        self.logger = logger.bind(component="PromptLoader")
        
        if not self.prompts_dir.exists():
            raise ValueError(f"Dossier prompts introuvable: {self.prompts_dir}")
    
    def load_prompt(self, prompt_path: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        Charge et formate un prompt depuis un fichier.
        
        Args:
            prompt_path: Chemin relatif vers le fichier prompt (ex: "analyzer/system.md")
            variables: Variables pour le templating
            
        Returns:
            Prompt formaté prêt à utiliser
        """
        # Normalization du chemin
        if not prompt_path.endswith('.md'):
            prompt_path += '.md'
        
        # Chemin complet
        full_path = self.prompts_dir / prompt_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"Prompt introuvable: {full_path}")
        
        # Cache key
        cache_key = str(full_path)
        
        # Chargement depuis cache ou fichier
        if cache_key not in self.cache:
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    self.cache[cache_key] = content
                    self.logger.debug(f"📝 Prompt chargé: {prompt_path}")
            except Exception as e:
                self.logger.error(f"❌ Erreur chargement prompt {prompt_path}: {e}")
                raise
        
        prompt_template = self.cache[cache_key]
        
        # Templating si variables fournies
        if variables:
            try:
                formatted_prompt = prompt_template.format(**variables)
                return formatted_prompt
            except KeyError as e:
                self.logger.error(f"❌ Variable manquante dans prompt {prompt_path}: {e}")
                raise ValueError(f"Variable manquante: {e}")
        
        return prompt_template
    
    def load_analyzer_prompts(self) -> Dict[str, str]:
        """
        Charge tous les prompts pour l'analyzer.
        
        Returns:
            Dictionnaire des prompts analyzer
        """
        return {
            "system": self.load_prompt("analyzer/system"),
            "content_analysis": self.load_prompt("analyzer/content_analysis")
        }
    
    def load_synthesizer_prompts(self) -> Dict[str, str]:
        """
        Charge tous les prompts pour le synthesizer.
        
        Returns:
            Dictionnaire des prompts synthesizer
        """
        return {
            "executive_summary": self.load_prompt("synthesizer/executive_summary"),
            "article_synthesis": self.load_prompt("synthesizer/article_synthesis"),
            "insights_extraction": self.load_prompt("synthesizer/insights_extraction"),
            "recommendations": self.load_prompt("synthesizer/recommendations")
        }
    
    def clear_cache(self):
        """Vide le cache des prompts."""
        self.cache.clear()
        self.logger.info("🗑️ Cache prompts vidé")
    
    def reload_prompt(self, prompt_path: str):
        """
        Force le rechargement d'un prompt spécifique.
        
        Args:
            prompt_path: Chemin vers le prompt à recharger
        """
        full_path = self.prompts_dir / prompt_path
        cache_key = str(full_path)
        
        if cache_key in self.cache:
            del self.cache[cache_key]
            self.logger.info(f"🔄 Prompt rechargé: {prompt_path}")
    
    def list_available_prompts(self) -> Dict[str, list]:
        """
        Liste tous les prompts disponibles par catégorie.
        
        Returns:
            Dictionnaire avec les prompts par catégorie
        """
        prompts_by_category = {}
        
        for category_dir in self.prompts_dir.iterdir():
            if category_dir.is_dir():
                category_name = category_dir.name
                prompts = []
                
                for prompt_file in category_dir.glob("*.md"):
                    prompts.append(prompt_file.stem)
                
                prompts_by_category[category_name] = prompts
        
        return prompts_by_category
    
    def validate_prompts(self) -> Dict[str, list]:
        """
        Valide tous les prompts et retourne les erreurs trouvées.
        
        Returns:
            Dictionnaire des erreurs par prompt
        """
        errors = {}
        
        for category_dir in self.prompts_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            for prompt_file in category_dir.glob("*.md"):
                prompt_path = f"{category_dir.name}/{prompt_file.stem}"
                
                try:
                    content = self.load_prompt(prompt_path)
                    
                    # Validations basiques
                    if not content.strip():
                        errors[prompt_path] = ["Prompt vide"]
                    elif len(content) < 50:
                        errors[prompt_path] = ["Prompt trop court (< 50 caractères)"]
                    
                except Exception as e:
                    errors[prompt_path] = [str(e)]
        
        return errors


# Instance globale pour utilisation simple
_global_loader = None

def get_prompt_loader(prompts_dir: str = "prompts") -> PromptLoader:
    """
    Retourne l'instance globale du PromptLoader.
    
    Args:
        prompts_dir: Dossier racine des prompts
        
    Returns:
        Instance PromptLoader
    """
    global _global_loader
    
    if _global_loader is None:
        _global_loader = PromptLoader(prompts_dir)
    
    return _global_loader


# Fonctions de convenience
def load_prompt(prompt_path: str, variables: Optional[Dict[str, Any]] = None) -> str:
    """
    Fonction de convenience pour charger un prompt.
    
    Args:
        prompt_path: Chemin vers le prompt
        variables: Variables pour templating
        
    Returns:
        Prompt formaté
    """
    loader = get_prompt_loader()
    return loader.load_prompt(prompt_path, variables)


def load_analyzer_prompts() -> Dict[str, str]:
    """Charge tous les prompts analyzer."""
    loader = get_prompt_loader()
    return loader.load_analyzer_prompts()


def load_synthesizer_prompts() -> Dict[str, str]:
    """Charge tous les prompts synthesizer."""
    loader = get_prompt_loader()
    return loader.load_synthesizer_prompts()
