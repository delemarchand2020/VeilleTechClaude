"""
Modules de modèles de données pour le système de veille.

Ce package contient tous les modèles de données utilisés par les différents agents:
- analysis_models: Modèles pour l'Agent Analyseur
- synthesis_models: Modèles pour l'Agent Synthétiseur  
"""

# Export des modèles d'analyse
from .analysis_models import (
    DifficultyLevel,
    ExpertLevel, 
    ExpertProfile,
    ContentAnalysis,
    AnalyzedContent
)

# Export des modèles de synthèse
from .synthesis_models import (
    SynthesisStage,
    ReportSection,
    SynthesisState,
    ArticleSynthesis,
    ActionableRecommendation,
    TechnicalTrend,
    DailyDigest,
    DEFAULT_SYNTHESIS_CONFIG
)

__all__ = [
    # Modèles d'analyse
    "DifficultyLevel",
    "ExpertLevel",
    "ExpertProfile", 
    "ContentAnalysis",
    "AnalyzedContent",
    # Modèles de synthèse
    "SynthesisStage",
    "ReportSection",
    "SynthesisState",
    "ArticleSynthesis",
    "ActionableRecommendation",
    "TechnicalTrend",
    "DailyDigest",
    "DEFAULT_SYNTHESIS_CONFIG"
]
