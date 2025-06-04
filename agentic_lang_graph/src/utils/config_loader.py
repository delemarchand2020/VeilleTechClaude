"""
Gestionnaire de configuration centralisé pour le système de veille.

Ce module fournit un loader pour charger et valider la configuration
depuis les fichiers YAML avec support des profils et environnements.
"""
import os
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class CollectionConfig:
    """Configuration pour la collecte d'articles."""
    total_limit: int = 15
    source_limits: Dict[str, int] = field(default_factory=lambda: {"medium": 8, "arxiv": 8})
    keywords: List[str] = field(default_factory=lambda: ["AI", "GenAI", "LLM"])
    max_age_days: int = 30
    enabled_sources: List[str] = field(default_factory=lambda: ["medium", "arxiv"])


@dataclass
class AnalysisConfig:
    """Configuration pour l'analyse d'articles."""
    expert_level: str = "intermediate"
    interests: List[str] = field(default_factory=lambda: ["LangGraph", "Multi-agent"])
    avoid_topics: List[str] = field(default_factory=lambda: ["basic tutorials"])
    preferred_content_types: List[str] = field(default_factory=lambda: ["technical implementation"])
    batch_size: int = 3
    max_retries: int = 2
    recommendation_threshold: float = 7.0
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 500


@dataclass
class SynthesisConfig:
    """Configuration pour la synthèse."""
    target_audience: str = "senior_engineer"
    max_articles_in_digest: int = 3
    max_insights: int = 5
    max_recommendations: int = 4
    executive_summary_max_words: int = 150
    article_summary_max_words: int = 100
    tone: str = "professional"
    technical_depth: str = "high"
    include_technical_trends: bool = True
    include_action_items: bool = True
    focus_areas: List[str] = field(default_factory=lambda: ["implementation_details"])
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1000


@dataclass
class OutputConfig:
    """Configuration pour la sortie."""
    format: str = "markdown"
    reports_dir: str = "output/reports"
    filename_template: str = "tech_digest_{date}.md"
    date_format: str = "%Y%m%d"
    include_metrics: bool = True


