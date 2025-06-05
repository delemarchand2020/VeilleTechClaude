"""
Base de données enrichie pour l'Agent de Veille Intelligente - Phase 3

Fonctionnalités avancées :
- Historique complet des articles et analyses
- Déduplication intelligente avec hash de contenu
- Cache des analyses pour éviter les re-traitements
- Métriques et suivi des performances
- Gestion des rapports générés
"""
import sqlite3
import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path

# Imports des modèles existants
from .analysis_models import AnalyzedContent, ContentAnalysis
from .synthesis_models import DailyDigest, ArticleSynthesis
from ..connectors.base_connector import RawContent


@dataclass
class DeduplicationResult:
    """Résultat de la déduplication."""
    is_duplicate: bool
    existing_id: Optional[int] = None
    similarity_score: float = 0.0
    duplicate_type: str = "none"  # "exact", "url", "content", "title"


@dataclass
class CacheHit:
    """Résultat de recherche dans le cache d'analyse."""
    found: bool
    analysis: Optional[ContentAnalysis] = None
    cache_age_hours: float = 0.0
    cache_id: int = None


@dataclass
class PerformanceMetrics:
    """Métriques de performance du système."""
    date: datetime
    collection_time: float
    analysis_time: float
    synthesis_time: float
    total_time: float
    articles_collected: int
    articles_analyzed: int
    articles_in_digest: int
    cache_hit_rate: float
    duplication_rate: float
    average_quality_score: float


