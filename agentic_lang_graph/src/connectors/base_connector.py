"""
Connecteur de base pour tous les collecteurs de contenu.

Ce module définit une interface commune pour tous les connecteurs de sources,
garantissant une approche cohérente pour la collecte de données.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from loguru import logger

@dataclass
class RawContent:
    """
    Structure de données pour le contenu brut collecté depuis une source.
    
    Cette classe standardise les données avant leur conversion en Article.
    Chaque connecteur retourne des objets RawContent qui seront ensuite
    transformés par l'Agent Collecteur.
    """
    title: str                          # Titre de l'article
    url: str                           # URL source
    source: str                        # Nom de la source (ex: "medium", "arxiv")
    content: str = ""                  # Contenu principal (si disponible)
    excerpt: str = ""                  # Résumé/extrait court
    published_date: Optional[datetime] = None  # Date de publication
    author: str = ""                   # Auteur
    tags: List[str] = None            # Tags/catégories
    raw_data: Dict[str, Any] = None   # Données brutes spécifiques à la source
    
    def __post_init__(self):
        """Initialise les listes vides si elles sont None"""
        if self.tags is None:
            self.tags = []
        if self.raw_data is None:
            self.raw_data = {}

class BaseConnector(ABC):
    """
    Classe abstraite définissant l'interface pour tous les connecteurs.
    
    Chaque source (Medium, ArXiv, GitHub) doit hériter de cette classe
    et implémenter les méthodes abstraites.
    """
    
    def __init__(self, source_name: str, keywords: List[str] = None):
        """
        Initialise le connecteur.
        
        Args:
            source_name: Nom identifiant la source (ex: "medium")
            keywords: Liste de mots-clés pour filtrer le contenu
        """
        self.source_name = source_name
        self.keywords = keywords or []
        self.logger = logger.bind(source=source_name)
    
    @abstractmethod
    async def collect(self, limit: int = 10) -> List[RawContent]:
        """
        Collecte le contenu depuis la source.
        
        Args:
            limit: Nombre maximum d'éléments à collecter
            
        Returns:
            Liste d'objets RawContent
            
        Raises:
            ConnectionError: Si la source n'est pas accessible
            ValueError: Si les paramètres sont invalides
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Vérifie si la source est accessible.
        
        Returns:
            True si la source répond correctement
        """
        pass
    
    def filter_by_keywords(self, contents: List[RawContent]) -> List[RawContent]:
        """
        Filtre le contenu basé sur les mots-clés configurés.
        
        Cette méthode est utilisée par tous les connecteurs pour appliquer
        un premier niveau de filtrage avant l'analyse par l'IA.
        
        Args:
            contents: Liste de contenus à filtrer
            
        Returns:
            Liste filtrée de contenus pertinents
        """
        if not self.keywords:
            return contents
        
        filtered = []
        keywords_lower = [kw.lower() for kw in self.keywords]
        
        for content in contents:
            # Combine title, excerpt et tags pour la recherche
            searchable_text = (
                f"{content.title} {content.excerpt} {' '.join(content.tags)}"
            ).lower()
            
            # Vérifie si au moins un mot-clé est présent
            if any(keyword in searchable_text for keyword in keywords_lower):
                filtered.append(content)
                self.logger.debug(f"✅ Contenu gardé: {content.title[:50]}...")
            else:
                self.logger.debug(f"❌ Contenu filtré: {content.title[:50]}...")
        
        self.logger.info(f"Filtrage: {len(contents)} → {len(filtered)} contenus")
        return filtered
    
    def validate_content(self, content: RawContent) -> bool:
        """
        Valide qu'un contenu est exploitable.
        
        Args:
            content: Contenu à valider
            
        Returns:
            True si le contenu est valide
        """
        if not content.title or not content.url:
            return False
        
        if len(content.title) < 10:  # Titre trop court
            return False
            
        return True
    
    def clean_and_validate(self, contents: List[RawContent]) -> List[RawContent]:
        """
        Nettoie et valide une liste de contenus.
        
        Args:
            contents: Contenus bruts à nettoyer
            
        Returns:
            Liste de contenus validés et nettoyés
        """
        valid_contents = []
        
        for content in contents:
            if self.validate_content(content):
                # Nettoyage basique
                content.title = content.title.strip()
                content.excerpt = content.excerpt.strip()
                content.author = content.author.strip()
                
                valid_contents.append(content)
            else:
                self.logger.warning(f"Contenu invalide ignoré: {content.url}")
        
        return valid_contents
