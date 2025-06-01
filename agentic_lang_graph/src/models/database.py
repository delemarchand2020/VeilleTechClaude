"""Modèles de données pour la base SQLite"""
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

# Import relatif corrigé
try:
    from ..utils.config import validate_config
except ImportError:
    # Fallback si import relatif échoue
    def validate_config():
        pass

@dataclass
class Article:
    """Modèle pour un article collecté"""
    id: Optional[int] = None
    title: str = ""
    url: str = ""
    source: str = ""
    content: str = ""
    summary: str = ""
    published_date: Optional[datetime] = None
    collected_date: Optional[datetime] = None
    keywords: List[str] = None
    raw_data: Dict = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.raw_data is None:
            self.raw_data = {}
        if self.collected_date is None:
            self.collected_date = datetime.now()

@dataclass
class AnalysisResult:
    """Modèle pour les résultats d'analyse"""
    id: Optional[int] = None
    article_id: int = 0
    relevance_score: float = 0.0
    category: str = ""  # "Découverte" ou "Raffinement"
    technical_level: str = ""  # "Beginner", "Intermediate", "Expert"
    is_novel: bool = False
    analysis_summary: str = ""
    analyzed_date: Optional[datetime] = None
    
    def __post_init__(self):
        if self.analyzed_date is None:
            self.analyzed_date = datetime.now()

class DatabaseManager:
    """Gestionnaire de base de données SQLite"""
    
    def __init__(self, db_path: str = None):
        # Utilisation d'un chemin par défaut si non spécifié
        if db_path is None:
            # Création du répertoire data s'il n'existe pas
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "articles.db")
        
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données avec les tables nécessaires"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Table articles
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    source TEXT NOT NULL,
                    content TEXT,
                    summary TEXT,
                    published_date TIMESTAMP,
                    collected_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    keywords TEXT,  -- JSON array
                    raw_data TEXT   -- JSON object
                )
            ''')
            
            # Table analysis_results
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER NOT NULL,
                    relevance_score REAL NOT NULL,
                    category TEXT NOT NULL,
                    technical_level TEXT NOT NULL,
                    is_novel BOOLEAN NOT NULL,
                    analysis_summary TEXT,
                    analyzed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES articles (id)
                )
            ''')
            
            # Table reports (pour garder un historique)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_date DATE NOT NULL,
                    report_type TEXT NOT NULL,  -- "daily", "weekly"
                    content TEXT NOT NULL,      -- Le contenu Markdown
                    articles_included TEXT,     -- JSON array des IDs d'articles
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def save_article(self, article: Article) -> int:
        """Sauvegarde un article et retourne son ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO articles 
                (title, url, source, content, summary, published_date, keywords, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article.title,
                article.url,
                article.source,
                article.content,
                article.summary,
                article.published_date,
                json.dumps(article.keywords),
                json.dumps(article.raw_data)
            ))
            
            return cursor.lastrowid
    
    def save_analysis(self, analysis: AnalysisResult) -> int:
        """Sauvegarde un résultat d'analyse"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO analysis_results 
                (article_id, relevance_score, category, technical_level, is_novel, analysis_summary)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                analysis.article_id,
                analysis.relevance_score,
                analysis.category,
                analysis.technical_level,
                analysis.is_novel,
                analysis.analysis_summary
            ))
            
            return cursor.lastrowid
    
    def get_articles_by_date(self, date: datetime = None) -> List[Article]:
        """Récupère les articles d'une date donnée"""
        if date is None:
            date = datetime.now().date()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM articles 
                WHERE DATE(collected_date) = ?
                ORDER BY collected_date DESC
            ''', (date,))
            
            rows = cursor.fetchall()
            return [self._row_to_article(row) for row in rows]
    
    def get_top_analyzed_articles(self, limit: int = 3) -> List[tuple]:
        """Récupère les articles les mieux notés avec leur analyse"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT a.*, ar.* FROM articles a
                JOIN analysis_results ar ON a.id = ar.article_id
                ORDER BY ar.relevance_score DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            results = []
            for row in rows:
                article = self._row_to_article(row[:10])  # Les 10 premiers champs sont pour l'article
                analysis = self._row_to_analysis(row[10:])  # Les suivants pour l'analyse
                results.append((article, analysis))
            
            return results
    
    def _row_to_article(self, row) -> Article:
        """Convertit une ligne SQL en objet Article"""
        return Article(
            id=row[0],
            title=row[1],
            url=row[2],
            source=row[3],
            content=row[4],
            summary=row[5],
            published_date=datetime.fromisoformat(row[6]) if row[6] else None,
            collected_date=datetime.fromisoformat(row[7]) if row[7] else None,
            keywords=json.loads(row[8]) if row[8] else [],
            raw_data=json.loads(row[9]) if row[9] else {}
        )
    
    def _row_to_analysis(self, row) -> AnalysisResult:
        """Convertit une ligne SQL en objet AnalysisResult"""
        return AnalysisResult(
            id=row[0],
            article_id=row[1],
            relevance_score=row[2],
            category=row[3],
            technical_level=row[4],
            is_novel=bool(row[5]),
            analysis_summary=row[6],
            analyzed_date=datetime.fromisoformat(row[7]) if row[7] else None
        )
