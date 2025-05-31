"""
Agent Collecteur Tech - Orchestrateur intelligent de collecte multi-sources.

Ce module implémente l'agent central qui orchestre tous les connecteurs
de sources pour la veille technologique, avec déduplication et priorisation.
"""
import asyncio
from typing import List, Dict, Set, Optional, Tuple, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from loguru import logger

from ..connectors import BaseConnector, RawContent, MediumConnector, ArxivConnector


@dataclass
class CollectionConfig:
    """Configuration pour une session de collecte."""
    total_limit: int = 30                    # Limite totale d'articles
    source_limits: Dict[str, int] = field(default_factory=lambda: {
        'medium': 15,
        'arxiv': 15
    })
    keywords: List[str] = field(default_factory=lambda: [
        'AI', 'GenAI', 'LLM', 'GPT', 'LangChain', 'LangGraph', 
        'machine learning', 'deep learning', 'artificial intelligence',
        'neural network', 'transformer', 'agentic', 'multi-agent'
    ])
    max_age_days: int = 7                    # Âge maximum des articles (jours)
    enable_deduplication: bool = True        # Activer la déduplication
    similarity_threshold: float = 0.8        # Seuil de similarité pour déduplication


@dataclass 
class CollectionResult:
    """Résultat d'une session de collecte."""
    contents: List[RawContent]               # Contenus collectés
    total_collected: int                     # Total collecté avant filtrage
    total_filtered: int                      # Total après filtrage
    sources_stats: Dict[str, Dict[str, int]] # Statistiques par source
    duplicates_removed: int                  # Nombre de doublons supprimés
    collection_time: float                   # Temps de collecte (secondes)
    errors: List[str] = field(default_factory=list)  # Erreurs rencontrées


