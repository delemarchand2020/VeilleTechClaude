"""
Connecteur Medium pour la collecte d'articles sur GenAI/LLM.

Ce connecteur utilise les flux RSS publics de Medium pour collecter
des articles récents sur les sujets de veille technologique.

Medium expose plusieurs flux RSS intéressants :
- Par tag : https://medium.com/feed/tag/{tag}
- Par publication : https://medium.com/feed/{publication}
- Recherche générale (moins fiable)
"""
import asyncio
import aiohttp
import feedparser
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import quote_plus
from loguru import logger

from .base_connector import BaseConnector, RawContent


class MediumConnector(BaseConnector):
    """
    Connecteur pour Medium utilisant les flux RSS.
    
    Ce connecteur collecte des articles depuis Medium en utilisant :
    1. Les flux RSS par tag (artificial-intelligence, machine-learning, etc.)
    2. Les flux de publications spécialisées (Towards Data Science, etc.)
    
    Avantages des flux RSS :
    - Pas besoin d'API key
    - Données structurées
    - Contenu récent et à jour
    
    Limitations :
    - Contenu partiel (résumés seulement)
    - Nombre limité d'articles par flux
    - Pas de contrôle fin sur les critères
    """
    
    # Tags Medium pertinents pour notre veille
    RELEVANT_TAGS = [
        "artificial-intelligence",
        "machine-learning", 
        "generative-ai",
        "large-language-models",
        "llm",
        "chatgpt",
        "automation",
        "ai-agents"
    ]
    
    # Publications Medium spécialisées
    RELEVANT_PUBLICATIONS = [
        "towards-data-science",
        "towards-ai",
        "artificial-intelligence",
        "the-ai-revolution"
    ]
    
    def __init__(self, keywords: List[str] = None):
        """
        Initialise le connecteur Medium.
        
        Args:
            keywords: Mots-clés pour filtrer les articles
        """
        super().__init__("medium", keywords)
        
        # Configuration spécifique à Medium
        self.base_url = "https://medium.com/feed"
        self.timeout = 30  # Timeout pour les requêtes HTTP
        self.user_agent = "Agent-Veille-Tech/1.0"  # User-Agent poli
        
        # URLs à surveiller (construites dynamiquement)
        self.feed_urls = self._build_feed_urls()
        
        self.logger.info(f"Medium connector initialisé avec {len(self.feed_urls)} flux RSS")
    
    def _build_feed_urls(self) -> List[str]:
        """
        Construit la liste des URLs de flux RSS à surveiller.
        
        Returns:
            Liste des URLs de flux RSS Medium
        """
        urls = []
        
        # Flux par tags
        for tag in self.RELEVANT_TAGS:
            urls.append(f"{self.base_url}/tag/{tag}")
        
        # Flux par publications
        for publication in self.RELEVANT_PUBLICATIONS:
            urls.append(f"{self.base_url}/{publication}")
        
        return urls
    
    async def collect(self, limit: int = 10) -> List[RawContent]:
        """
        Collecte les articles Medium depuis les flux RSS.
        
        Processus :
        1. Parcourt tous les flux RSS configurés
        2. Parse le contenu XML de chaque flux
        3. Extrait les métadonnées des articles
        4. Filtre par mots-clés
        5. Déduplique les résultats
        6. Retourne les plus récents
        
        Args:
            limit: Nombre maximum d'articles à retourner
            
        Returns:
            Liste d'articles Medium formatés en RawContent
        """
        self.logger.info(f"🔍 Début collecte Medium (limite: {limit})")
        
        all_contents = []
        
        # Configuration pour les requêtes HTTP asynchrones
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        headers = {"User-Agent": self.user_agent}
        
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            # Traite tous les flux en parallèle pour optimiser les performances
            tasks = [
                self._fetch_feed(session, url) 
                for url in self.feed_urls
            ]
            
            # Attend toutes les réponses (avec gestion d'erreurs individuelles)
            feed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Traite les résultats
            for i, result in enumerate(feed_results):
                if isinstance(result, Exception):
                    self.logger.warning(f"Erreur flux {self.feed_urls[i]}: {result}")
                    continue
                
                if result:  # Si le flux a retourné du contenu
                    all_contents.extend(result)
                    self.logger.debug(f"✅ {len(result)} articles du flux {i+1}")
        
        self.logger.info(f"📥 {len(all_contents)} articles collectés bruts")
        
        # Post-traitement des données
        if all_contents:
            # 1. Nettoie et valide
            all_contents = self.clean_and_validate(all_contents)
            
            # 2. Filtre par mots-clés
            all_contents = self.filter_by_keywords(all_contents)
            
            # 3. Déduplique (par URL)
            all_contents = self._deduplicate(all_contents)
            
            # 4. Trie par date (plus récent d'abord)
            all_contents.sort(
                key=lambda x: x.published_date or datetime.min.replace(tzinfo=timezone.utc), 
                reverse=True
            )
            
            # 5. Limite le nombre de résultats
            all_contents = all_contents[:limit]
        
        self.logger.info(f"✅ Collecte Medium terminée: {len(all_contents)} articles finaux")
        return all_contents
    
    async def _fetch_feed(self, session: aiohttp.ClientSession, feed_url: str) -> List[RawContent]:
        """
        Récupère et parse un flux RSS spécifique.
        
        Args:
            session: Session HTTP pour la requête
            feed_url: URL du flux RSS à traiter
            
        Returns:
            Liste des articles du flux, ou liste vide en cas d'erreur
        """
        try:
            self.logger.debug(f"📡 Récupération {feed_url}")
            
            async with session.get(feed_url) as response:
                if response.status != 200:
                    self.logger.warning(f"HTTP {response.status} pour {feed_url}")
                    return []
                
                # Récupère le contenu XML
                xml_content = await response.text()
                
                # Parse le flux RSS avec feedparser
                feed = feedparser.parse(xml_content)
                
                if not hasattr(feed, 'entries') or not feed.entries:
                    self.logger.warning(f"Pas d'articles dans {feed_url}")
                    return []
                
                # Convertit chaque entrée RSS en RawContent
                contents = []
                for entry in feed.entries:
                    content = self._parse_rss_entry(entry, feed_url)
                    if content:
                        contents.append(content)
                
                self.logger.debug(f"✅ {len(contents)} articles parsés de {feed_url}")
                return contents
                
        except asyncio.TimeoutError:
            self.logger.error(f"⏰ Timeout sur {feed_url}")
            return []
        except Exception as e:
            self.logger.error(f"❌ Erreur sur {feed_url}: {e}")
            return []
    
    def _parse_rss_entry(self, entry, source_url: str) -> Optional[RawContent]:
        """
        Convertit une entrée RSS en objet RawContent.
        
        Args:
            entry: Entrée feedparser du flux RSS
            source_url: URL du flux source (pour debug)
            
        Returns:
            RawContent ou None si l'entrée est invalide
        """
        try:
            # Extraction du titre
            title = getattr(entry, 'title', '').strip()
            if not title:
                return None
            
            # Extraction de l'URL
            url = getattr(entry, 'link', '').strip()
            if not url:
                return None
            
            # Extraction du contenu/résumé
            excerpt = ""
            if hasattr(entry, 'summary'):
                excerpt = entry.summary
            elif hasattr(entry, 'description'):
                excerpt = entry.description
            
            # Nettoyage du HTML dans l'excerpt (feedparser ne le fait pas toujours)
            if excerpt:
                import re
                excerpt = re.sub(r'<[^>]+>', '', excerpt).strip()
            
            # Extraction de l'auteur
            author = ""
            if hasattr(entry, 'author'):
                author = entry.author
            elif hasattr(entry, 'dc_creator'):
                author = entry.dc_creator
            
            # Extraction de la date de publication
            published_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            
            # Extraction des tags
            tags = []
            if hasattr(entry, 'tags'):
                tags = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
            
            # Données brutes pour debug/analyse future
            raw_data = {
                'source_feed': source_url,
                'guid': getattr(entry, 'id', ''),
                'updated': getattr(entry, 'updated', ''),
                'published': getattr(entry, 'published', ''),
                'medium_post_id': self._extract_medium_post_id(url)
            }
            
            return RawContent(
                title=title,
                url=url,
                source="medium",
                excerpt=excerpt,
                author=author,
                published_date=published_date,
                tags=tags,
                raw_data=raw_data
            )
            
        except Exception as e:
            self.logger.error(f"Erreur parsing entrée RSS: {e}")
            return None
    
    def _extract_medium_post_id(self, url: str) -> str:
        """
        Extrait l'ID du post Medium depuis l'URL.
        
        Les URLs Medium contiennent généralement un ID unique
        qu'on peut utiliser pour la déduplication.
        
        Args:
            url: URL de l'article Medium
            
        Returns:
            ID du post ou chaîne vide
        """
        try:
            # Format typique: https://medium.com/@author/title-123abc456def
            # L'ID est généralement à la fin après le dernier '-'
            if '-' in url:
                return url.split('-')[-1]
            return ""
        except:
            return ""
    
    def _deduplicate(self, contents: List[RawContent]) -> List[RawContent]:
        """
        Supprime les doublons basés sur l'URL.
        
        Args:
            contents: Liste avec potentiels doublons
            
        Returns:
            Liste sans doublons
        """
        seen_urls = set()
        unique_contents = []
        
        for content in contents:
            if content.url not in seen_urls:
                seen_urls.add(content.url)
                unique_contents.append(content)
            else:
                self.logger.debug(f"🔄 Doublon supprimé: {content.title[:50]}...")
        
        self.logger.info(f"Déduplication: {len(contents)} → {len(unique_contents)} articles")
        return unique_contents
    
    def is_available(self) -> bool:
        """
        Vérifie si Medium est accessible en testant un flux simple.
        
        Returns:
            True si au moins un flux répond correctement
        """
        import requests
        
        try:
            # Test avec un flux simple et rapide
            test_url = f"{self.base_url}/tag/artificial-intelligence"
            response = requests.get(
                test_url, 
                timeout=10,
                headers={"User-Agent": self.user_agent}
            )
            
            if response.status_code == 200:
                # Vérifie que c'est bien du XML/RSS
                content_type = response.headers.get('content-type', '').lower()
                return 'xml' in content_type or 'rss' in content_type
            
            return False
            
        except Exception as e:
            self.logger.error(f"Test disponibilité Medium échoué: {e}")
            return False
    
    async def test_connection(self) -> dict:
        """
        Teste la connexion et retourne des statistiques pour debug.
        
        Returns:
            Dictionnaire avec les résultats de test
        """
        self.logger.info("🧪 Test de connexion Medium...")
        
        results = {
            'available': False,
            'working_feeds': 0,
            'total_feeds': len(self.feed_urls),
            'sample_articles': [],
            'errors': []
        }
        
        try:
            # Test de collecte avec limite faible
            sample_contents = await self.collect(limit=3)
            
            results['available'] = len(sample_contents) > 0
            results['working_feeds'] = len(sample_contents)  # Approximation
            results['sample_articles'] = [
                {
                    'title': content.title[:100],
                    'author': content.author,
                    'date': content.published_date.isoformat() if content.published_date else None,
                    'url': content.url
                }
                for content in sample_contents[:3]
            ]
            
        except Exception as e:
            results['errors'].append(str(e))
            self.logger.error(f"Test connexion échoué: {e}")
        
        self.logger.info(f"✅ Test terminé: {results['working_feeds']}/{results['total_feeds']} flux OK")
        return results
