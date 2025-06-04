"""
Modèles de données pour l'Agent Analyseur.

Ce module définit les structures de données utilisées par l'Agent Analyseur
pour évaluer et scorer les contenus collectés.
"""
from typing import List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Import des modèles de base
from ..connectors import RawContent


class DifficultyLevel(Enum):
    """Niveaux de difficulté des contenus."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate" 
    EXPERT = "expert"


class ExpertLevel(Enum):
    """Niveaux d'expertise du profil."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


@dataclass
class ExpertProfile:
    """Profil de l'expert pour personnaliser l'analyse."""
    level: ExpertLevel = ExpertLevel.INTERMEDIATE
    interests: List[str] = field(default_factory=lambda: [
        "LangGraph", "LangChain", "Multi-agent", "RAG", "GenAI", "LLM"
    ])
    avoid_topics: List[str] = field(default_factory=lambda: [
        "basic tutorials", "introduction to programming", "hello world"
    ])
    preferred_content_types: List[str] = field(default_factory=lambda: [
        "technical implementation", "case studies", "best practices", "architecture"
    ])


@dataclass
class ContentAnalysis:
    """Résultat de l'analyse d'un contenu par le LLM."""
    relevance_score: float          # 0-10
    difficulty_level: DifficultyLevel
    main_topics: List[str]          # Sujets principaux extraits  
    key_insights: str               # Résumé des insights clés
    practical_value: float          # 0-10 (théorique vs pratique)
    reasons: List[str]              # Raisons du score
    recommended: bool               # Recommandé pour le profil expert
    
    # Attributs ajoutés pour compatibilité avec le synthétiseur
    category: str = "unknown"        # "research", "tutorial", "news"
    expertise_level: str = "intermediate"  # Alias pour difficulty_level
    
    def __post_init__(self):
        """Post-processing après initialisation."""
        # Synchronisation expertise_level avec difficulty_level
        if hasattr(self.difficulty_level, 'value'):
            self.expertise_level = self.difficulty_level.value
        else:
            self.expertise_level = str(self.difficulty_level)
        
        # Détermination de la catégorie par défaut si non spécifiée
        if self.category == "unknown":
            # Heuristique simple basée sur les topics
            topics_lower = [topic.lower() for topic in self.main_topics]
            if any(word in topics_lower for word in ['research', 'paper', 'study', 'analysis']):
                self.category = "research"
            elif any(word in topics_lower for word in ['tutorial', 'guide', 'how-to', 'implementation']):
                self.category = "tutorial"
            else:
                self.category = "news"
    

@dataclass 
class AnalyzedContent:
    """Contenu enrichi avec l'analyse intelligence."""
    raw_content: RawContent
    analysis: ContentAnalysis
    analyzed_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_recommended(self) -> bool:
        """Indique si le contenu est recommandé."""
        return self.analysis.recommended
    
    @property 
    def score(self) -> float:
        """Score de pertinence (alias)."""
        return self.analysis.relevance_score
