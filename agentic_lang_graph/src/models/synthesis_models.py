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
from ..agents.tech_analyzer_agent import AnalyzedContent


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
    
    # Métadonnées
    date: datetime
    title: str
    subtitle: str
    target_audience: str
    
    # Contenu principal
    executive_summary: str
    top_articles: List[ArticleSynthesis]
    key_insights: List[str]
    technical_trends: List[TechnicalTrend]
    recommendations: List[ActionableRecommendation]
    
    # Statistiques
    total_articles_analyzed: int
    articles_recommended: int
    average_quality_score: float
    
    # Ressources
    all_article_links: List[Dict[str, str]]  # {"title": "", "url": "", "source": ""}
    suggested_reading: List[str]
    
    # Format final
    markdown_content: Optional[str] = None
    word_count: int = 0
    estimated_read_time: int = 0  # minutes
    
    # Métadonnées de génération
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


# Templates de prompts pour la synthèse
SYNTHESIS_PROMPTS = {
    "executive_summary": """Tu es un expert technique senior qui rédige un résumé exécutif pour des ingénieurs expérimentés.

CONTEXTE: Digest quotidien de veille technologique GenAI/LLM/Agentic
AUDIENCE: {target_audience}
ARTICLES ANALYSÉS: {articles_count}

ARTICLES PRINCIPAUX:
{articles_overview}

CONSIGNE: Rédige un résumé exécutif de 100-150 mots qui:
1. Identifie les tendances principales observées aujourd'hui
2. Souligne les innovations les plus significatives
3. Met en perspective l'impact pour les équipes techniques
4. Adopte un ton professionnel et informatif

Le résumé doit capturer l'essentiel pour un lecteur expert qui veut comprendre rapidement les développements du jour.""",

    "article_synthesis": """Tu es un expert technique qui synthétise des articles pour des ingénieurs seniors.

ARTICLE À SYNTHÉTISER:
Titre: {title}
Source: {source}
Catégorie: {category}
Score d'analyse: {score}
Insights clés: {insights}
Contenu: {content}

CONSIGNE: Crée une synthèse structurée avec:

1. TITRE RAFFINÉ (concis et accrocheur)
2. RÉSUMÉ EXÉCUTIF (2-3 phrases maximum)
3. POINTS CLÉS (3-5 takeaways concrets)
4. ASPECTS TECHNIQUES (éléments d'implémentation/architecture)
5. NIVEAU DE COMPLEXITÉ (intermediate/advanced/expert)
6. INNOVATION (incremental/significant/breakthrough)

Format JSON attendu:
{{
    "title_refined": "...",
    "executive_summary": "...",
    "key_takeaways": ["...", "..."],
    "technical_highlights": ["...", "..."],
    "complexity_level": "...",
    "innovation_level": "..."
}}""",

    "insights_extraction": """Tu es un expert en veille technologique qui identifie les insights transversaux.

ARTICLES ANALYSÉS:
{articles_summaries}

CONSIGNE: Identifie 3-5 insights clés qui émergent de l'analyse croisée de ces articles.

Critères pour un bon insight:
- Transversal (identifiable dans plusieurs articles)
- Actionnable (peut influencer des décisions techniques)
- Significatif (impact réel sur l'industrie/pratiques)
- Concret (évite les généralités)

Format: Liste de phrases courtes et percutantes (15-25 mots max par insight)

Exemple:
- "L'architecture multi-agent devient mainstream avec des patterns standardisés émergents"
- "L'optimisation des LLM se concentre sur l'efficacité en production vs la performance pure"

Retourne uniquement la liste des insights, un par ligne.""",

    "recommendations": """Tu es un tech lead expérimenté qui transforme la veille en recommandations actionables.

ARTICLES ET INSIGHTS:
{content_summary}

AUDIENCE: {target_audience}

CONSIGNE: Génère 3-4 recommandations actionables basées sur cette veille.

Chaque recommandation doit inclure:
1. TITRE (court et clair)
2. DESCRIPTION (pourquoi c'est important)
3. ACTIONS CONCRÈTES (2-4 étapes spécifiques)
4. CATÉGORIE (learning/implementation/investigation/monitoring)
5. PRIORITÉ (high/medium/low)
6. EFFORT ESTIMÉ (< 1h / 1-4h / 1-2d / > 1w)

Format JSON attendu:
{{
    "recommendations": [
        {{
            "title": "...",
            "description": "...",
            "action_items": ["...", "..."],
            "category": "...",
            "priority": "...",
            "time_investment": "..."
        }}
    ]
}}"""
}
