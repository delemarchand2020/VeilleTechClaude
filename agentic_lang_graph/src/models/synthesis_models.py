"""
Modèles de données pour l'Agent Synthétiseur.

Ce module définit les structures de données utilisées par l'Agent Synthétiseur
pour créer des digests quotidiens à partir des articles analysés.
"""
from typing import TypedDict, List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Import des modèles existants
from ..models.analysis_models import AnalyzedContent


class SynthesisStage(Enum):
    """Étapes du workflow de synthèse."""
    INITIAL = "initial"
    PREPARED = "prepared"
    SUMMARIZED = "summarized"
    INSIGHTS_EXTRACTED = "insights_extracted"
    RECOMMENDATIONS_CREATED = "recommendations_created"
    FORMATTED = "formatted"
    FINALIZED = "finalized"


class ReportSection(Enum):
    """Sections du rapport digest."""
    EXECUTIVE_SUMMARY = "executive_summary"
    TOP_ARTICLES = "top_articles"
    KEY_INSIGHTS = "key_insights"
    TECHNICAL_TRENDS = "technical_trends"
    RECOMMENDATIONS = "recommendations"
    RESOURCES = "resources"


class SynthesisState(TypedDict):
    """État du workflow de synthèse LangGraph."""
    
    # Configuration
    synthesis_config: Dict[str, Any]
    target_audience: str  # "senior_engineer", "tech_lead", "architect"
    
    # Données d'entrée (depuis Agent Analyseur)
    analyzed_articles: List[AnalyzedContent]
    
    # État du processus
    current_stage: SynthesisStage
    processed_sections: List[ReportSection]
    
    # Contenu généré par section
    executive_summary: Optional[str]
    articles_synthesis: List['ArticleSynthesis']
    key_insights: List[str]
    technical_trends: List[str]
    recommendations: List['ActionableRecommendation']
    
    # Rapport final
    final_digest: Optional['DailyDigest']
    
    # Métadonnées
    generation_time: float
    word_count: int
    errors: List[str]


@dataclass
class ArticleSynthesis:
    """Synthèse d'un article pour le digest."""
    
    # Article source
    original_article: AnalyzedContent
    
    # Synthèse générée
    title_refined: str
    executive_summary: str  # 2-3 phrases
    key_takeaways: List[str]  # 3-5 points clés
    technical_highlights: List[str]  # Aspects techniques importants
    
    # Évaluation pour le digest
    relevance_for_audience: float  # 0-1
    actionability_score: float  # 0-1
    innovation_level: str  # "incremental", "significant", "breakthrough"
    
    # Métadonnées
    estimated_read_time: int  # minutes
    complexity_level: str  # "intermediate", "advanced", "expert"


@dataclass
class ActionableRecommendation:
    """Recommandation actionnable basée sur les articles."""
    
    # Contenu de la recommandation
    title: str
    description: str
    action_items: List[str]
    
    # Contexte
    based_on_articles: List[str]  # URLs des articles sources
    category: str  # "learning", "implementation", "investigation", "monitoring"
    priority: str  # "high", "medium", "low"
    
    # Effort estimé
    time_investment: str  # "< 1h", "1-4h", "1-2d", "> 1w"
    complexity: str  # "beginner", "intermediate", "advanced"
    
    # Ressources
    suggested_next_steps: List[str]
    related_technologies: List[str]


@dataclass
class TechnicalTrend:
    """Tendance technique identifiée."""
    
    # Tendance
    name: str
    description: str
    significance: str  # "emerging", "growing", "mainstream", "declining"
    
    # Évidence
    supporting_articles: List[str]  # URLs
    key_indicators: List[str]
    
    # Impact
    potential_impact: str  # "low", "medium", "high", "transformative"
    timeline: str  # "immediate", "6-12 months", "1-2 years", "long-term"
    
    # Recommandations
    action_for_engineers: str
    technologies_to_watch: List[str]


@dataclass
class DailyDigest:
    """Digest quotidien complet."""
    
    # Métadonnées (obligatoires)
    date: datetime
    title: str
    subtitle: str
    target_audience: str
    
    # Contenu principal (obligatoires)
    executive_summary: str
    top_articles: List[ArticleSynthesis]
    key_insights: List[str]
    technical_trends: List[TechnicalTrend]
    recommendations: List[ActionableRecommendation]
    
    # Ressources (obligatoires)
    all_article_links: List[Dict[str, str]]  # {"title": "", "url": "", "source": ""}
    suggested_reading: List[str]
    
    # Statistiques (avec valeurs par défaut)
    total_articles_collected: int = 0  # Articles collectés au total
    total_articles_analyzed: int = 0   # Articles analysés par l'IA
    total_articles_selected: int = 0   # Articles sélectionnés pour le digest
    articles_recommended: int = 0      # Articles recommandés par l'analyseur
    average_quality_score: float = 0.0
    
    # Format final (avec valeurs par défaut)
    markdown_content: Optional[str] = None
    word_count: int = 0
    estimated_read_time: int = 0  # minutes
    
    # Métadonnées de génération (avec valeurs par défaut)
    generated_at: datetime = field(default_factory=datetime.now)
    generator_version: str = "1.0"
    llm_model_used: str = "gpt-4o"


# Configuration par défaut pour la synthèse
DEFAULT_SYNTHESIS_CONFIG = {
    "target_audience": "senior_engineer",
    "max_articles_in_digest": 3,
    "executive_summary_max_words": 150,
    "article_summary_max_words": 100,
    "max_insights": 5,
    "max_recommendations": 4,
    "include_technical_trends": True,
    "include_action_items": True,
    "tone": "professional",  # "casual", "professional", "academic"
    "technical_depth": "high",  # "low", "medium", "high"
    "focus_areas": [
        "implementation_details",
        "architectural_patterns", 
        "performance_optimization",
        "best_practices",
        "emerging_technologies"
    ]
}