class TechCollectorAgent:
    """
    Agent Collecteur Tech - Orchestrateur intelligent de collecte multi-sources.
    
    Cet agent coordonne la collecte depuis plusieurs sources (Medium, ArXiv, etc.),
    applique des filtres intelligents, déduplique et priorise les contenus
    pour la veille technologique.
    
    Architecture:
    1. Collecte parallèle depuis toutes les sources configurées
    2. Filtrage par mots-clés et âge des articles  
    3. Déduplication intelligente basée sur la similarité
    4. Priorisation par pertinence et récence
    5. Retour d'un ensemble cohérent et de qualité
    """
    
    def __init__(self, config: Optional[CollectionConfig] = None):
        """
        Initialise l'agent collecteur.
        
        Args:
            config: Configuration de collecte (utilise la config par défaut si None)
        """
        self.config = config or CollectionConfig()
        self.logger = logger.bind(component="TechCollectorAgent")
        
        # Initialisation des connecteurs
        self.connectors: Dict[str, BaseConnector] = {}
        self._init_connectors()
        
        # Statistiques de session
        self.session_stats = {
            'total_sessions': 0,
            'total_collected': 0,
            'total_duplicates_removed': 0,
            'sources_availability': {}
        }
    
    def _init_connectors(self) -> None:
        """Initialise tous les connecteurs disponibles."""
        try:
            # Medium Connector
            self.connectors['medium'] = MediumConnector(keywords=self.config.keywords)
            self.logger.info("✅ Medium connector initialisé")
            
            # ArXiv Connector  
            self.connectors['arxiv'] = ArxivConnector(keywords=self.config.keywords)
            self.logger.info("✅ ArXiv connector initialisé")
            
            self.logger.info(f"🔧 {len(self.connectors)} connecteurs initialisés")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur initialisation connecteurs: {e}")
            raise
    
    async def collect_all_sources(self, config: Optional[CollectionConfig] = None) -> CollectionResult:
        """
        Collecte orchestrée depuis toutes les sources disponibles.
        
        Args:
            config: Configuration spécifique pour cette collecte
            
        Returns:
            CollectionResult avec les contenus collectés et les statistiques
        """
        start_time = datetime.now()
        collection_config = config or self.config
        
        self.logger.info("🚀 Début de la collecte orchestrée")
        
        # 1. Vérification de la disponibilité des sources
        available_sources = await self._check_sources_availability()
        
        # 2. Collecte parallèle depuis toutes les sources
        raw_contents, collection_errors = await self._collect_from_all_sources(
            available_sources, collection_config
        )
        
        # 3. Filtrage par âge et qualité
        filtered_contents = self._filter_by_age_and_quality(
            raw_contents, collection_config
        )
        
        # 4. Déduplication intelligente
        deduplicated_contents, duplicates_count = self._deduplicate_contents(
            filtered_contents, collection_config
        )
        
        # 5. Priorisation et limitation finale
        final_contents = self._prioritize_and_limit(
            deduplicated_contents, collection_config
        )
        
        # 6. Calcul des statistiques
        collection_time = (datetime.now() - start_time).total_seconds()
        sources_stats = self._calculate_sources_stats(raw_contents, final_contents)
        
        # 7. Mise à jour des statistiques de session
        self._update_session_stats(len(raw_contents), duplicates_count, available_sources)
        
        result = CollectionResult(
            contents=final_contents,
            total_collected=len(raw_contents),
            total_filtered=len(final_contents),
            sources_stats=sources_stats,
            duplicates_removed=duplicates_count,
            collection_time=collection_time,
            errors=collection_errors
        )
        
        self._log_collection_summary(result)
        return result
    
    def _normalize_datetime(self, dt: Optional[datetime]) -> Optional[datetime]:
        """
        Normalise une datetime pour comparaison (supprime timezone).
        
        Args:
            dt: DateTime à normaliser
            
        Returns:
            DateTime normalisée (naive) ou None
        """
        if dt is None:
            return None
        
        try:
            # Si la date a une timezone, on la supprime
            if dt.tzinfo is not None:
                return dt.replace(tzinfo=None)
            return dt
        except (AttributeError, TypeError):
            return None
    
    async def _check_sources_availability(self) -> List[str]:
        """
        Vérifie quelles sources sont disponibles.
        
        Returns:
            Liste des noms des sources disponibles
        """
        available = []
        
        for source_name, connector in self.connectors.items():
            try:
                if connector.is_available():
                    available.append(source_name)
                    self.logger.info(f"✅ {source_name} disponible")
                else:
                    self.logger.warning(f"⚠️ {source_name} indisponible")
            except Exception as e:
                self.logger.error(f"❌ Erreur vérification {source_name}: {e}")
        
        return available
    
    async def _collect_from_all_sources(
        self, 
        available_sources: List[str], 
        config: CollectionConfig
    ) -> Tuple[List[RawContent], List[str]]:
        """
        Collecte en parallèle depuis toutes les sources disponibles.
        
        Args:
            available_sources: Sources disponibles à interroger
            config: Configuration de collecte
            
        Returns:
            Tuple (contenus collectés, erreurs)
        """
        tasks = []
        errors = []
        
        for source_name in available_sources:
            if source_name in self.connectors:
                limit = config.source_limits.get(source_name, 10)
                task = self._collect_from_source(source_name, limit)
                tasks.append(task)
        
        # Collecte parallèle avec gestion d'erreurs
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_contents = []
        for i, result in enumerate(results):
            source_name = available_sources[i] if i < len(available_sources) else f"source_{i}"
            
            if isinstance(result, Exception):
                error_msg = f"Erreur collecte {source_name}: {result}"
                errors.append(error_msg)
                self.logger.error(error_msg)
            elif isinstance(result, list):
                all_contents.extend(result)
                self.logger.info(f"✅ {source_name}: {len(result)} contenus collectés")
        
        return all_contents, errors
    
    async def _collect_from_source(self, source_name: str, limit: int) -> List[RawContent]:
        """
        Collecte depuis une source spécifique.
        
        Args:
            source_name: Nom de la source
            limit: Limite de contenus à collecter
            
        Returns:
            Liste des contenus collectés
        """
        connector = self.connectors[source_name]
        
        try:
            contents = await connector.collect(limit=limit)
            self.logger.debug(f"{source_name}: {len(contents)} contenus récupérés")
            return contents
            
        except Exception as e:
            self.logger.error(f"Erreur collecte {source_name}: {e}")
            raise
    
    def _filter_by_age_and_quality(
        self, 
        contents: List[RawContent], 
        config: CollectionConfig
    ) -> List[RawContent]:
        """
        Filtre les contenus par âge et qualité.
        
        Args:
            contents: Contenus à filtrer
            config: Configuration de filtrage
            
        Returns:
            Contenus filtrés
        """
        if not contents:
            return []
        
        cutoff_date = datetime.now() - timedelta(days=config.max_age_days)
        filtered = []
        
        for content in contents:
            # Filtre par âge avec gestion des timezones
            if content.published_date:
                try:
                    # Normalisation des dates pour comparaison
                    content_date = self._normalize_datetime(content.published_date)
                    cutoff_date_normalized = self._normalize_datetime(cutoff_date)
                    
                    if content_date and cutoff_date_normalized and content_date < cutoff_date_normalized:
                        continue
                except Exception as e:
                    # En cas d'erreur de date, on garde le contenu par défaut
                    self.logger.warning(f"Erreur comparaison date pour {content.url}: {e}")
            
            # Filtre par qualité basique
            if len(content.title) < 10 or not content.url:
                continue
            
            filtered.append(content)
        
        self.logger.info(f"📅 Filtrage âge/qualité: {len(contents)} → {len(filtered)}")
        return filtered
    
    def _deduplicate_contents(
        self, 
        contents: List[RawContent], 
        config: CollectionConfig
    ) -> Tuple[List[RawContent], int]:
        """
        Déduplique les contenus basé sur la similarité.
        
        Args:
            contents: Contenus à dédupliquer
            config: Configuration de déduplication
            
        Returns:
            Tuple (contenus dédupliqués, nombre de doublons supprimés)
        """
        if not config.enable_deduplication or len(contents) <= 1:
            return contents, 0
        
        deduplicated = []
        seen_urls: Set[str] = set()
        seen_titles: Set[str] = set()
        duplicates_count = 0
        
        for content in contents:
            # Déduplication par URL exacte
            if content.url in seen_urls:
                duplicates_count += 1
                continue
            
            # Déduplication par titre similaire (simple)
            title_lower = content.title.lower().strip()
            if title_lower in seen_titles:
                duplicates_count += 1
                continue
            
            # Déduplication par similarité de titre (basique)
            is_duplicate = False
            for seen_title in seen_titles:
                if self._are_titles_similar(title_lower, seen_title, config.similarity_threshold):
                    duplicates_count += 1
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(content)
                seen_urls.add(content.url)
                seen_titles.add(title_lower)
        
        self.logger.info(f"🔄 Déduplication: {len(contents)} → {len(deduplicated)} (-{duplicates_count} doublons)")
        return deduplicated, duplicates_count
    
    def _are_titles_similar(self, title1: str, title2: str, threshold: float) -> bool:
        """
        Vérifie si deux titres sont similaires (implémentation basique).
        
        Args:
            title1, title2: Titres à comparer
            threshold: Seuil de similarité
            
        Returns:
            True si les titres sont similaires
        """
        # Implémentation simple basée sur les mots communs
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if len(words1) == 0 or len(words2) == 0:
            return False
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0
        return similarity >= threshold
    
    def _prioritize_and_limit(
        self, 
        contents: List[RawContent], 
        config: CollectionConfig
    ) -> List[RawContent]:
        """
        Priorise et limite les contenus finaux.
        
        Args:
            contents: Contenus à prioriser
            config: Configuration de priorisation
            
        Returns:
            Contenus finaux triés et limités
        """
        # Tri par date de publication (plus récent en premier) avec gestion timezone
        def get_sort_key(content: RawContent) -> datetime:
            normalized_date = self._normalize_datetime(content.published_date)
            return normalized_date or datetime.min
        
        sorted_contents = sorted(
            contents,
            key=get_sort_key,
            reverse=True
        )
        
        # Application de la limite totale
        limited_contents = sorted_contents[:config.total_limit]
        
        self.logger.info(f"🎯 Priorisation: {len(contents)} → {len(limited_contents)} contenus finaux")
        return limited_contents
    
    def _calculate_sources_stats(
        self, 
        raw_contents: List[RawContent], 
        final_contents: List[RawContent]
    ) -> Dict[str, Dict[str, int]]:
        """
        Calcule les statistiques par source.
        
        Args:
            raw_contents: Contenus bruts collectés
            final_contents: Contenus finaux après traitement
            
        Returns:
            Statistiques détaillées par source
        """
        stats = {}
        
        # Statistiques contenus bruts
        for content in raw_contents:
            source = content.source
            if source not in stats:
                stats[source] = {'raw': 0, 'final': 0, 'retention_rate': 0.0}
            stats[source]['raw'] += 1
        
        # Statistiques contenus finaux
        for content in final_contents:
            source = content.source
            if source in stats:
                stats[source]['final'] += 1
        
        # Calcul du taux de rétention
        for source in stats:
            raw_count = stats[source]['raw']
            final_count = stats[source]['final']
            stats[source]['retention_rate'] = (final_count / raw_count * 100) if raw_count > 0 else 0.0
        
        return stats
    
    def _update_session_stats(
        self, 
        total_collected: int, 
        duplicates_removed: int, 
        available_sources: List[str]
    ) -> None:
        """Met à jour les statistiques de session."""
        self.session_stats['total_sessions'] += 1
        self.session_stats['total_collected'] += total_collected
        self.session_stats['total_duplicates_removed'] += duplicates_removed
        
        for source in available_sources:
            if source not in self.session_stats['sources_availability']:
                self.session_stats['sources_availability'][source] = 0
            self.session_stats['sources_availability'][source] += 1
    
    def _log_collection_summary(self, result: CollectionResult) -> None:
        """Affiche un résumé de la collecte."""
        self.logger.info("📊 RÉSUMÉ DE COLLECTE")
        self.logger.info(f"   📄 Contenus collectés: {result.total_collected}")
        self.logger.info(f"   ✅ Contenus finaux: {result.total_filtered}")
        self.logger.info(f"   🔄 Doublons supprimés: {result.duplicates_removed}")
        self.logger.info(f"   ⏱️ Temps de collecte: {result.collection_time:.2f}s")
        
        for source, stats in result.sources_stats.items():
            retention = stats['retention_rate']
            self.logger.info(f"   📈 {source}: {stats['raw']}→{stats['final']} ({retention:.1f}%)")
        
        if result.errors:
            self.logger.warning(f"   ⚠️ Erreurs: {len(result.errors)}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques de session.
        
        Returns:
            Dictionnaire des statistiques
        """
        return self.session_stats.copy()
    
    def reset_session_stats(self) -> None:
        """Remet à zéro les statistiques de session."""
        self.session_stats = {
            'total_sessions': 0,
            'total_collected': 0,
            'total_duplicates_removed': 0,
            'sources_availability': {}
        }
        self.logger.info("🔄 Statistiques de session remises à zéro")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Effectue un diagnostic de santé de l'agent.
        
        Returns:
            Rapport de santé détaillé
        """
        health_report = {
            'agent_status': 'healthy',
            'connectors_status': {},
            'config': {
                'total_limit': self.config.total_limit,
                'source_limits': self.config.source_limits,
                'keywords_count': len(self.config.keywords)
            },
            'session_stats': self.get_session_stats()
        }
        
        # Vérification des connecteurs
        for source_name, connector in self.connectors.items():
            try:
                is_available = connector.is_available()
                health_report['connectors_status'][source_name] = {
                    'available': is_available,
                    'status': 'healthy' if is_available else 'unavailable'
                }
            except Exception as e:
                health_report['connectors_status'][source_name] = {
                    'available': False,
                    'status': 'error',
                    'error': str(e)
                }
                health_report['agent_status'] = 'degraded'
        
        return health_report
