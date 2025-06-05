"""
Point d'entrée principal enrichi de l'Agent de Veille Intelligente - Phase 3

Version enrichie avec intégration base de données :
- Déduplication intelligente des articles
- Cache des analyses pour optimiser les performances  
- Historique complet et métriques avancées
- Suivi des performances en temps réel
"""
import asyncio
import sys
import os
import argparse
from datetime import datetime
from loguru import logger

# Imports de la configuration centralisée
from src.utils.config_loader import load_config
from src.models.database_enhanced import DatabaseManagerEnhanced
from src.services.veille_integration_service import VeilleIntegrationService
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
    """Parse les arguments de ligne de commande avec nouvelles options Phase 3."""
    parser = argparse.ArgumentParser(
        description="Agent de Veille Intelligente ENRICHI - Générateur de digest avec BD",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation Phase 3:
  python main_enhanced.py                          # Mode production avec BD enrichie
  python main_enhanced.py --demo                   # Mode démo avec BD
  python main_enhanced.py --profile expert         # Profil expert avec cache
  python main_enhanced.py --skip-cache             # Forcer analyse (ignorer cache)
  python main_enhanced.py --cleanup-old            # Nettoyer anciennes données
  python main_enhanced.py --show-stats             # Afficher statistiques BD
  python main_enhanced.py --cache-max-age 12       # Cache max 12h
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
    
    # Options Phase 3 - Base de données
    parser.add_argument(
        "--skip-cache", 
        action="store_true", 
        help="Ignorer le cache et forcer l'analyse de tous les articles"
    )
    
    parser.add_argument(
        "--cache-max-age", 
        type=int, 
        default=24,
        help="Âge maximum du cache en heures (défaut: 24h)"
    )
    
    parser.add_argument(
        "--cleanup-old", 
        action="store_true", 
        help="Nettoyer les anciennes données avant exécution"
    )
    
    parser.add_argument(
        "--show-stats", 
        action="store_true", 
        help="Afficher les statistiques détaillées de la BD"
    )
    
    parser.add_argument(
        "--db-path", 
        help="Chemin personnalisé vers la base de données"
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
    
    parser.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Mode verbose (equivalent à --log-level DEBUG)"
    )
    
    return parser.parse_args()


async def create_daily_digest_enhanced(profile: str = None, 
                                     environment: str = None, 
                                     db_path: str = None,
                                     cache_max_age_hours: int = 24,
                                     skip_cache: bool = False,
                                     **overrides):
    """Workflow principal enrichi de création du digest quotidien avec BD."""
    
    logger.info("🚀 DÉMARRAGE AGENT DE VEILLE INTELLIGENTE ENRICHI")
    logger.info("🗄️ Version Phase 3 avec Base de Données Avancée")
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
        logger.info(f"   💾 Cache: {'DÉSACTIVÉ' if skip_cache else f'{cache_max_age_hours}h max'}")
        
        # ===============================
        # INITIALISATION SERVICE BD ENRICHIE
        # ===============================
        logger.info("🗄️ Initialisation service BD enrichie...")
        integration_service = VeilleIntegrationService(db_path)
        
        # Configuration pour la collecte basée sur le config file
        collection_config = CollectionConfig(
            total_limit=config.collection.total_limit,
            source_limits=config.collection.source_limits,
            keywords=config.collection.keywords,
            max_age_days=config.collection.max_age_days,
            enable_deduplication=True
        )
        
        logger.info("✅ Configuration et BD enrichie validées")
        
        # ===============================
        # PHASE 1: COLLECTE AVEC DÉDUPLICATION
        # ===============================
        logger.info("\n📡 PHASE 1: Collecte avec déduplication intelligente...")
        
        collector = TechCollectorAgent(collection_config)
        collection_result = await collector.collect_all_sources()
        
        if collection_result.total_filtered == 0:
            logger.error("❌ Aucun contenu collecté - Arrêt du processus")
            return None
        
        # Traitement avec déduplication via service enrichi
        dedup_result = await integration_service.process_collection_with_deduplication(collection_result)
        
        unique_contents = dedup_result['unique_contents']
        dedup_stats = dedup_result['deduplication_stats']
        
        if not unique_contents:
            logger.warning("⚠️ Tous les articles sont des doublons - Aucun nouveau contenu")
            # Afficher les statistiques quand même
            integration_service.print_daily_summary()
            return None
        
        logger.info(f"✅ Collecte avec déduplication réussie:")
        logger.info(f"   📊 {dedup_stats['total_collected']} articles récupérés")
        logger.info(f"   🆕 {dedup_stats['unique_articles']} articles uniques")
        logger.info(f"   🔄 {dedup_stats['duplicates_removed']} doublons évités")
        if dedup_stats['duplicates_by_type']:
            logger.info(f"   📋 Types de doublons: {dedup_stats['duplicates_by_type']}")
        
        # ===============================
        # PHASE 2: ANALYSE AVEC CACHE
        # ===============================
        logger.info("\n🧠 PHASE 2: Analyse intelligente avec cache...")
        
        # Création de l'expert profile depuis la config
        from src.models.analysis_models import ExpertProfile, ExpertLevel
        expert_profile = ExpertProfile(
            level=ExpertLevel(config.analysis.expert_level),
            interests=config.analysis.interests,
            avoid_topics=config.analysis.avoid_topics,
            preferred_content_types=config.analysis.preferred_content_types
        )
        
        analyzer = TechAnalyzerAgent(expert_profile)
        
        # Fonction d'analyse pour le service d'intégration
        async def analyze_single_content(raw_content):
            # Utiliser analyze_contents qui prend une liste et retourner le premier élément
            results = await analyzer.analyze_contents([raw_content])
            if not results:
                raise ValueError(f"Aucune analyse produite pour: {raw_content.title}")
            return results[0]
        
        # Traitement avec cache via service enrichi
        if skip_cache:
            logger.info("⚠️ Cache désactivé - Analyse forcée de tous les articles")
            analyzed_articles = await analyzer.analyze_contents(unique_contents)
            # Sauvegarde en cache pour les prochaines fois
            for analyzed_content in analyzed_articles:
                integration_service.db.save_analyzed_content(analyzed_content)
        else:
            analyzed_articles = await integration_service.process_analysis_with_cache(
                unique_contents, 
                analyze_single_content,
                cache_max_age_hours
            )
        
        if not analyzed_articles:
            logger.error("❌ Aucun article analysé - Arrêt du processus")
            return None
        
        recommended_articles = [a for a in analyzed_articles if a.analysis.recommended]
        avg_score = sum(a.analysis.relevance_score for a in analyzed_articles) / len(analyzed_articles)
        
        logger.info(f"✅ Analyse avec cache réussie:")
        logger.info(f"   📊 {len(analyzed_articles)} articles analysés")
        logger.info(f"   🎯 {len(recommended_articles)} articles recommandés")
        logger.info(f"   📈 Score moyen: {avg_score:.2f}/10.0")
        
        # ===============================
        # PHASE 3: SYNTHÈSE AVEC HISTORIQUE
        # ===============================
        logger.info("\n📝 PHASE 3: Génération du digest avec historique...")
        
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
        
        # Fonction de synthèse pour le service d'intégration
        async def synthesize_content(analyzed_contents):
            return await synthesizer.create_daily_digest(analyzed_contents)
        
        # Configuration snapshot pour l'historique
        config_snapshot = {
            'profile': profile,
            'environment': environment,
            'collection_config': {
                'total_limit': config.collection.total_limit,
                'keywords': config.collection.keywords
            },
            'analysis_config': {
                'expert_level': config.analysis.expert_level,
                'recommendation_threshold': config.analysis.recommendation_threshold
            },
            'synthesis_config': synthesis_config,
            'cache_settings': {
                'max_age_hours': cache_max_age_hours,
                'skip_cache': skip_cache
            },
            'execution_time': start_time.isoformat()
        }
        
        # Traitement avec historique via service enrichi
        synthesis_result = await integration_service.process_synthesis_with_history(
            analyzed_articles,
            synthesize_content,
            config_snapshot
        )
        
        daily_digest = synthesis_result['daily_digest']
        
        # Sauvegarde du digest selon la config output
        output_path = await synthesizer.save_digest_to_file(
            daily_digest, 
            output_dir=config.output.reports_dir
        )
        
        logger.info(f"✅ Digest avec historique généré:")
        logger.info(f"   📋 {daily_digest.title}")
        logger.info(f"   📄 {daily_digest.word_count} mots ({daily_digest.estimated_read_time}min)")
        logger.info(f"   🏆 {len(daily_digest.top_articles)} articles vedettes")
        logger.info(f"   💡 {len(daily_digest.key_insights)} insights clés")
        logger.info(f"   🎯 {len(daily_digest.recommendations)} recommandations")
        logger.info(f"   💾 Sauvegardé: {output_path}")
        logger.info(f"   🗄️ Historique BD: ID {synthesis_result['digest_id']}")
        
        # ===============================
        # MÉTRIQUES ET PERFORMANCE
        # ===============================
        logger.info("\n📊 Sauvegarde des métriques de performance...")
        
        # Mise à jour des statistiques de session
        integration_service.session_stats['articles_processed'] = len(collection_result.contents)
        
        # Sauvegarde des métriques via service enrichi
        metrics_id = integration_service.save_session_metrics(
            collection_result,
            analyzed_articles,
            daily_digest
        )
        
        # ===============================
        # RÉSUMÉ FINAL ENRICHI
        # ===============================
        total_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"\n🎉 DIGEST QUOTIDIEN ENRICHI GÉNÉRÉ AVEC SUCCÈS!")
        logger.info(f"⏱️ Temps total: {total_time:.2f}s")
        logger.info(f"📊 Performance: {total_time/len(analyzed_articles):.2f}s/article")
        logger.info(f"📄 Fichier: {output_path}")
        logger.info(f"🗄️ Métriques BD: ID {metrics_id}")
        
        # Aperçu du contenu
        logger.info(f"\n📋 APERÇU DU DIGEST ENRICHI:")
        logger.info(f"🗺️ {daily_digest.title}")
        
        # Top articles
        for i, article in enumerate(daily_digest.top_articles[:2], 1):
            logger.info(f"   {i}. {article.title_refined}")
            logger.info(f"      📊 Score: {article.relevance_for_audience:.2f} | {article.complexity_level}")
        
        # Top insights
        for insight in daily_digest.key_insights[:2]:
            logger.info(f"   💡 {insight}")
        
        # Statistiques enrichies
        logger.info(f"\n📈 STATISTIQUES ENRICHIES:")
        logger.info(f"   🔄 Taux déduplication: {dedup_stats['duplication_rate']:.1%}")
        logger.info(f"   💾 Cache hits: {integration_service.session_stats['cache_hits']}")
        logger.info(f"   ⏱️ Temps économisé: {integration_service.session_stats['analysis_time_saved']:.1f}s")
        
        # Affichage du résumé quotidien
        integration_service.print_daily_summary()
        
        return {
            'digest': daily_digest,
            'output_path': output_path,
            'stats': {
                'collection': collection_result,
                'deduplication': dedup_stats,
                'analysis': analyzed_articles,
                'synthesis': synthesis_result,
                'total_time': total_time
            },
            'db_ids': {
                'digest_id': synthesis_result['digest_id'],
                'metrics_id': metrics_id
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution enrichie: {e}")
        logger.exception("Détails de l'erreur:")
        raise


def main():
    """Fonction principale enrichie avec gestion des arguments CLI Phase 3."""
    
    # Parse des arguments
    args = parse_arguments()
    
    # Configuration du logging
    log_level = "DEBUG" if args.verbose else args.log_level
    setup_logging(log_level)
    
    # Détermination du profil et environnement
    profile = args.profile or ("demo" if args.demo else None)
    environment = args.environment
    
    # Options Phase 3
    cache_max_age = 0 if args.skip_cache else args.cache_max_age
    skip_cache = args.skip_cache
    db_path = args.db_path
    
    # Préparation des overrides
    overrides = {}
    if args.total_limit:
        overrides['total_limit'] = args.total_limit
    if args.target_audience:
        overrides['target_audience'] = args.target_audience  
    if args.max_articles:
        overrides['max_articles'] = args.max_articles
    
    # Log des paramètres d'exécution enrichie
    logger.info("🚀 Agent de Veille Intelligente ENRICHI - Phase 3")
    logger.info("🗄️ Version avec Base de Données Avancée")
    if profile:
        logger.info(f"📋 Profil: {profile}")
    if environment:
        logger.info(f"🌍 Environnement: {environment}")
    if overrides:
        logger.info(f"🔧 Overrides: {overrides}")
    
    # Options Phase 3
    logger.info(f"💾 Cache: {'DÉSACTIVÉ' if skip_cache else f'{cache_max_age}h max'}")
    if db_path:
        logger.info(f"🗄️ BD personnalisée: {db_path}")
    
    try:
        # Actions préliminaires Phase 3
        if args.cleanup_old:
            logger.info("🧹 Nettoyage des anciennes données...")
            integration_service = VeilleIntegrationService(db_path)
            cleanup_result = integration_service.cleanup_old_data()
            logger.info(f"✅ Nettoyage terminé: {cleanup_result}")
        
        if args.show_stats:
            logger.info("📊 Affichage des statistiques de la BD...")
            integration_service = VeilleIntegrationService(db_path)
            integration_service.print_daily_summary()
            return
        
        # Exécution principale enrichie
        result = asyncio.run(create_daily_digest_enhanced(
            profile=profile,
            environment=environment,
            db_path=db_path,
            cache_max_age_hours=cache_max_age,
            skip_cache=skip_cache,
            **overrides
        ))
        
        if result:
            logger.info("🎉 Traitement enrichi terminé avec succès!")
            
            # Affichage des statistiques finales enrichies
            stats = result['stats']
            db_ids = result['db_ids']
            
            logger.info(f"📊 Statistiques finales enrichies:")
            logger.info(f"   📡 Collectés: {stats['collection'].total_collected}")
            logger.info(f"   🔄 Doublons évités: {stats['deduplication']['duplicates_removed']}")
            logger.info(f"   🧠 Analysés: {len(stats['analysis'])}")
            logger.info(f"   ⏱️ Durée totale: {stats['total_time']:.1f}s")
            logger.info(f"   📄 Fichier: {result['output_path']}")
            logger.info(f"   🗄️ BD - Digest ID: {db_ids['digest_id']}, Métriques ID: {db_ids['metrics_id']}")
        else:
            logger.error("❌ Échec du traitement enrichi")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("⚠️ Interruption utilisateur")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Erreur fatale enrichie: {e}")
        if log_level == "DEBUG":
            logger.exception("Détails:")
        sys.exit(1)


if __name__ == "__main__":
    main()
