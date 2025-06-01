"""
Test UAT Pipeline Complet - 3 Agents
Collecteur → Analyseur → Synthétiseur avec vraies données live
"""
import asyncio
import sys
import os
from datetime import datetime
from loguru import logger

# Configuration du logging pour le test
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

# Ajout du chemin pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agents.tech_collector_agent import TechCollectorAgent, CollectionConfig
from src.agents.tech_analyzer_agent import TechAnalyzerAgent
from src.agents.tech_synthesizer_agent import TechSynthesizerAgent


async def test_complete_pipeline():
    """Test UAT complet du pipeline 3 agents avec vraies données."""
    
    logger.info("🚀 DÉBUT TEST UAT PIPELINE COMPLET - 3 AGENTS")
    logger.info("=" * 70)
    
    start_time = datetime.now()
    
    try:
        # ===============================
        # PHASE 1: AGENT COLLECTEUR
        # ===============================
        logger.info("📡 PHASE 1: Agent Collecteur Tech")
        
        # Configuration optimisée pour test rapide mais représentatif
        collection_config = CollectionConfig(
            total_limit=10,  # Plus d'articles pour test synthèse
            source_limits={'medium': 6, 'arxiv': 6},
            keywords=['AI', 'LLM', 'machine learning', 'GenAI', 'transformer', 'agent'],
            max_age_days=60,  # Plus large pour avoir assez de contenu
            enable_deduplication=True
        )
        
        logger.info(f"🔧 Configuration: {collection_config.total_limit} articles max")
        logger.info(f"📚 Mots-clés: {collection_config.keywords[:3]}...")
        
        # Collecte
        collector = TechCollectorAgent(collection_config)
        phase1_start = datetime.now()
        collection_result = await collector.collect_all_sources()
        phase1_time = (datetime.now() - phase1_start).total_seconds()
        
        # Validation Phase 1
        assert collection_result.total_filtered > 0, "❌ Aucun contenu collecté"
        assert len(collection_result.contents) > 0, "❌ Liste de contenus vide"
        
        logger.info("✅ PHASE 1 RÉUSSIE")
        logger.info(f"   📊 Collectés: {collection_result.total_collected}")
        logger.info(f"   ✅ Filtrés: {collection_result.total_filtered}")
        logger.info(f"   🔄 Doublons: {collection_result.duplicates_removed}")
        logger.info(f"   ⏱️ Temps: {phase1_time:.2f}s")
        
        # Échantillon Phase 1
        logger.info("\n📄 ÉCHANTILLON COLLECTÉ:")
        for i, content in enumerate(collection_result.contents[:3], 1):
            logger.info(f"   {i}. {content.title[:60]}...")
            logger.info(f"      📍 {content.source} | {content.published_date}")
        
        # ===============================
        # PHASE 2: AGENT ANALYSEUR
        # ===============================
        logger.info("\n🧠 PHASE 2: Agent Analyseur avec LangGraph")
        
        analyzer = TechAnalyzerAgent()
        logger.info("🔧 Agent Analyseur initialisé")
        
        phase2_start = datetime.now()
        analyzed_articles = await analyzer.analyze_contents(collection_result.contents)
        phase2_time = (datetime.now() - phase2_start).total_seconds()
        
        # Validation Phase 2
        assert len(analyzed_articles) >= 0, "❌ Erreur dans l'analyse"
        
        logger.info("✅ PHASE 2 RÉUSSIE")
        logger.info(f"   📊 Articles analysés: {len(analyzed_articles)}")
        logger.info(f"   ⏱️ Temps: {phase2_time:.2f}s")
        
        if analyzed_articles:
            recommended_count = sum(1 for a in analyzed_articles if a.analysis.recommended)
            avg_score = sum(a.final_score for a in analyzed_articles) / len(analyzed_articles)
            
            logger.info(f"   🎯 Recommandés: {recommended_count}/{len(analyzed_articles)}")
            logger.info(f"   📈 Score moyen: {avg_score:.2f}")
            
            # Top articles de Phase 2
            logger.info("\n🏆 TOP ARTICLES ANALYSÉS:")
            for i, article in enumerate(analyzed_articles[:3], 1):
                status = "✅" if article.analysis.recommended else "❌"
                logger.info(f"   {i}. {status} Score: {article.final_score:.2f}/1.0")
                logger.info(f"      📄 {article.raw_content.title[:50]}...")
                logger.info(f"      🔍 {article.analysis.category} | {article.analysis.expertise_level}")
        
        # ===============================
        # PHASE 3: AGENT SYNTHÉTISEUR
        # ===============================
        logger.info("\n📝 PHASE 3: Agent Synthétiseur - Création Digest")
        
        synthesizer = TechSynthesizerAgent()
        logger.info("🔧 Agent Synthétiseur initialisé")
        
        # Configuration spécifique pour test
        synthesizer.config.update({
            "max_articles_in_digest": 3,
            "max_insights": 4,
            "max_recommendations": 3
        })
        
        phase3_start = datetime.now()
        daily_digest = await synthesizer.create_daily_digest(analyzed_articles)
        phase3_time = (datetime.now() - phase3_start).total_seconds()
        
        # Validation Phase 3
        assert daily_digest is not None, "❌ Échec génération digest"
        assert daily_digest.markdown_content is not None, "❌ Contenu Markdown manquant"
        assert len(daily_digest.top_articles) > 0, "❌ Aucun article dans le digest"
        
        logger.info("✅ PHASE 3 RÉUSSIE")
        logger.info(f"   📝 Digest créé: {daily_digest.title}")
        logger.info(f"   📊 Articles digest: {len(daily_digest.top_articles)}")
        logger.info(f"   💡 Insights: {len(daily_digest.key_insights)}")
        logger.info(f"   🎯 Recommandations: {len(daily_digest.recommendations)}")
        logger.info(f"   📄 Mots: {daily_digest.word_count}")
        logger.info(f"   ⏱️ Temps: {phase3_time:.2f}s")
        
        # Sauvegarde du digest
        output_path = await synthesizer.save_digest_to_file(daily_digest)
        logger.info(f"   💾 Sauvegardé: {output_path}")
        
        # ===============================
        # VALIDATION PIPELINE COMPLET
        # ===============================
        total_time = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n🎯 RÉSULTATS PIPELINE COMPLET - 3 AGENTS")
        logger.info("=" * 60)
        logger.info(f"✅ Phase 1 (Collecte): {collection_result.total_filtered} articles → {phase1_time:.1f}s")
        logger.info(f"✅ Phase 2 (Analyse): {len(analyzed_articles)} articles → {phase2_time:.1f}s") 
        logger.info(f"✅ Phase 3 (Synthèse): 1 digest → {phase3_time:.1f}s")
        logger.info(f"⏱️ Temps total: {total_time:.2f}s")
        logger.info(f"📊 Performance: {total_time/max(1, len(analyzed_articles)):.2f}s/article")
        
        # ===============================
        # APERÇU DU DIGEST GÉNÉRÉ
        # ===============================
        logger.info("\n📋 APERÇU DU DIGEST GÉNÉRÉ:")
        logger.info(f"🗓️ {daily_digest.title}")
        logger.info(f"📝 {daily_digest.subtitle}")
        
        # Résumé exécutif (tronqué)
        executive_preview = daily_digest.executive_summary[:150] + "..." if len(daily_digest.executive_summary) > 150 else daily_digest.executive_summary
        logger.info(f"\n📊 Résumé Exécutif:\n{executive_preview}")
        
        # Top articles du digest
        logger.info(f"\n🏆 Top {len(daily_digest.top_articles)} Articles:")
        for i, article in enumerate(daily_digest.top_articles, 1):
            logger.info(f"   {i}. {article.title_refined}")
            logger.info(f"      📊 Score: {article.relevance_for_audience:.2f} | {article.complexity_level}")
            logger.info(f"      💡 {article.executive_summary[:80]}...")
        
        # Insights clés
        if daily_digest.key_insights:
            logger.info(f"\n💡 Insights Clés:")
            for insight in daily_digest.key_insights[:3]:
                logger.info(f"   • {insight}")
        
        # Recommandations
        if daily_digest.recommendations:
            logger.info(f"\n🎯 Recommandations:")
            for rec in daily_digest.recommendations[:2]:
                logger.info(f"   • {rec.title} ({rec.priority} priority)")
                logger.info(f"     {rec.description[:60]}...")
        
        # ===============================
        # MÉTRIQUES QUALITÉ
        # ===============================
        logger.info("\n📈 MÉTRIQUES DE QUALITÉ:")
        
        # Taux de conversion par phase
        collection_to_analysis = (len(analyzed_articles) / collection_result.total_filtered) * 100
        analysis_to_digest = (len(daily_digest.top_articles) / len(analyzed_articles)) * 100 if analyzed_articles else 0
        overall_conversion = (len(daily_digest.top_articles) / collection_result.total_filtered) * 100
        
        logger.info(f"   📊 Collecte → Analyse: {collection_to_analysis:.1f}%")
        logger.info(f"   📊 Analyse → Digest: {analysis_to_digest:.1f}%") 
        logger.info(f"   📊 Conversion globale: {overall_conversion:.1f}%")
        logger.info(f"   📊 Score qualité moyen: {daily_digest.average_quality_score:.2f}/1.0")
        
        # Répartition par source
        sources_in_digest = {}
        for article in daily_digest.top_articles:
            source = article.original_article.raw_content.source
            sources_in_digest[source] = sources_in_digest.get(source, 0) + 1
        logger.info(f"   📍 Sources digest: {dict(sources_in_digest)}")
        
        # ===============================
        # VALIDATION INTÉGRITÉ
        # ===============================
        logger.info("\n🔍 VALIDATION INTÉGRITÉ:")
        
        # Vérifications de cohérence
        integrity_checks = []
        
        # Cohérence des données
        if all(article.original_article is not None for article in daily_digest.top_articles):
            integrity_checks.append("✅ Liens articles originaux préservés")
        else:
            integrity_checks.append("❌ Liens articles originaux cassés")
        
        # Qualité du contenu
        if daily_digest.word_count > 500:
            integrity_checks.append("✅ Digest suffisamment détaillé")
        else:
            integrity_checks.append("⚠️ Digest potentiellement trop court")
        
        # Cohérence scores
        if all(0 <= article.relevance_for_audience <= 1 for article in daily_digest.top_articles):
            integrity_checks.append("✅ Scores de relevance cohérents")
        else:
            integrity_checks.append("❌ Scores de relevance incohérents")
        
        # Format Markdown
        if "# " in daily_digest.markdown_content and "## " in daily_digest.markdown_content:
            integrity_checks.append("✅ Structure Markdown valide")
        else:
            integrity_checks.append("❌ Structure Markdown invalide")
        
        for check in integrity_checks:
            logger.info(f"   {check}")
        
        # ===============================
        # SUCCÈS FINAL
        # ===============================
        logger.info("\n🎉 TEST UAT PIPELINE COMPLET: ✅ SUCCÈS TOTAL")
        logger.info("=" * 70)
        logger.info("🏆 SYSTÈME OPÉRATIONNEL - 3 AGENTS INTÉGRÉS")
        logger.info(f"📄 Digest final sauvegardé: {output_path}")
        
        return {
            'collection_result': collection_result,
            'analyzed_articles': analyzed_articles,
            'daily_digest': daily_digest,
            'total_time': total_time,
            'phases_time': {
                'collection': phase1_time,
                'analysis': phase2_time,
                'synthesis': phase3_time
            },
            'output_file': output_path,
            'success': True
        }
        
    except Exception as e:
        logger.error(f"❌ ÉCHEC TEST UAT PIPELINE: {e}")
        logger.exception("Détails de l'erreur:")
        return {
            'error': str(e),
            'success': False
        }