class DatabaseManagerEnhanced:
    """Gestionnaire de base de données enrichi pour la Phase 3."""
    
    def __init__(self, db_path: str = None):
        """Initialise la base de données enrichie."""
        if db_path is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = data_dir / "veille_enhanced.db"
        
        self.db_path = str(db_path)
        self.init_enhanced_database()
    
    def init_enhanced_database(self):
        """Initialise les tables enrichies."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table articles enrichie avec hash de déduplication
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    content TEXT,
                    summary TEXT,
                    published_date TIMESTAMP,
                    collected_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    keywords TEXT,  -- JSON array
                    raw_data TEXT,  -- JSON object
                    
                    -- Nouveaux champs pour déduplication
                    url_hash TEXT NOT NULL,        -- Hash de l'URL
                    content_hash TEXT,             -- Hash du contenu pour détecter les doublons
                    title_normalized TEXT,         -- Titre normalisé pour comparaison
                    
                    -- Métadonnées enrichies
                    word_count INTEGER DEFAULT 0,
                    language TEXT DEFAULT 'en',
                    processing_version TEXT DEFAULT '3.0',
                    
                    -- Index pour déduplication
                    UNIQUE(url_hash)
                )
            ''')
            
            # Table analyses enrichie avec cache
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER NOT NULL,
                    
                    -- Résultats d'analyse (JSON pour flexibilité)
                    analysis_result TEXT NOT NULL,  -- ContentAnalysis sérialisé
                    
                    -- Métadonnées du cache
                    content_hash TEXT NOT NULL,     -- Hash pour invalidation cache
                    analysis_version TEXT DEFAULT '3.0',
                    analyzed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    analysis_time_seconds REAL,
                    llm_model_used TEXT,
                    
                    -- Performance
                    token_count INTEGER,
                    cost_estimate REAL,
                    
                    FOREIGN KEY (article_id) REFERENCES articles (id)
                )
            ''')
            
            # Table digests pour historique des rapports
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS digests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    title TEXT NOT NULL,
                    
                    -- Contenu du digest
                    digest_data TEXT NOT NULL,      -- DailyDigest sérialisé
                    markdown_content TEXT,
                    
                    -- Articles inclus
                    included_articles TEXT,         -- JSON array des IDs
                    
                    -- Métadonnées
                    target_audience TEXT,
                    word_count INTEGER,
                    estimated_read_time INTEGER,
                    
                    -- Performance de génération
                    generation_time REAL,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Version et configuration
                    generator_version TEXT DEFAULT '3.0',
                    config_snapshot TEXT,           -- Configuration utilisée
                    
                    UNIQUE(date)
                )
            ''')
            
            # Table métriques pour suivi des performances
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    
                    -- Temps d'exécution
                    collection_time REAL NOT NULL,
                    analysis_time REAL NOT NULL,
                    synthesis_time REAL NOT NULL,
                    total_time REAL NOT NULL,
                    
                    -- Volumes traités
                    articles_collected INTEGER NOT NULL,
                    articles_analyzed INTEGER NOT NULL,
                    articles_in_digest INTEGER NOT NULL,
                    
                    -- Efficacité
                    cache_hit_rate REAL DEFAULT 0.0,
                    duplication_rate REAL DEFAULT 0.0,
                    average_quality_score REAL DEFAULT 0.0,
                    
                    -- Coûts
                    estimated_cost REAL DEFAULT 0.0,
                    token_usage INTEGER DEFAULT 0,
                    
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE(date)
                )
            ''')
            
            # Table cache des analyses (table séparée pour optimisation)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_hash TEXT NOT NULL UNIQUE,
                    analysis_result TEXT NOT NULL,
                    
                    -- Métadonnées du cache
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    use_count INTEGER DEFAULT 1,
                    cache_version TEXT DEFAULT '3.0',
                    
                    -- TTL et invalidation
                    expires_at TIMESTAMP,
                    is_valid BOOLEAN DEFAULT 1
                )
            ''')
            
            # Création des index séparément
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_content_hash ON articles(content_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_title_normalized ON articles(title_normalized)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_collected_date ON articles(collected_date)')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analyses_content_hash ON analyses(content_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_analyses_date ON analyses(analyzed_date)')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_digests_created_date ON digests(created_date)')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_created_date ON performance_metrics(created_date)')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_content_hash ON analysis_cache(content_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_expires_at ON analysis_cache(expires_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_last_used ON analysis_cache(last_used)')
            
            conn.commit()
    
    # ==========================================
    # FONCTIONS DE DÉDUPLICATION INTELLIGENTE
    # ==========================================
    
    def _generate_content_hash(self, content: str) -> str:
        """Génère un hash unique du contenu pour déduplication."""
        # Normalisation du contenu avant hashing
        normalized = content.lower().strip()
        # Suppression des espaces multiples et caractères spéciaux
        import re
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def _generate_url_hash(self, url: str) -> str:
        """Génère un hash de l'URL."""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _serialize_for_json(self, obj_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Sérialise un dictionnaire en convertissant les Enum et datetime en strings."""
        serialized = {}
        for key, value in obj_dict.items():
            if hasattr(value, 'value'):  # C'est un Enum
                serialized[key] = value.value
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = self._serialize_for_json(value)
            elif isinstance(value, list):
                serialized[key] = [self._serialize_for_json(item) if isinstance(item, dict) else 
                                 item.value if hasattr(item, 'value') else 
                                 item.isoformat() if isinstance(item, datetime) else item for item in value]
            else:
                serialized[key] = value
        return serialized
    
    def _normalize_title(self, title: str) -> str:
        """Normalise un titre pour comparaison."""
        import re
        # Suppression des caractères spéciaux et normalisation
        normalized = title.lower().strip()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
    
    def check_article_duplication(self, raw_content: RawContent) -> DeduplicationResult:
        """Vérifie si un article est un doublon."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            url_hash = self._generate_url_hash(raw_content.url)
            content_hash = self._generate_content_hash(raw_content.content)
            title_normalized = self._normalize_title(raw_content.title)
            
            # Vérification par URL (doublon exact)
            cursor.execute('SELECT id FROM articles WHERE url_hash = ?', (url_hash,))
            result = cursor.fetchone()
            if result:
                return DeduplicationResult(
                    is_duplicate=True,
                    existing_id=result[0],
                    similarity_score=1.0,
                    duplicate_type="url"
                )
            
            # Vérification par contenu (même contenu, URL différente)
            cursor.execute('SELECT id FROM articles WHERE content_hash = ?', (content_hash,))
            result = cursor.fetchone()
            if result:
                return DeduplicationResult(
                    is_duplicate=True,
                    existing_id=result[0],
                    similarity_score=0.95,
                    duplicate_type="content"
                )
            
            # Vérification par titre normalisé (articles similaires)
            cursor.execute('SELECT id, title FROM articles WHERE title_normalized = ?', (title_normalized,))
            result = cursor.fetchone()
            if result:
                return DeduplicationResult(
                    is_duplicate=True,
                    existing_id=result[0],
                    similarity_score=0.8,
                    duplicate_type="title"
                )
            
            return DeduplicationResult(is_duplicate=False)
    
    def save_article_with_deduplication(self, raw_content: RawContent) -> Tuple[int, bool]:
        """
        Sauvegarde un article avec vérification de déduplication.
        
        Returns:
            Tuple[int, bool]: (article_id, was_new)
        """
        # Vérification de déduplication
        dedup_result = self.check_article_duplication(raw_content)
        
        if dedup_result.is_duplicate:
            return dedup_result.existing_id, False
        
        # Sauvegarde du nouvel article
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            url_hash = self._generate_url_hash(raw_content.url)
            content_hash = self._generate_content_hash(raw_content.content)
            title_normalized = self._normalize_title(raw_content.title)
            word_count = len(raw_content.content.split()) if raw_content.content else 0
            
            cursor.execute('''
                INSERT INTO articles (
                    title, url, source, content, summary, published_date,
                    keywords, raw_data, url_hash, content_hash, title_normalized, word_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                raw_content.title,
                raw_content.url,
                raw_content.source,
                raw_content.content,
                raw_content.excerpt,  # Utiliser excerpt au lieu de summary
                raw_content.published_date,
                json.dumps(raw_content.tags) if raw_content.tags else "[]",  # Utiliser tags au lieu de keywords
                json.dumps(raw_content.raw_data) if raw_content.raw_data else "{}",
                url_hash,
                content_hash,
                title_normalized,
                word_count
            ))
            
            return cursor.lastrowid, True
    
    # ==========================================
    # CACHE DES ANALYSES
    # ==========================================
    
    def check_analysis_cache(self, raw_content: RawContent, max_age_hours: int = 24) -> CacheHit:
        """Vérifie si une analyse est en cache."""
        content_hash = self._generate_content_hash(raw_content.content)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Recherche dans le cache avec vérification TTL
            cursor.execute('''
                SELECT id, analysis_result, created_date, use_count 
                FROM analysis_cache 
                WHERE content_hash = ? AND is_valid = 1 AND expires_at > ?
            ''', (content_hash, datetime.now()))
            
            result = cursor.fetchone()
            if not result:
                return CacheHit(found=False)
            
            cache_id, analysis_json, created_date, use_count = result
            created_dt = datetime.fromisoformat(created_date)
            age_hours = (datetime.now() - created_dt).total_seconds() / 3600
            
            # Vérification de l'âge maximum
            if age_hours > max_age_hours:
                return CacheHit(found=False)
            
            # Désérialisation de l'analyse
            try:
                analysis_data = json.loads(analysis_json)
                # Ici on devrait recréer l'objet ContentAnalysis
                # Pour l'instant, on retourne les données brutes
                
                # Mise à jour des statistiques d'usage
                cursor.execute('''
                    UPDATE analysis_cache 
                    SET use_count = use_count + 1, last_used = ? 
                    WHERE id = ?
                ''', (datetime.now(), cache_id))
                conn.commit()
                
                return CacheHit(
                    found=True,
                    analysis=analysis_data,  # À adapter selon le modèle
                    cache_age_hours=age_hours,
                    cache_id=cache_id
                )
                
            except json.JSONDecodeError:
                # Cache corrompu, le marquer comme invalide
                cursor.execute('UPDATE analysis_cache SET is_valid = 0 WHERE id = ?', (cache_id,))
                conn.commit()
                return CacheHit(found=False)
    
    def save_analysis_to_cache(self, raw_content: RawContent, analysis: ContentAnalysis, 
                              ttl_hours: int = 168) -> int:  # 1 semaine par défaut
        """Sauvegarde une analyse dans le cache."""
        content_hash = self._generate_content_hash(raw_content.content)
        expires_at = datetime.now() + timedelta(hours=ttl_hours)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Sérialisation de l'analyse avec gestion des Enum
            analysis_dict = asdict(analysis)
            analysis_dict = self._serialize_for_json(analysis_dict)
            analysis_json = json.dumps(analysis_dict)
            
            cursor.execute('''
                INSERT OR REPLACE INTO analysis_cache (
                    content_hash, analysis_result, expires_at
                ) VALUES (?, ?, ?)
            ''', (content_hash, analysis_json, expires_at))
            
            return cursor.lastrowid
    
    def save_analyzed_content(self, analyzed_content: AnalyzedContent, 
                            analysis_time: float = 0.0) -> int:
        """Sauvegarde un contenu analysé complet."""
        # Sauvegarde de l'article
        article_id, was_new = self.save_article_with_deduplication(analyzed_content.raw_content)
        
        # Sauvegarde de l'analyse
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Sérialisation de l'analyse avec gestion des Enum
            analysis_dict = asdict(analyzed_content.analysis)
            analysis_dict = self._serialize_for_json(analysis_dict)
            analysis_json = json.dumps(analysis_dict)
            
            cursor.execute('''
                INSERT INTO analyses (
                    article_id, analysis_result, content_hash, 
                    analysis_time_seconds, analyzed_date
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                article_id,
                analysis_json,
                self._generate_content_hash(analyzed_content.raw_content.content),
                analysis_time,
                analyzed_content.analyzed_at
            ))
            
            analysis_id = cursor.lastrowid
        
        # Sauvegarde dans le cache
        self.save_analysis_to_cache(analyzed_content.raw_content, analyzed_content.analysis)
        
        return analysis_id
    
    # ==========================================
    # MÉTRIQUES ET HISTORIQUE
    # ==========================================
    
    def save_performance_metrics(self, metrics: PerformanceMetrics) -> int:
        """Sauvegarde les métriques de performance."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO performance_metrics (
                    date, collection_time, analysis_time, synthesis_time, total_time,
                    articles_collected, articles_analyzed, articles_in_digest,
                    cache_hit_rate, duplication_rate, average_quality_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.date.date(),
                metrics.collection_time,
                metrics.analysis_time,
                metrics.synthesis_time,
                metrics.total_time,
                metrics.articles_collected,
                metrics.articles_analyzed,
                metrics.articles_in_digest,
                metrics.cache_hit_rate,
                metrics.duplication_rate,
                metrics.average_quality_score
            ))
            
            return cursor.lastrowid
    
    def save_digest(self, daily_digest: DailyDigest, config_snapshot: Dict = None) -> int:
        """Sauvegarde un digest complet."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Extraction des IDs d'articles inclus
            included_article_ids = []
            for article_synthesis in daily_digest.top_articles:
                if hasattr(article_synthesis, 'original_article'):
                    # Recherche de l'ID de l'article par URL
                    cursor.execute('SELECT id FROM articles WHERE url = ?', 
                                 (article_synthesis.original_article.raw_content.url,))
                    result = cursor.fetchone()
                    if result:
                        included_article_ids.append(result[0])
            
            # Sérialisation du digest avec gestion des Enum
            digest_dict = asdict(daily_digest)
            digest_dict = self._serialize_for_json(digest_dict)
            digest_json = json.dumps(digest_dict)
            
            cursor.execute('''
                INSERT OR REPLACE INTO digests (
                    date, title, digest_data, markdown_content, included_articles,
                    target_audience, word_count, estimated_read_time,
                    generation_time, config_snapshot
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                daily_digest.date.date(),
                daily_digest.title,
                digest_json,
                daily_digest.markdown_content,
                json.dumps(included_article_ids),
                daily_digest.target_audience,
                daily_digest.word_count,
                daily_digest.estimated_read_time,
                0.0,  # À calculer en appelant
                json.dumps(config_snapshot) if config_snapshot else "{}"
            ))
            
            return cursor.lastrowid
    
    # ==========================================
    # REQUÊTES ET STATISTIQUES
    # ==========================================
    
    def get_duplicate_stats(self, days: int = 7) -> Dict[str, Any]:
        """Statistiques de déduplication sur les N derniers jours."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            since_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT COUNT(*) as total_processed,
                       COUNT(DISTINCT url_hash) as unique_urls,
                       COUNT(DISTINCT content_hash) as unique_content
                FROM articles 
                WHERE collected_date >= ?
            ''', (since_date,))
            
            result = cursor.fetchone()
            total, unique_urls, unique_content = result
            
            return {
                'total_processed': total,
                'unique_urls': unique_urls,
                'unique_content': unique_content,
                'url_duplication_rate': (total - unique_urls) / total if total > 0 else 0,
                'content_duplication_rate': (total - unique_content) / total if total > 0 else 0,
                'period_days': days
            }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du cache d'analyses."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) as total_entries,
                       COUNT(CASE WHEN is_valid = 1 THEN 1 END) as valid_entries,
                       AVG(use_count) as avg_use_count,
                       SUM(use_count) as total_cache_hits
                FROM analysis_cache
            ''')
            
            result = cursor.fetchone()
            total, valid, avg_use, total_hits = result
            
            return {
                'total_entries': total or 0,
                'valid_entries': valid or 0,
                'invalid_entries': (total or 0) - (valid or 0),
                'average_use_count': avg_use or 0,
                'total_cache_hits': total_hits or 0,
                'cache_efficiency': (total_hits or 0) / (total or 1)
            }
    
    def cleanup_old_cache(self, days_to_keep: int = 30) -> int:
        """Nettoie les anciens éléments du cache."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Suppression des éléments expirés ou trop anciens
            cursor.execute('''
                DELETE FROM analysis_cache 
                WHERE expires_at < ? OR (last_used < ? AND use_count <= 1)
            ''', (datetime.now(), cutoff_date))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            return deleted_count
    
    def get_historical_performance(self, days: int = 30) -> List[PerformanceMetrics]:
        """Récupère l'historique des performances."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            since_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT * FROM performance_metrics 
                WHERE date >= ? 
                ORDER BY date DESC
            ''', (since_date.date(),))
            
            results = []
            for row in cursor.fetchall():
                metrics = PerformanceMetrics(
                    date=datetime.fromisoformat(str(row[1])),
                    collection_time=row[2],
                    analysis_time=row[3],
                    synthesis_time=row[4],
                    total_time=row[5],
                    articles_collected=row[6],
                    articles_analyzed=row[7],
                    articles_in_digest=row[8],
                    cache_hit_rate=row[9],
                    duplication_rate=row[10],
                    average_quality_score=row[11]
                )
                results.append(metrics)
            
            return results
    
    def close(self):
        """Ferme toutes les connexions ouvertes."""
        # SQLite ferme automatiquement les connexions, mais on peut forcer le garbage collection
        import gc
        gc.collect()
