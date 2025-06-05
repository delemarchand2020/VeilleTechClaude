"""
Service d'intégration de la base de données enrichie dans le workflow principal.

Ce service fait le pont entre les agents existants et la nouvelle base de données
avec fonctionnalités avancées de déduplication, cache et historique.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from loguru import logger

# Imports des modèles et agents existants
from ..models.database_enhanced import (
    DatabaseManagerEnhanced, 
    PerformanceMetrics, 
    DeduplicationResult,
    CacheHit
)
from ..models.analysis_models import AnalyzedContent, ContentAnalysis
from ..models.synthesis_models import DailyDigest
from ..connectors.base_connector import RawContent
from ..agents.tech_collector_agent import CollectionResult


class VeilleIntegrationService:
    """Service d'intégration pour la veille avec BD enrichie."""
    
    def __init__(self, db_path: str = None):
        """Initialise le service avec la base de données enrichie."""
        self.db = DatabaseManagerEnhanced(db_path)
        self.collection_start_time = None
        self.analysis_start_time = None
        self.synthesis_start_time = None
        
        # Statistiques de session
        self.session_stats = {
            'articles_processed': 0,
            'duplicates_found': 0,
            'cache_hits': 0,
            'new_articles': 0,
            'analysis_time_saved': 0.0
        }
        
        logger.info("🗄️ Service d'intégration BD enrichie initialisé")
    
    # ==========================================
    # INTÉGRATION COLLECTE AVEC DÉDUPLICATION
    # ==========================================
    
    async def process_collection_with_deduplication(self, 
                                                   collection_result: CollectionResult) -> Dict[str, Any]:
        """
        Traite le résultat de collecte avec déduplication intelligente.
        
        Returns:
            Dict avec les contenus filtrés et les statistiques de déduplication
        """
        logger.info("🔍 Démarrage déduplication intelligente...")
        self.collection_start_time = datetime.now()
        
        unique_contents = []
        duplicates_info = []
        
        for raw_content in collection_result.contents:
            # Vérification de déduplication
            dedup_result = self.db.check_article_duplication(raw_content)
            
            if dedup_result.is_duplicate:
                duplicates_info.append({
                    'url': raw_content.url,
                    'title': raw_content.title,
                    'duplicate_type': dedup_result.duplicate_type,
                    'similarity_score': dedup_result.similarity_score,
                    'existing_id': dedup_result.existing_id
                })
                self.session_stats['duplicates_found'] += 1
                logger.debug(f"🔄 Doublon détecté ({dedup_result.duplicate_type}): {raw_content.title}")
            else:
                # Sauvegarde du nouvel article
                article_id, was_new = self.db.save_article_with_deduplication(raw_content)
                if was_new:
                    unique_contents.append(raw_content)
                    self.session_stats['new_articles'] += 1
                    logger.debug(f"✅ Nouvel article sauvegardé: {raw_content.title}")
        
        # Statistiques de déduplication
        dedup_stats = {
            'total_collected': len(collection_result.contents),
            'unique_articles': len(unique_contents),
            'duplicates_removed': len(duplicates_info),
            'duplication_rate': len(duplicates_info) / len(collection_result.contents) if collection_result.contents else 0,
            'duplicates_by_type': {}
        }
        
        # Comptage par type de doublon
        for dup in duplicates_info:
            dup_type = dup['duplicate_type']
            dedup_stats['duplicates_by_type'][dup_type] = dedup_stats['duplicates_by_type'].get(dup_type, 0) + 1
        
        logger.info(f"✅ Déduplication terminée:")
        logger.info(f"   📊 {dedup_stats['total_collected']} articles collectés")
        logger.info(f"   🆕 {dedup_stats['unique_articles']} articles uniques")
        logger.info(f"   🔄 {dedup_stats['duplicates_removed']} doublons supprimés")
        logger.info(f"   📈 Taux de déduplication: {dedup_stats['duplication_rate']:.1%}")
        
        return {
            'unique_contents': unique_contents,
            'duplicates_info': duplicates_info,
            'deduplication_stats': dedup_stats,
            'original_collection_result': collection_result
        }
    
    # ==========================================
    # INTÉGRATION ANALYSE AVEC CACHE
    # ==========================================
    
    async def process_analysis_with_cache(self, 
                                        contents: List[RawContent],
                                        analyzer_func,
                                        cache_max_age_hours: int = 24) -> List[AnalyzedContent]:
        """
        Traite l'analyse avec cache intelligent.
        
        Args:
            contents: Liste des contenus à analyser
            analyzer_func: Fonction d'analyse (from TechAnalyzerAgent)
            cache_max_age_hours: Âge maximum du cache en heures
        """
        logger.info("🧠 Démarrage analyse avec cache intelligent...")
        self.analysis_start_time = datetime.now()
        
        analyzed_contents = []
        cache_hits = 0
        new_analyses = 0
        
        for raw_content in contents:
            # Vérification du cache
            cache_result = self.db.check_analysis_cache(raw_content, cache_max_age_hours)
            
            if cache_result.found:
                # Cache hit - récupération de l'analyse existante
                logger.debug(f"💾 Cache hit pour: {raw_content.title}")
                
                # Reconstruction de l'objet AnalyzedContent depuis le cache
                # Note: Ici on devrait adapter selon la structure exacte de ContentAnalysis
                try:
                    # Reconstruction simplifiée - à adapter selon les modèles
                    cached_analysis = ContentAnalysis(**cache_result.analysis)
                    analyzed_content = AnalyzedContent(
                        raw_content=raw_content,
                        analysis=cached_analysis,
                        analyzed_at=datetime.now()  # Ou garder la date du cache
                    )
                    analyzed_contents.append(analyzed_content)
                    cache_hits += 1
                    self.session_stats['cache_hits'] += 1
                    
                    # Estimation du temps économisé (moyenne ~30s par analyse)
                    self.session_stats['analysis_time_saved'] += 30.0
                    
                except Exception as e:
                    logger.warning(f"⚠️ Cache corrompu pour {raw_content.title}: {e}")
                    # En cas d'erreur de cache, faire l'analyse normale
                    cache_result.found = False
            
            if not cache_result.found:
                # Cache miss - analyse nécessaire
                logger.debug(f"🔄 Analyse nécessaire pour: {raw_content.title}")
                
                analysis_start = datetime.now()
                
                # Appel de la fonction d'analyse (celle de TechAnalyzerAgent)
                analyzed_content = await analyzer_func(raw_content)
                
                analysis_time = (datetime.now() - analysis_start).total_seconds()
                
                # Sauvegarde de l'analyse complète en BD
                self.db.save_analyzed_content(analyzed_content, analysis_time)
                
                analyzed_contents.append(analyzed_content)
                new_analyses += 1
        
        # Statistiques de cache
        total_processed = len(contents)
        cache_hit_rate = cache_hits / total_processed if total_processed > 0 else 0
        
        logger.info(f"✅ Analyse avec cache terminée:")
        logger.info(f"   📊 {total_processed} articles traités")
        logger.info(f"   💾 {cache_hits} cache hits ({cache_hit_rate:.1%})")
        logger.info(f"   🆕 {new_analyses} nouvelles analyses")
        if self.session_stats['analysis_time_saved'] > 0:
            logger.info(f"   ⏱️ Temps économisé: {self.session_stats['analysis_time_saved']:.1f}s")
        
        return analyzed_contents
    
    # ==========================================
    # INTÉGRATION SYNTHÈSE AVEC HISTORIQUE
    # ==========================================
    
    async def process_synthesis_with_history(self, 
                                           analyzed_contents: List[AnalyzedContent],
                                           synthesizer_func,
                                           config_snapshot: Dict = None) -> Dict[str, Any]:
        """
        Traite la synthèse avec sauvegarde de l'historique.
        
        Args:
            analyzed_contents: Articles analysés
            synthesizer_func: Fonction de synthèse
            config_snapshot: Configuration utilisée pour cette exécution
        """
        logger.info("📝 Démarrage synthèse avec historique...")
        self.synthesis_start_time = datetime.now()
        
        # Appel de la fonction de synthèse
        daily_digest = await synthesizer_func(analyzed_contents)
        
        synthesis_time = (datetime.now() - self.synthesis_start_time).total_seconds()
        
        # Sauvegarde du digest en BD avec historique
        digest_id = self.db.save_digest(daily_digest, config_snapshot)
        
        logger.info(f"✅ Synthèse avec historique terminée:")
        logger.info(f"   📋 Digest sauvegardé (ID: {digest_id})")
        logger.info(f"   ⏱️ Temps de synthèse: {synthesis_time:.2f}s")
        
        return {
            'daily_digest': daily_digest,
            'digest_id': digest_id,
            'synthesis_time': synthesis_time
        }
    
    # ==========================================
    # MÉTRIQUES ET PERFORMANCE
    # ==========================================
    
    def save_session_metrics(self, 
                           collection_result: CollectionResult,
                           analyzed_contents: List[AnalyzedContent],
                           daily_digest: DailyDigest) -> int:
        """Sauvegarde les métriques de performance de la session."""
        
        if not self.collection_start_time or not self.analysis_start_time or not self.synthesis_start_time:
            logger.warning("⚠️ Impossible de calculer les métriques - timestamps manquants")
            return None
        
        total_time = (datetime.now() - self.collection_start_time).total_seconds()
        analysis_time = (self.synthesis_start_time - self.analysis_start_time).total_seconds()
        
        # Calcul des temps par phase
        collection_time = (self.analysis_start_time - self.collection_start_time).total_seconds()
        synthesis_time = (datetime.now() - self.synthesis_start_time).total_seconds()
        
        # Calcul des scores moyens
        quality_scores = [ac.analysis.relevance_score for ac in analyzed_contents if hasattr(ac.analysis, 'relevance_score')]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        
        # Cache hit rate
        cache_hit_rate = self.session_stats['cache_hits'] / len(analyzed_contents) if analyzed_contents else 0.0
        
        # Duplication rate (depuis session stats)
        duplication_rate = self.session_stats['duplicates_found'] / self.session_stats['articles_processed'] if self.session_stats['articles_processed'] > 0 else 0.0
        
        metrics = PerformanceMetrics(
            date=datetime.now(),
            collection_time=collection_time,
            analysis_time=analysis_time,
            synthesis_time=synthesis_time,
            total_time=total_time,
            articles_collected=collection_result.total_collected,
            articles_analyzed=len(analyzed_contents),
            articles_in_digest=len(daily_digest.top_articles),
            cache_hit_rate=cache_hit_rate,
            duplication_rate=duplication_rate,
            average_quality_score=avg_quality
        )
        
        metrics_id = self.db.save_performance_metrics(metrics)
        
        logger.info(f"📊 Métriques de session sauvegardées (ID: {metrics_id})")
        logger.info(f"   ⏱️ Temps total: {total_time:.2f}s")
        logger.info(f"   💾 Cache hit rate: {cache_hit_rate:.1%}")
        logger.info(f"   🔄 Duplication rate: {duplication_rate:.1%}")
        logger.info(f"   📈 Score qualité moyen: {avg_quality:.2f}")
        
        return metrics_id
    
    # ==========================================
    # STATISTIQUES ET REPORTING
    # ==========================================
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """Récupère les statistiques d'intégration."""
        
        # Statistiques de déduplication (7 derniers jours)
        dedup_stats = self.db.get_duplicate_stats(days=7)
        
        # Statistiques de cache
        cache_stats = self.db.get_cache_stats()
        
        # Performance historique (30 derniers jours)
        historical_metrics = self.db.get_historical_performance(days=30)
        
        return {
            'session_stats': self.session_stats,
            'deduplication_stats': dedup_stats,
            'cache_stats': cache_stats,
            'historical_performance': {
                'metrics_count': len(historical_metrics),
                'avg_total_time': sum(m.total_time for m in historical_metrics) / len(historical_metrics) if historical_metrics else 0,
                'avg_cache_hit_rate': sum(m.cache_hit_rate for m in historical_metrics) / len(historical_metrics) if historical_metrics else 0,
                'avg_quality_score': sum(m.average_quality_score for m in historical_metrics) / len(historical_metrics) if historical_metrics else 0
            }
        }
    
    def cleanup_old_data(self, cache_days: int = 30) -> Dict[str, int]:
        """Nettoie les anciennes données."""
        logger.info(f"🧹 Nettoyage des données anciennes (>{cache_days} jours)...")
        
        # Nettoyage du cache
        deleted_cache = self.db.cleanup_old_cache(cache_days)
        
        logger.info(f"✅ Nettoyage terminé:")
        logger.info(f"   🗑️ {deleted_cache} entrées de cache supprimées")
        
        return {
            'deleted_cache_entries': deleted_cache
        }
    
    def print_daily_summary(self):
        """Affiche un résumé quotidien des opérations."""
        stats = self.get_integration_stats()
        
        logger.info("\n📊 RÉSUMÉ QUOTIDIEN - BASE DE DONNÉES ENRICHIE")
        logger.info("=" * 60)
        
        # Session actuelle
        session = stats['session_stats']
        logger.info(f"📋 Session actuelle:")
        logger.info(f"   🆕 Articles nouveaux: {session['new_articles']}")
        logger.info(f"   🔄 Doublons évités: {session['duplicates_found']}")
        logger.info(f"   💾 Cache hits: {session['cache_hits']}")
        logger.info(f"   ⏱️ Temps économisé: {session['analysis_time_saved']:.1f}s")
        
        # Déduplication
        dedup = stats['deduplication_stats']
        logger.info(f"\n🔍 Déduplication (7 derniers jours):")
        logger.info(f"   📊 Total traité: {dedup['total_processed']}")
        logger.info(f"   🎯 Taux déduplication URL: {dedup['url_duplication_rate']:.1%}")
        logger.info(f"   📄 Taux déduplication contenu: {dedup['content_duplication_rate']:.1%}")
        
        # Cache
        cache = stats['cache_stats']
        logger.info(f"\n💾 Cache d'analyses:")
        logger.info(f"   📁 Entrées valides: {cache['valid_entries']}/{cache['total_entries']}")
        logger.info(f"   🎯 Efficacité cache: {cache['cache_efficiency']:.1%}")
        logger.info(f"   🔄 Hits totaux: {cache['total_cache_hits']}")
        
        # Performance historique
        perf = stats['historical_performance']
        if perf['metrics_count'] > 0:
            logger.info(f"\n📈 Performance historique (30 jours):")
            logger.info(f"   ⏱️ Temps moyen: {perf['avg_total_time']:.1f}s")
            logger.info(f"   💾 Cache hit rate moyen: {perf['avg_cache_hit_rate']:.1%}")
            logger.info(f"   📊 Score qualité moyen: {perf['avg_quality_score']:.2f}")
        
        logger.info("=" * 60)
