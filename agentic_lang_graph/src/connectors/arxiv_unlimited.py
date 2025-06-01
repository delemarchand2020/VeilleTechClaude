#!/usr/bin/env python3
"""
Version fallback du connecteur ArXiv sans restrictions de date.
"""
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus
from loguru import logger

from src.connectors.base_connector import BaseConnector, RawContent


class ArxivConnectorUnlimited(BaseConnector):
    """
    Version ArXiv sans restrictions de date pour diagnostics.
    """
    
    # Catégories les plus actives
    ACTIVE_CATEGORIES = ["cs.LG", "cs.CL", "stat.ML", "cs.AI"]
    
    # Mots-clés très populaires
    POPULAR_KEYWORDS = [
        "machine learning", "neural network", "artificial intelligence",
        "deep learning", "transformer", "language model"
    ]
    
    def __init__(self, keywords: List[str] = None):
        super().__init__("arxiv_unlimited", keywords)
        
        self.base_url = "http://export.arxiv.org/api/query"
        self.timeout = 30
        self.user_agent = "Agent-Veille-Tech-Unlimited/1.0"
        
        self.categories = self.ACTIVE_CATEGORIES
        self.search_keywords = self.POPULAR_KEYWORDS + (keywords or [])
        
        # Configuration sans restrictions
        self.max_results_per_query = 300
        self.use_date_filter = False  # AUCUN filtre de date
        
        self.logger.info(f"ArXiv Unlimited initialisé - AUCUNE restriction de date")
    
    async def collect(self, limit: int = 10) -> List[RawContent]:
        """Collecte ArXiv sans restrictions de date."""
        self.logger.info(f"🔍 Début collecte ArXiv UNLIMITED (limite: {limit})")
        
        all_contents = []
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        headers = {"User-Agent": self.user_agent}
        
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            # Requêtes simplifiées sans filtre de date
            queries = self._build_unlimited_queries()
            
            tasks = [
                self._execute_search(session, query, self.max_results_per_query) 
                for query in queries
            ]
            
            search_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(search_results):
                if isinstance(result, Exception):
                    self.logger.warning(f"Erreur requête {i+1}: {result}")
                    continue
                
                if result:
                    all_contents.extend(result)
                    self.logger.debug(f"✅ {len(result)} papers de la requête {i+1}")
        
        self.logger.info(f"📥 {len(all_contents)} papers collectés bruts")
        
        if all_contents:
            all_contents = self.clean_and_validate(all_contents)
            all_contents = self.filter_by_keywords(all_contents)
            all_contents = self._deduplicate(all_contents)
            
            # Trie par date (plus récent d'abord)
            all_contents.sort(
                key=lambda x: x.published_date or datetime.min.replace(tzinfo=timezone.utc), 
                reverse=True
            )
            
            all_contents = all_contents[:limit]
        
        self.logger.info(f"✅ Collecte ArXiv UNLIMITED terminée: {len(all_contents)} papers finaux")
        return all_contents
    
    def _build_unlimited_queries(self) -> List[str]:
        """Construit des requêtes sans filtre de date."""
        queries = []
        
        # 1. Recherche par catégories (SANS filtre de date)
        for category in self.categories:
            query = f"cat:{category}"
            queries.append(query)
        
        # 2. Recherche par mots-clés populaires
        for keyword in self.POPULAR_KEYWORDS[:5]:  # Top 5 seulement
            query = f'abs:"{keyword}"'
            queries.append(query)
        
        self.logger.debug(f"Construites {len(queries)} requêtes UNLIMITED")
        return queries
    
    async def _execute_search(self, session: aiohttp.ClientSession, query: str, max_results: int) -> List[RawContent]:
        """Exécute une requête ArXiv."""
        try:
            params = {
                'search_query': query,
                'start': 0,
                'max_results': max_results,
                'sortBy': 'submittedDate',
                'sortOrder': 'descending'
            }
            
            param_string = '&'.join([f"{k}={quote_plus(str(v))}" for k, v in params.items()])
            url = f"{self.base_url}?{param_string}"
            
            self.logger.debug(f"📡 Requête ArXiv UNLIMITED: {query[:50]}...")
            
            async with session.get(url) as response:
                if response.status != 200:
                    self.logger.warning(f"HTTP {response.status} pour requête ArXiv")
                    return []
                
                xml_content = await response.text()
                papers = self._parse_arxiv_response(xml_content)
                
                self.logger.debug(f"✅ {len(papers)} papers parsés")
                return papers
        
        except Exception as e:
            self.logger.error(f"❌ Erreur requête ArXiv: {e}")
            return []
    
    def _parse_arxiv_response(self, xml_content: str) -> List[RawContent]:
        """Parse la réponse XML ArXiv."""
        papers = []
        
        try:
            root = ET.fromstring(xml_content)
            
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            entries = root.findall('atom:entry', namespaces)
            
            for entry in entries:
                paper = self._parse_arxiv_entry(entry, namespaces)
                if paper:
                    papers.append(paper)
            
            self.logger.debug(f"Parsés {len(papers)} papers depuis XML ArXiv")
            
        except ET.ParseError as e:
            self.logger.error(f"Erreur parsing XML ArXiv: {e}")
        except Exception as e:
            self.logger.error(f"Erreur inattendue parsing ArXiv: {e}")
        
        return papers
    
    def _parse_arxiv_entry(self, entry, namespaces: Dict[str, str]) -> Optional[RawContent]:
        """Parse une entrée ArXiv."""
        try:
            # Titre
            title_elem = entry.find('atom:title', namespaces)
            if title_elem is None or not title_elem.text:
                return None
            title = title_elem.text.strip().replace('\n', ' ').replace('  ', ' ')
            
            # URL
            link_elem = entry.find('atom:id', namespaces)
            if link_elem is None or not link_elem.text:
                return None
            arxiv_url = link_elem.text.strip()
            
            # Abstract
            summary_elem = entry.find('atom:summary', namespaces)
            abstract = ""
            if summary_elem is not None and summary_elem.text:
                abstract = summary_elem.text.strip().replace('\n', ' ').replace('  ', ' ')
            
            # Auteurs
            authors = []
            author_elems = entry.findall('atom:author/atom:name', namespaces)
            for author_elem in author_elems:
                if author_elem.text:
                    authors.append(author_elem.text.strip())
            author_str = ", ".join(authors) if authors else ""
            
            # Date de publication
            published_elem = entry.find('atom:published', namespaces)
            published_date = None
            if published_elem is not None and published_elem.text:
                try:
                    date_str = published_elem.text.strip()
                    published_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except ValueError:
                    self.logger.warning(f"Format de date invalide: {published_elem.text}")
            
            # Catégories
            categories = []
            category_elems = entry.findall('atom:category', namespaces)
            for cat_elem in category_elems:
                term = cat_elem.get('term')
                if term:
                    categories.append(term)
            
            # ID ArXiv
            arxiv_id = self._extract_arxiv_id(arxiv_url)
            
            # Données brutes
            raw_data = {
                'arxiv_id': arxiv_id,
                'pdf_url': f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else "",
                'categories': categories,
                'authors_list': authors
            }
            
            return RawContent(
                title=title,
                url=arxiv_url,
                source="arxiv",
                content=abstract,
                excerpt=abstract[:500] + "..." if len(abstract) > 500 else abstract,
                author=author_str,
                published_date=published_date,
                tags=categories,
                raw_data=raw_data
            )
            
        except Exception as e:
            self.logger.error(f"Erreur parsing entrée ArXiv: {e}")
            return None
    
    def _extract_arxiv_id(self, arxiv_url: str) -> str:
        """Extrait l'ID ArXiv."""
        try:
            if '/abs/' in arxiv_url:
                return arxiv_url.split('/abs/')[-1]
            return ""
        except:
            return ""
    
    def _deduplicate(self, contents: List[RawContent]) -> List[RawContent]:
        """Supprime les doublons."""
        seen_ids = set()
        unique_contents = []
        
        for content in contents:
            arxiv_id = content.raw_data.get('arxiv_id', '')
            dedup_key = arxiv_id or content.url
            
            if dedup_key not in seen_ids:
                seen_ids.add(dedup_key)
                unique_contents.append(content)
        
        self.logger.info(f"Déduplication ArXiv: {len(contents)} → {len(unique_contents)} papers")
        return unique_contents
    
    def is_available(self) -> bool:
        """Vérifie disponibilité ArXiv."""
        import requests
        
        try:
            test_url = f"{self.base_url}?search_query=cat:cs.LG&max_results=1"
            response = requests.get(test_url, timeout=10, headers={"User-Agent": self.user_agent})
            
            if response.status_code == 200:
                return '<feed xmlns="http://www.w3.org/2005/Atom"' in response.text
            
            return False
            
        except Exception as e:
            self.logger.error(f"Test disponibilité ArXiv échoué: {e}")
            return False


# Test rapide de la version unlimited
async def test_unlimited():
    """Test rapide du connecteur unlimited."""
    print("🚀 TEST ARXIV UNLIMITED")
    print("=" * 40)
    
    connector = ArxivConnectorUnlimited()
    
    try:
        contents = await connector.collect(limit=5)
        print(f"✅ {len(contents)} contenus collectés")
        
        if contents:
            for i, content in enumerate(contents[:3], 1):
                print(f"{i}. {content.title[:50]}...")
                print(f"   📅 {content.published_date}")
        else:
            print("❌ Aucun contenu trouvé")
    
    except Exception as e:
        print(f"❌ Erreur: {e}")


if __name__ == "__main__":
    asyncio.run(test_unlimited())
