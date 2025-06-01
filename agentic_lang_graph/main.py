"""
Point d'entrée principal de l'Agent de Veille Intelligente - Version Complète

Orchestrateur des 3 agents : Collecteur → Analyseur → Synthétiseur
Génère automatiquement un digest quotidien de veille technologique.
"""
import asyncio
import sys
import os
from datetime import datetime
from loguru import logger

# Configuration du logging
logger.remove()
logger.add(
    sys.stdout, 
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan> | {message}",
    level="INFO"
)

from src.utils.config import validate_config
from src.models.database import DatabaseManager
from src.agents import (
    TechCollectorAgent, CollectionConfig,
    TechAnalyzerAgent, TechSynthesizerAgent
)


async def create_daily_digest():
    """Workflow principal de création du digest quotidien."""
    
    logger.info("🚀 DÉMARRAGE AGENT DE VEILLE INTELLIGENTE")
    logger.info("🎯 Génération du digest quotidien GenAI/LLM/Agentic")
    
    start_time = datetime.now()
    
    try:
        # ===============================
        # CONFIGURATION ET VALIDATION
        # ===============================
        logger.info("🔧 Validation de la configuration...")
        validate_config()
        
        logger.info("💾 Initialisation base de données...")
        db = DatabaseManager()
        
        # Configuration pour la collecte production
        collection_config = CollectionConfig(
            total_limit=15,  # Nombre optimisé pour analyse qualitative
            source_limits={'medium': 8, 'arxiv': 8},
            keywords=[
                'AI', 'GenAI', 'LLM', 'GPT', 'ChatGPT',
                'LangChain', 'LangGraph', 'transformer',
                'machine learning', 'deep learning',
                'neural network', 'agentic', 'multi-agent',
                'artificial intelligence'
            ],
            max_age_days=30,  # Articles récents mais suffisamment de contenu
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
        
        analyzer = TechAnalyzerAgent()
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
        
        synthesizer = TechSynthesizerAgent()
        daily_digest = await synthesizer.create_daily_digest(analyzed_articles)
        
        # Sauvegarde du digest
        output_path = await synthesizer.save_digest_to_file(daily_digest)
        
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
        logger.info(f"🗓️ {daily_digest.title}")
        
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


async def run_quick_demo():
    """Démo rapide avec moins d'articles pour test."""
    
    logger.info("🚀 MODE DÉMO RAPIDE")
    
    # Configuration allégée
    demo_config = CollectionConfig(
        total_limit=6,
        source_limits={'medium': 3, 'arxiv': 3},
        keywords=['AI', 'LLM', 'machine learning'],
        max_age_days=60
    )
    
    try:
        # Collecte
        collector = TechCollectorAgent(demo_config)
        collection_result = await collector.collect_all_sources()
        
        # Analyse
        analyzer = TechAnalyzerAgent()
        analyzed_articles = await analyzer.analyze_contents(collection_result.contents)
        
        # Synthèse
        synthesizer = TechSynthesizerAgent()
        daily_digest = await synthesizer.create_daily_digest(analyzed_articles)
        
        # Sauvegarde
        output_path = await synthesizer.save_digest_to_file(daily_digest)
        
        logger.info(f"✅ Démo terminée - Digest: {output_path}")
        return daily_digest
        
    except Exception as e:
        logger.error(f"❌ Erreur démo: {e}")
        raise


def main():
    """Fonction principale avec gestion des modes."""
    
    # Détection du mode
    demo_mode = "--demo" in sys.argv or "-d" in sys.argv
    
    if demo_mode:
        logger.info("🎬 Lancement en mode DÉMO (collecte réduite)")
        result = asyncio.run(run_quick_demo())
    else:
        logger.info("🎯 Lancement en mode PRODUCTION (collecte complète)")
        result = asyncio.run(create_daily_digest())
    
    if result:
        logger.info("🎉 Traitement terminé avec succès!")
    else:
        logger.error("❌ Échec du traitement")
        sys.exit(1)


if __name__ == "__main__":
    main()