@dataclass
class VeilleConfig:
    """Configuration complète du système de veille."""
    collection: CollectionConfig = field(default_factory=CollectionConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    synthesis: SynthesisConfig = field(default_factory=SynthesisConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


class ConfigLoader:
    """
    Gestionnaire centralisé pour charger et valider la configuration.
    
    Fonctionnalités:
    - Chargement depuis fichiers YAML
    - Support des profils et environnements
    - Validation des paramètres
    - Override via variables d'environnement
    - Cache de configuration
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialise le loader de configuration.
        
        Args:
            config_dir: Dossier racine de configuration
        """
        self.config_dir = Path(config_dir)
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.logger = logger.bind(component="ConfigLoader")
        
        if not self.config_dir.exists():
            raise ValueError(f"Dossier config introuvable: {self.config_dir}")
    
    def load_config(self, 
                   config_file: str = "veille_config.yaml",
                   profile: Optional[str] = None,
                   environment: Optional[str] = None) -> VeilleConfig:
        """
        Charge la configuration complète.
        
        Args:
            config_file: Fichier de configuration à charger
            profile: Profil à appliquer (demo, production, expert)
            environment: Environnement à appliquer (development, production)
            
        Returns:
            Configuration complète validée
        """
        # Chargement du fichier principal
        config_path = self.config_dir / config_file
        
        if not config_path.exists():
            raise FileNotFoundError(f"Fichier config introuvable: {config_path}")
        
        # Cache key
        cache_key = f"{config_file}_{profile}_{environment}"
        
        if cache_key not in self.cache:
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    raw_config = yaml.safe_load(f)
                
                # Application du profil
                if profile and profile in raw_config.get("profiles", {}):
                    self._apply_profile(raw_config, profile)
                    self.logger.info(f"📋 Profil appliqué: {profile}")
                
                # Application de l'environnement
                if environment and environment in raw_config.get("environments", {}):
                    self._apply_environment(raw_config, environment)
                    self.logger.info(f"🌍 Environnement appliqué: {environment}")
                
                # Override avec variables d'environnement
                self._apply_env_overrides(raw_config)
                
                self.cache[cache_key] = raw_config
                self.logger.debug(f"📝 Configuration chargée: {config_file}")
                
            except Exception as e:
                self.logger.error(f"❌ Erreur chargement config {config_file}: {e}")
                raise
        
        raw_config = self.cache[cache_key]
        
        # Conversion en objets typés
        config = self._build_typed_config(raw_config)
        
        # Validation
        self._validate_config(config)
        
        return config
    
    def _apply_profile(self, config: Dict[str, Any], profile: str):
        """Applique un profil à la configuration."""
        profile_config = config["profiles"][profile]
        self._deep_merge(config, profile_config)
    
    def _apply_environment(self, config: Dict[str, Any], environment: str):
        """Applique un environnement à la configuration."""
        env_config = config["environments"][environment]
        self._deep_merge(config, env_config)
    
    def _apply_env_overrides(self, config: Dict[str, Any]):
        """Applique les overrides depuis les variables d'environnement."""
        
        # Mapping des variables d'environnement importantes
        env_mappings = {
            "VEILLE_TOTAL_LIMIT": ["collection", "total_limit"],
            "VEILLE_TARGET_AUDIENCE": ["synthesis", "target_audience"],
            "VEILLE_MAX_ARTICLES": ["synthesis", "max_articles_in_digest"],
            "VEILLE_EXPERT_LEVEL": ["analysis", "expert_profile", "level"],
            "VEILLE_LOG_LEVEL": ["logging", "level"]
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested_value(config, config_path, self._parse_env_value(value))
                self.logger.debug(f"🔧 Override env: {env_var} = {value}")
    
    def _deep_merge(self, base: Dict[str, Any], overlay: Dict[str, Any]):
        """Merge profond de deux dictionnaires."""
        for key, value in overlay.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _set_nested_value(self, config: Dict[str, Any], path: List[str], value: Any):
        """Définit une valeur dans un dictionnaire imbriqué."""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    
    def _parse_env_value(self, value: str) -> Any:
        """Parse une valeur de variable d'environnement."""
        # Essaie de convertir en int
        try:
            return int(value)
        except ValueError:
            pass
        
        # Essaie de convertir en float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Essaie de convertir en boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Reste en string
        return value
    
    def _build_typed_config(self, raw_config: Dict[str, Any]) -> VeilleConfig:
        """Construit les objets de configuration typés."""
        
        # Configuration collection
        collection_data = raw_config.get("collection", {})
        collection = CollectionConfig(
            total_limit=collection_data.get("total_limit", 15),
            source_limits=collection_data.get("source_limits", {"medium": 8, "arxiv": 8}),
            keywords=collection_data.get("keywords", ["AI", "GenAI", "LLM"]),
            max_age_days=collection_data.get("max_age_days", 30),
            enabled_sources=collection_data.get("enabled_sources", ["medium", "arxiv"])
        )
        
        # Configuration analysis
        analysis_data = raw_config.get("analysis", {})
        expert_profile = analysis_data.get("expert_profile", {})
        llm_config = analysis_data.get("llm", {})
        
        analysis = AnalysisConfig(
            expert_level=expert_profile.get("level", "intermediate"),
            interests=expert_profile.get("interests", ["LangGraph", "Multi-agent"]),
            avoid_topics=expert_profile.get("avoid_topics", ["basic tutorials"]),
            preferred_content_types=expert_profile.get("preferred_content_types", ["technical implementation"]),
            batch_size=analysis_data.get("batch_size", 3),
            max_retries=analysis_data.get("max_retries", 2),
            recommendation_threshold=analysis_data.get("recommendation_threshold", 7.0),
            llm_model=llm_config.get("model", "gpt-4o-mini"),
            llm_temperature=llm_config.get("temperature", 0.1),
            llm_max_tokens=llm_config.get("max_tokens", 500)
        )
        
        # Configuration synthesis
        synthesis_data = raw_config.get("synthesis", {})
        word_limits = synthesis_data.get("word_limits", {})
        synthesis_llm = synthesis_data.get("llm", {})
        
        synthesis = SynthesisConfig(
            target_audience=synthesis_data.get("target_audience", "senior_engineer"),
            max_articles_in_digest=synthesis_data.get("max_articles_in_digest", 3),
            max_insights=synthesis_data.get("max_insights", 5),
            max_recommendations=synthesis_data.get("max_recommendations", 4),
            executive_summary_max_words=word_limits.get("executive_summary", 150),
            article_summary_max_words=word_limits.get("article_summary", 100),
            tone=synthesis_data.get("tone", "professional"),
            technical_depth=synthesis_data.get("technical_depth", "high"),
            include_technical_trends=synthesis_data.get("include_technical_trends", True),
            include_action_items=synthesis_data.get("include_action_items", True),
            focus_areas=synthesis_data.get("focus_areas", ["implementation_details"]),
            llm_model=synthesis_llm.get("model", "gpt-4o"),
            llm_temperature=synthesis_llm.get("temperature", 0.2),
            llm_max_tokens=synthesis_llm.get("max_tokens", 1000)
        )
        
        # Configuration output
        output_data = raw_config.get("output", {})
        output = OutputConfig(
            format=output_data.get("format", "markdown"),
            reports_dir=output_data.get("reports_dir", "output/reports"),
            filename_template=output_data.get("filename_template", "tech_digest_{date}.md"),
            date_format=output_data.get("date_format", "%Y%m%d"),
            include_metrics=output_data.get("include_metrics", True)
        )
        
        return VeilleConfig(
            collection=collection,
            analysis=analysis,
            synthesis=synthesis,
            output=output
        )
    
    def _validate_config(self, config: VeilleConfig):
        """Valide la configuration."""
        errors = []
        
        # Validation collection
        if config.collection.total_limit <= 0:
            errors.append("collection.total_limit doit être > 0")
        
        if not config.collection.keywords:
            errors.append("collection.keywords ne peut pas être vide")
        
        # Validation analysis
        if config.analysis.expert_level not in ["beginner", "intermediate", "expert"]:
            errors.append("analysis.expert_level doit être beginner, intermediate ou expert")
        
        if config.analysis.batch_size <= 0:
            errors.append("analysis.batch_size doit être > 0")
        
        # Validation synthesis
        if config.synthesis.max_articles_in_digest <= 0:
            errors.append("synthesis.max_articles_in_digest doit être > 0")
        
        if config.synthesis.target_audience not in ["senior_engineer", "tech_lead", "architect"]:
            errors.append("synthesis.target_audience doit être senior_engineer, tech_lead ou architect")
        
        # Validation output
        if not config.output.reports_dir:
            errors.append("output.reports_dir ne peut pas être vide")
        
        if errors:
            raise ValueError(f"Erreurs de validation config: {errors}")
        
        self.logger.debug("✅ Validation configuration OK")
    
    def save_config(self, config: VeilleConfig, output_file: str = "veille_config_generated.yaml"):
        """
        Sauvegarde une configuration en YAML.
        
        Args:
            config: Configuration à sauvegarder
            output_file: Fichier de sortie
        """
        output_path = self.config_dir / output_file
        
        # Conversion en dict
        config_dict = {
            "collection": {
                "total_limit": config.collection.total_limit,
                "source_limits": config.collection.source_limits,
                "keywords": config.collection.keywords,
                "max_age_days": config.collection.max_age_days,
                "enabled_sources": config.collection.enabled_sources
            },
            "analysis": {
                "expert_profile": {
                    "level": config.analysis.expert_level,
                    "interests": config.analysis.interests,
                    "avoid_topics": config.analysis.avoid_topics,
                    "preferred_content_types": config.analysis.preferred_content_types
                },
                "batch_size": config.analysis.batch_size,
                "max_retries": config.analysis.max_retries,
                "recommendation_threshold": config.analysis.recommendation_threshold,
                "llm": {
                    "model": config.analysis.llm_model,
                    "temperature": config.analysis.llm_temperature,
                    "max_tokens": config.analysis.llm_max_tokens
                }
            },
            "synthesis": {
                "target_audience": config.synthesis.target_audience,
                "max_articles_in_digest": config.synthesis.max_articles_in_digest,
                "max_insights": config.synthesis.max_insights,
                "max_recommendations": config.synthesis.max_recommendations,
                "word_limits": {
                    "executive_summary": config.synthesis.executive_summary_max_words,
                    "article_summary": config.synthesis.article_summary_max_words
                },
                "tone": config.synthesis.tone,
                "technical_depth": config.synthesis.technical_depth,
                "include_technical_trends": config.synthesis.include_technical_trends,
                "include_action_items": config.synthesis.include_action_items,
                "focus_areas": config.synthesis.focus_areas,
                "llm": {
                    "model": config.synthesis.llm_model,
                    "temperature": config.synthesis.llm_temperature,
                    "max_tokens": config.synthesis.llm_max_tokens
                }
            },
            "output": {
                "format": config.output.format,
                "reports_dir": config.output.reports_dir,
                "filename_template": config.output.filename_template,
                "date_format": config.output.date_format,
                "include_metrics": config.output.include_metrics
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
        
        self.logger.info(f"💾 Configuration sauvegardée: {output_path}")
    
    def clear_cache(self):
        """Vide le cache de configuration."""
        self.cache.clear()
        self.logger.info("🗑️ Cache configuration vidé")


# Instance globale pour utilisation simple
_global_config_loader = None

def get_config_loader(config_dir: str = "config") -> ConfigLoader:
    """
    Retourne l'instance globale du ConfigLoader.
    
    Args:
        config_dir: Dossier racine de configuration
        
    Returns:
        Instance ConfigLoader
    """
    global _global_config_loader
    
    if _global_config_loader is None:
        _global_config_loader = ConfigLoader(config_dir)
    
    return _global_config_loader


def load_config(profile: Optional[str] = None, 
               environment: Optional[str] = None) -> VeilleConfig:
    """
    Fonction de convenience pour charger la configuration.
    
    Args:
        profile: Profil à appliquer
        environment: Environnement à appliquer
        
    Returns:
        Configuration complète
    """
    loader = get_config_loader()
    return loader.load_config(profile=profile, environment=environment)