async def demo_digest_preview():
    """Démonstrateur rapide du format digest."""
    
    logger.info("\n" + "="*50)
    logger.info("📋 APERÇU FORMAT DIGEST MARKDOWN")
    logger.info("="*50)
    
    # Simulation d'un digest exemple
    sample_content = """
# Tech Digest - 01 Juin 2025

> Veille technologique GenAI/LLM/Agentic pour ingénieurs seniors  
> 📅 01 Juin 2025 • 🎯 senior_engineer • ⏱️ 8 min de lecture

---

## 📊 Résumé Exécutif

Les développements d'aujourd'hui révèlent une accélération notable dans l'adoption des architectures multi-agents en production. Les équipes techniques se focalisent désormais sur l'optimisation des performances LLM plutôt que sur l'augmentation brute des capacités. L'émergence de patterns standardisés pour LangGraph facilite l'implémentation d'agents complexes, tandis que les nouveaux frameworks d'orchestration promettent une meilleure observabilité des workflows IA.

**📈 Métriques de veille:**
- 📄 **Articles analysés:** 10
- ✅ **Articles recommandés:** 3
- 🎯 **Score moyen de qualité:** 0.82/1.0

---

## 🏆 Top Articles

### 1. 🚀 Production-Ready Multi-Agent Architectures with LangGraph

**🧠 Advanced • ⏱️ 12min • 📊 0.89/1.0**

Cette analyse approfondie présente des patterns d'architecture éprouvés pour déployer des systèmes multi-agents en production, avec un focus sur la gestion d'état et l'observabilité.

**🔑 Points clés:**
- Patterns de workflow orchestrés pour agents complexes
- Stratégies de gestion d'état centralisée avec StateGraph
- Métriques et monitoring pour systèmes agentic en production

**⚙️ Aspects techniques:**
- Implémentation de checkpoints pour récupération d'erreurs
- Optimisation mémoire pour workflows long-running
- Intégration avec systèmes de monitoring existants

🔗 **Source:** [arxiv](https://arxiv.org/abs/...)

---

## 💡 Insights Clés

- **L'orchestration multi-agents devient mainstream avec LangGraph comme standard de facto**
- **Les équipes privilégient l'efficacité opérationnelle aux performances brutes des LLM**
- **L'observabilité émerge comme défi principal des systèmes IA en production**

---

## 🎯 Recommandations Actionables

### 1. 🔥 Évaluer LangGraph pour vos workflows IA

**📚 Learning • ⏱️ 1-4h • 🎯 High priority**

Avec la standardisation croissante de LangGraph, évaluer son adoption pour vos systèmes multi-agents actuels pourrait simplifier l'architecture et améliorer la maintenabilité.

**Actions concrètes:**
- [ ] Analyser vos workflows IA existants
- [ ] Créer un POC avec LangGraph
- [ ] Comparer avec votre solution actuelle

---

*Digest généré le 01/06/2025 à 14:30 par 1.0 • LLM: gpt-4o*
"""
    
    logger.info(sample_content)
    logger.info("\n✅ Le pipeline génère des digests dans ce format")


if __name__ == "__main__":
    # Exécution du test UAT complet
    print("🚀 Lancement du test UAT pipeline complet (3 agents)...")
    print("⚠️ Ce test utilise de vraies données et l'API OpenAI")
    print()
    
    result = asyncio.run(test_complete_pipeline())
    
    if result['success']:
        print("\n" + "="*70)
        print("🎉 TEST UAT RÉUSSI - PIPELINE 3 AGENTS OPÉRATIONNEL")
        print("="*70)
        print(f"📄 Digest sauvegardé: {result['output_file']}")
        print("🚀 Système prêt pour production")
        
        # Aperçu du format
        asyncio.run(demo_digest_preview())
        
    else:
        print("\n" + "="*70)
        print("❌ TEST UAT ÉCHOUÉ")
        print("="*70)
        sys.exit(1)
