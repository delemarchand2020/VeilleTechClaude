"""
Point d'entrée principal de l'Agent de Veille Intelligente - Version Complète

Orchestrateur des 3 agents : Collecteur → Analyseur → Synthétiseur
Génère automatiquement un digest quotidien de veille technologique.
"""
import asyncio
import sys
import os
import argparse
from datetime import datetime
from loguru import logger

# Imports de la configuration centralisée
from src.utils.config_loader import load_config
from src.models.database import DatabaseManager
from src.agents import (
    TechCollectorAgent, CollectionConfig,
    TechAnalyzerAgent, TechSynthesizerAgent
)


def setup_logging(level: str = "INFO"):
    """Configure le logging."""
    logger.remove()
    logger.add(
        sys.stdout, 
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> | {message}",
        level=level
    )


def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Agent de Veille Intelligente - Générateur de digest quotidien",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python main.py                              # Mode production standard
  python main.py --demo                       # Mode démo rapide
  python main.py --profile expert             # Profil expert
  python main.py --environment development    # Environnement de développement
  python main.py --total-limit 20             # Override limite de collecte
  python main.py --target-audience tech_lead  # Override audience cible
        """
    )
    
    # Modes de fonctionnement
    parser.add_argument(
        "--demo", "-d", 
        action="store_true", 
        help="Mode démo avec collecte réduite"
    )
    
    # Configuration
    parser.add_argument(
        "--profile", "-p", 
        choices=["demo", "production", "expert"],
        help="Profil de configuration à utiliser"
    )
    
    parser.add_argument(
        "--environment", "-e", 
        choices=["development", "production"],
        help="Environnement d'exécution"
    )
    
    # Overrides de configuration
    parser.add_argument(
        "--total-limit", 
        type=int, 
        help="Nombre maximum d'articles à collecter"
    )
    
    parser.add_argument(
        "--target-audience", 
        choices=["senior_engineer", "tech_lead", "architect"],
        help="Audience cible pour le digest"
    )
    
    parser.add_argument(
        "--max-articles", 
        type=int, 
        help="Nombre maximum d'articles dans le digest final"
    )
    
    # Options de sortie
    parser.add_argument(
        "--output-dir", 
        help="Répertoire de sortie pour les digests"
    )
    
    # Logging
    parser.add_argument(
        "--log-level", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Niveau de logging"
    )
    
    # Options de débogage
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Mode verbose (equivalent à --log-level DEBUG)"
    )
    
    return parser.parse_args()


async def create_daily_digest(profile: str = None, environment: str = None, **overrides):
    """Workflow principal de création du digest quotidien."""
    
    logger.info("🚀 DÉMARRAGE AGENT DE VEILLE INTELLIGENTE")
    logger.info("🎯 Génération du digest quotidien GenAI/LLM/Agentic")
    
    start_time = datetime.now()
    
    try:
        # ===============================
        # CONFIGURATION ET VALIDATION
        # ===============================
        logger.info("🔧 Chargement de la configuration...")
        config = load_config(profile=profile, environment=environment)
        
        # Application des overrides CLI
        if overrides:
            logger.info(f"🔧 Application overrides: {overrides}")
            # Exemple d'overrides
            if 'total_limit' in overrides:
                config.collection.total_limit = overrides['total_limit']
            if 'target_audience' in overrides:
                config.synthesis.target_audience = overrides['target_audience']
            if 'max_articles' in overrides:
                config.synthesis.max_articles_in_digest = overrides['max_articles']
        
        logger.info(f"⚙️ Configuration:")
        logger.info(f"   📡 Collecte: {config.collection.total_limit} articles max")
        logger.info(f"   🎯 Audience: {config.synthesis.target_audience}")
        logger.info(f"   📝 Digest: {config.synthesis.max_articles_in_digest} articles")
        
        logger.info("💾 Initialisation base de données...")
        db = DatabaseManager()
        
        # Configuration pour la collecte basée sur le config file
        collection_config = CollectionConfig(
            total_limit=config.collection.total_limit,
            source_limits=config.collection.source_limits,
            keywords=config.collection.keywords,
            max_age_days=config.collection.max_age_days,
            enable_deduplication=True
        )
        
        logger.info("✅ Configuration validée")
        
        # ===============================
        # PHASE 1: COLLECTE
        # ===============================
        logger.info("\n📡 PHASE 1: Collecte de contenu...")
        
        collector = TechCollectorAgent(collection_config)
        collection_result = await collector.collect_all_sources()
        
        if collection_result.total_filtered == 0:
            logger.error("❌ Aucun contenu collecté - Arrêt du processus")
            return None
        
        logger.info(f"✅ Collecte réussie:")
        logger.info(f"   📊 {collection_result.total_collected} articles récupérés")
        logger.info(f"   ✅ {collection_result.total_filtered} articles filtrés")
        logger.info(f"   🔄 {collection_result.duplicates_removed} doublons supprimés")
        logger.info(f"   ⏱️ {collection_result.collection_time:.2f}s")
        
        # ===============================
        # PHASE 2: ANALYSE
        # ===============================
        logger.info("\n🧠 PHASE 2: Analyse intelligente...")
        
        # Création de l'expert profile depuis la config
        from src.models.analysis_models import ExpertProfile, ExpertLevel
        expert_profile = ExpertProfile(
            level=ExpertLevel(config.analysis.expert_level),
            interests=config.analysis.interests,
            avoid_topics=config.analysis.avoid_topics,
            preferred_content_types=config.analysis.preferred_content_types
        )
        
        analyzer = TechAnalyzerAgent(expert_profile)
        analyzed_articles = await analyzer.analyze_contents(collection_result.contents)
        
        if not analyzed_articles:
            logger.error("❌ Aucun article analysé - Arrêt du processus")
            return None
        
        recommended_articles = [a for a in analyzed_articles if a.analysis.recommended]
        avg_score = sum(a.final_score for a in analyzed_articles) / len(analyzed_articles)
        
        logger.info(f"✅ Analyse réussie:")
        logger.info(f"   📊 {len(analyzed_articles)} articles analysés")
        logger.info(f"   🎯 {len(recommended_articles)} articles recommandés")
        logger.info(f"   📈 Score moyen: {avg_score:.2f}/1.0")
        
        # ===============================
        # PHASE 3: SYNTHÈSE
        # ===============================
        logger.info("\n📝 PHASE 3: Génération du digest...")
        
        # Configuration du synthétiseur avec la config centralisée
        synthesis_config = {
            "target_audience": config.synthesis.target_audience,
            "max_articles_in_digest": config.synthesis.max_articles_in_digest,
            "executive_summary_max_words": config.synthesis.executive_summary_max_words,
            "article_summary_max_words": config.synthesis.article_summary_max_words,
            "max_insights": config.synthesis.max_insights,
            "max_recommendations": config.synthesis.max_recommendations,
            "include_technical_trends": config.synthesis.include_technical_trends,
            "include_action_items": config.synthesis.include_action_items,
            "tone": config.synthesis.tone,
            "technical_depth": config.synthesis.technical_depth,
            "focus_areas": config.synthesis.focus_areas
        }
        
        synthesizer = TechSynthesizerAgent(synthesis_config)
        daily_digest = await synthesizer.create_daily_digest(analyzed_articles)
        
        # Sauvegarde du digest selon la config output
        output_path = await synthesizer.save_digest_to_file(
            daily_digest, 
            output_dir=config.output.reports_dir
        )
        
        logger.info(f"✅ Digest généré:")
        logger.info(f"   📋 {daily_digest.title}")
        logger.info(f"   📄 {daily_digest.word_count} mots ({daily_digest.estimated_read_time}min)")
        logger.info(f"   🏆 {len(daily_digest.top_articles)} articles vedettes")
        logger.info(f"   💡 {len(daily_digest.key_insights)} insights clés")
        logger.info(f"   🎯 {len(daily_digest.recommendations)} recommandations")
        logger.info(f"   💾 Sauvegardé: {output_path}")
        
        # ===============================
        # RÉSUMÉ FINAL
        # ===============================
        total_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"\n🎉 DIGEST QUOTIDIEN GÉNÉRÉ AVEC SUCCÈS!")
        logger.info(f"⏱️ Temps total: {total_time:.2f}s")
        logger.info(f"📊 Performance: {total_time/len(analyzed_articles):.2f}s/article")
        logger.info(f"📄 Fichier: {output_path}")
        
        # Aperçu du contenu
        logger.info(f"\n📋 APERÇU DU DIGEST:")
        logger.info(f"🗺️ {daily_digest.title}")
        
        # Top articles
        for i, article in enumerate(daily_digest.top_articles[:2], 1):
            logger.info(f"   {i}. {article.title_refined}")
            logger.info(f"      📊 Score: {article.relevance_for_audience:.2f} | {article.complexity_level}")
        
        # Top insights
        for insight in daily_digest.key_insights[:2]:
            logger.info(f"   💡 {insight}")
        
        return {
            'digest': daily_digest,
            'output_path': output_path,
            'stats': {
                'collection': collection_result,
                'analysis': analyzed_articles,
                'total_time': total_time
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution: {e}")
        logger.exception("Détails de l'erreur:")
        raise


def main():
    """Fonction principale avec gestion des arguments CLI."""
    
    # Parse des arguments
    args = parse_arguments()
    
    # Configuration du logging
    log_level = "DEBUG" if args.verbose else args.log_level
    setup_logging(log_level)
    
    # Détermination du profil et environnement
    profile = args.profile or ("demo" if args.demo else None)
    environment = args.environment
    
    # Préparation des overrides
    overrides = {}
    if args.total_limit:
        overrides['total_limit'] = args.total_limit
    if args.target_audience:
        overrides['target_audience'] = args.target_audience  
    if args.max_articles:
        overrides['max_articles'] = args.max_articles
    
    # Log des paramètres d'exécution
    logger.info("🚀 Agent de Veille Intelligente")
    if profile:
        logger.info(f"📋 Profil: {profile}")
    if environment:
        logger.info(f"🌍 Environnement: {environment}")
    if overrides:
        logger.info(f"🔧 Overrides: {overrides}")
    
    try:
        # Exécution principale
        result = asyncio.run(create_daily_digest(
            profile=profile,
            environment=environment,
            **overrides
        ))
        
        if result:
            logger.info("🎉 Traitement terminé avec succès!")
            
            # Affichage des statistiques finales
            stats = result['stats']
            logger.info(f"📊 Statistiques finales:")
            logger.info(f"   📡 Collectés: {stats['collection'].total_collected}")
            logger.info(f"   🧠 Analysés: {len(stats['analysis'])}")
            logger.info(f"   ⏱️ Durée totale: {stats['total_time']:.1f}s")
            logger.info(f"   📄 Fichier: {result['output_path']}")
        else:
            logger.error("❌ Échec du traitement")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("⚠️ Interruption utilisateur")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        if log_level == "DEBUG":
            logger.exception("Détails:")
        sys.exit(1)


if __name__ == "__main__":
    main()
