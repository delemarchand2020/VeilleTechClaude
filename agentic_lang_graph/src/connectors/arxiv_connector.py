"""
Connecteur ArXiv pour la collecte de papers académiques sur GenAI/LLM.

Ce connecteur utilise l'API ArXiv pour collecter des papers récents
sur les sujets de recherche en intelligence artificielle.

ArXiv API :
- API REST publique et gratuite
- Recherche par catégories et mots-clés
- Métadonnées complètes des papers
- Pas de limite de taux stricte (mais utilisation polie recommandée)
"""
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus
from loguru import logger

from .base_connector import BaseConnector, RawContent


class ArxivConnector(BaseConnector):
    """
    Connecteur pour ArXiv utilisant l'API de recherche officielle.
    
    Ce connecteur collecte des papers depuis ArXiv en utilisant :
    1. L'API de recherche ArXiv (http://export.arxiv.org/api/query)
    2. Recherche par catégories pertinentes (cs.AI, cs.CL, cs.LG, etc.)
    3. Recherche par mots-clés dans les titres et abstracts
    
    Avantages de l'API ArXiv :
    - API officielle gratuite et stable
    - Métadonnées complètes (auteurs, abstract, catégories)
    - Recherche fine par catégories et dates
    - Accès au texte complet (PDF)
    
    Limitations :
    - Contenu académique uniquement
    - Peut être très technique
    - Volume variable selon les périodes
    """
    
    # Catégories ArXiv OPTIMISÉES (plus actives)
    RELEVANT_CATEGORIES = [
        "cs.LG",    # Machine Learning (plus actif)
        "cs.CL",    # Computation and Language (NLP)
        "stat.ML",  # Machine Learning (Statistics)
        "cs.AI",    # Artificial Intelligence
        "cs.CV",    # Computer Vision
        "cs.IR",    # Information Retrieval
        "cs.HC",    # Human-Computer Interaction
        "cs.MA",    # Multiagent Systems
        "cs.NE",    # Neural and Evolutionary Computing
    ]
    
    # Mots-clés OPTIMISÉS (plus génériques et populaires)
    DEFAULT_KEYWORDS = [
        # Mots-clés très populaires (priorité haute)
        "machine learning",
        "neural network", 
        "artificial intelligence",
        "deep learning",
        
        # Mots-clés IA moderne
        "transformer",
        "large language model",
        "language model",
        "LLM",
        
        # Techniques spécifiques
        "attention mechanism",
        "generative AI", 
        "natural language processing",
        "computer vision",
        "reinforcement learning",
        
        # Modèles populaires
        "GPT",
        "BERT",
        "transformer model",
        
        # Applications
        "multi-agent",
        "chatbot",
        "conversational AI",
        "prompt engineering",
        "fine-tuning",
        "RLHF",
        "instruction tuning"
    ]
    
    def __init__(self, keywords: List[str] = None, categories: List[str] = None):
        """
        Initialise le connecteur ArXiv.
        
        Args:
            keywords: Mots-clés pour filtrer les papers (en plus des défauts)
            categories: Catégories ArXiv à surveiller (utilise les défauts si None)
        """
        super().__init__("arxiv", keywords)
        
        # Configuration spécifique à ArXiv
        self.base_url = "http://export.arxiv.org/api/query"
        self.timeout = 30
        self.user_agent = "Agent-Veille-Tech/1.0 (https://github.com/user/agent-veille)"
        
        # Catégories à surveiller
        self.categories = categories or self.RELEVANT_CATEGORIES
        
        # Keywords combinés (défauts + utilisateur)
        all_keywords = self.DEFAULT_KEYWORDS.copy()
        if keywords:
            all_keywords.extend(keywords)
        self.search_keywords = list(set(all_keywords))  # Supprime les doublons
        
        # Configuration de recherche OPTIMISÉE
        self.max_results_per_query = 200  # Limite par requête (maximisée)
        self.days_back = 180  # Chercher les papers des N derniers jours (très permissif)
        
        self.logger.info(f"ArXiv connector initialisé avec {len(self.categories)} catégories et {len(self.search_keywords)} mots-clés")
    
    async def collect(self, limit: int = 10) -> List[RawContent]:
        """
        Collecte les papers ArXiv récents.
        
        Processus :
        1. Construit des requêtes de recherche par catégorie et mots-clés
        2. Exécute les requêtes en parallèle
        3. Parse les réponses XML
        4. Filtre et trie les résultats
        5. Retourne les plus pertinents
        
        Args:
            limit: Nombre maximum de papers à retourner
            
        Returns:
            Liste de papers ArXiv formatés en RawContent
        """
        self.logger.info(f"🔍 Début collecte ArXiv (limite: {limit})")
        
        all_contents = []
        
        # Configuration pour les requêtes HTTP
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        headers = {"User-Agent": self.user_agent}
        
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            # Génère les requêtes de recherche
            search_queries = self._build_search_queries()
            
            # Exécute toutes les requêtes en parallèle
            tasks = [
                self._execute_search(session, query, self.max_results_per_query) 
                for query in search_queries
            ]
            
            # Attend toutes les réponses
            search_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Traite les résultats
            for i, result in enumerate(search_results):
                if isinstance(result, Exception):
                    self.logger.warning(f"Erreur requête {i+1}: {result}")
                    continue
                
                if result:
                    all_contents.extend(result)
                    self.logger.debug(f"✅ {len(result)} papers de la requête {i+1}")
        
        self.logger.info(f"📥 {len(all_contents)} papers collectés bruts")
        
        # Post-traitement
        if all_contents:
            # 1. Nettoie et valide
            all_contents = self.clean_and_validate(all_contents)
            
            # 2. Filtre par mots-clés (filtrage plus fin)
            all_contents = self.filter_by_keywords(all_contents)
            
            # 3. Déduplique (par ID ArXiv)
            all_contents = self._deduplicate(all_contents)
            
            # 4. Trie par date de soumission (plus récent d'abord)
            all_contents.sort(
                key=lambda x: x.published_date or datetime.min.replace(tzinfo=timezone.utc), 
                reverse=True
            )
            
            # 5. Limite les résultats
            all_contents = all_contents[:limit]
        
        self.logger.info(f"✅ Collecte ArXiv terminée: {len(all_contents)} papers finaux")
        return all_contents
    
    def _build_search_queries(self) -> List[str]:
        """
        Construit les requêtes de recherche ArXiv.
        
        Combine les catégories et mots-clés pour créer des requêtes optimales.
        
        Returns:
            Liste des requêtes de recherche à exécuter
        """
        queries = []
        
        # Date limite pour les papers récents
        date_limit = datetime.now(timezone.utc) - timedelta(days=self.days_back)
        date_str = date_limit.strftime("%Y%m%d%H%M%S")
        
        # 1. Recherche par catégories (papers récents dans chaque catégorie)
        for category in self.categories:
            query = f"cat:{category} AND submittedDate:[{date_str} TO *]"
            queries.append(query)
        
        # 2. Recherche par mots-clés importants (dans titre et abstract)
        important_keywords = [
            "large language model",
            "transformer",
            "generative AI",
            "GPT",
            "BERT",
            "neural network",
            "deep learning"
        ]
        
        for keyword in important_keywords:
            # Recherche dans titre ET abstract, avec limite de date
            query = f"(ti:\"{keyword}\" OR abs:\"{keyword}\") AND submittedDate:[{date_str} TO *]"
            queries.append(query)
        
        self.logger.debug(f"Construites {len(queries)} requêtes de recherche")
        return queries
    
    async def _execute_search(self, session: aiohttp.ClientSession, query: str, max_results: int) -> List[RawContent]:
        """
        Exécute une requête de recherche ArXiv.
        
        Args:
            session: Session HTTP
            query: Requête de recherche ArXiv
            max_results: Nombre maximum de résultats
            
        Returns:
            Liste des papers trouvés
        """
        try:
            # Construction de l'URL de requête
            params = {
                'search_query': query,
                'start': 0,
                'max_results': max_results,
                'sortBy': 'submittedDate',
                'sortOrder': 'descending'
            }
            
            # Encode les paramètres
            param_string = '&'.join([f"{k}={quote_plus(str(v))}" for k, v in params.items()])
            url = f"{self.base_url}?{param_string}"
            
            self.logger.debug(f"📡 Requête ArXiv: {query[:100]}...")
            
            async with session.get(url) as response:
                if response.status != 200:
                    self.logger.warning(f"HTTP {response.status} pour requête ArXiv")
                    return []
                
                # Récupère le contenu XML
                xml_content = await response.text()
                
                # Parse la réponse XML
                papers = self._parse_arxiv_response(xml_content)
                
                self.logger.debug(f"✅ {len(papers)} papers parsés")
                return papers
        
        except asyncio.TimeoutError:
            self.logger.error(f"⏰ Timeout sur requête ArXiv: {query[:50]}...")
            return []
        except Exception as e:
            self.logger.error(f"❌ Erreur requête ArXiv: {e}")
            return []
    
    def _parse_arxiv_response(self, xml_content: str) -> List[RawContent]:
        """
        Parse la réponse XML de l'API ArXiv.
        
        Args:
            xml_content: Contenu XML de la réponse ArXiv
            
        Returns:
            Liste des papers parsés
        """
        papers = []
        
        try:
            # Parse le XML
            root = ET.fromstring(xml_content)
            
            # Namespace ArXiv
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            # Trouve tous les entries (papers)
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
        """
        Parse une entrée (paper) individuelle de la réponse ArXiv.
        
        Args:
            entry: Élément XML de l'entrée
            namespaces: Namespaces XML
            
        Returns:
            RawContent ou None si invalide
        """
        try:
            # Titre
            title_elem = entry.find('atom:title', namespaces)
            if title_elem is None or not title_elem.text:
                return None
            title = title_elem.text.strip().replace('\n', ' ').replace('  ', ' ')
            
            # URL (lien vers la page ArXiv)
            link_elem = entry.find('atom:id', namespaces)
            if link_elem is None or not link_elem.text:
                return None
            arxiv_url = link_elem.text.strip()
            
            # Abstract (contenu principal)
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
            
            # Date de publication/soumission
            published_elem = entry.find('atom:published', namespaces)
            published_date = None
            if published_elem is not None and published_elem.text:
                try:
                    # Format ArXiv: 2024-01-15T09:30:00Z
                    date_str = published_elem.text.strip()
                    published_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except ValueError:
                    self.logger.warning(f"Format de date invalide: {published_elem.text}")
            
            # Catégories ArXiv
            categories = []
            category_elems = entry.findall('atom:category', namespaces)
            for cat_elem in category_elems:
                term = cat_elem.get('term')
                if term:
                    categories.append(term)
            
            # DOI (si disponible)
            doi = ""
            doi_elem = entry.find('arxiv:doi', namespaces)
            if doi_elem is not None and doi_elem.text:
                doi = doi_elem.text.strip()
            
            # Commentaires (info additionnelle)
            comment = ""
            comment_elem = entry.find('arxiv:comment', namespaces)
            if comment_elem is not None and comment_elem.text:
                comment = comment_elem.text.strip()
            
            # Journal reference (si publié)
            journal_ref = ""
            journal_elem = entry.find('arxiv:journal_ref', namespaces)
            if journal_elem is not None and journal_elem.text:
                journal_ref = journal_elem.text.strip()
            
            # Extraction de l'ID ArXiv depuis l'URL
            arxiv_id = self._extract_arxiv_id(arxiv_url)
            
            # URL du PDF
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else ""
            
            # Données brutes pour analyse future
            raw_data = {
                'arxiv_id': arxiv_id,
                'doi': doi,
                'comment': comment,
                'journal_ref': journal_ref,
                'pdf_url': pdf_url,
                'categories': categories,
                'authors_list': authors
            }
            
            return RawContent(
                title=title,
                url=arxiv_url,
                source="arxiv",
                content=abstract,  # L'abstract est le contenu principal
                excerpt=abstract[:500] + "..." if len(abstract) > 500 else abstract,
                author=author_str,
                published_date=published_date,
                tags=categories,  # Les catégories ArXiv comme tags
                raw_data=raw_data
            )
            
        except Exception as e:
            self.logger.error(f"Erreur parsing entrée ArXiv: {e}")
            return None
    
    def _extract_arxiv_id(self, arxiv_url: str) -> str:
        """
        Extrait l'ID ArXiv depuis l'URL.
        
        Args:
            arxiv_url: URL ArXiv (ex: http://arxiv.org/abs/2401.12345v1)
            
        Returns:
            ID ArXiv (ex: 2401.12345v1)
        """
        try:
            # Format typique: http://arxiv.org/abs/ID
            if '/abs/' in arxiv_url:
                return arxiv_url.split('/abs/')[-1]
            return ""
        except:
            return ""
    
    def _deduplicate(self, contents: List[RawContent]) -> List[RawContent]:
        """
        Supprime les doublons basés sur l'ID ArXiv.
        
        Args:
            contents: Liste avec potentiels doublons
            
        Returns:
            Liste sans doublons
        """
        seen_ids = set()
        unique_contents = []
        
        for content in contents:
            arxiv_id = content.raw_data.get('arxiv_id', '')
            # Utilise l'ID ArXiv ou l'URL comme clé de déduplication
            dedup_key = arxiv_id or content.url
            
            if dedup_key not in seen_ids:
                seen_ids.add(dedup_key)
                unique_contents.append(content)
            else:
                self.logger.debug(f"🔄 Doublon ArXiv supprimé: {content.title[:50]}...")
        
        self.logger.info(f"Déduplication ArXiv: {len(contents)} → {len(unique_contents)} papers")
        return unique_contents
    
    def is_available(self) -> bool:
        """
        Vérifie si l'API ArXiv est accessible.
        
        Returns:
            True si l'API répond correctement
        """
        import requests
        
        try:
            # Test avec une requête simple
            test_url = f"{self.base_url}?search_query=cat:cs.AI&max_results=1"
            response = requests.get(
                test_url,
                timeout=10,
                headers={"User-Agent": self.user_agent}
            )
            
            if response.status_code == 200:
                # Vérifie que c'est bien du XML ArXiv
                content = response.text
                return '<feed xmlns="http://www.w3.org/2005/Atom"' in content
            
            return False
            
        except Exception as e:
            self.logger.error(f"Test disponibilité ArXiv échoué: {e}")
            return False
    
    async def test_connection(self) -> dict:
        """
        Teste la connexion ArXiv et retourne des statistiques.
        
        Returns:
            Dictionnaire avec les résultats de test
        """
        self.logger.info("🧪 Test de connexion ArXiv...")
        
        results = {
            'available': False,
            'categories_tested': len(self.categories),
            'keywords_used': len(self.search_keywords),
            'sample_papers': [],
            'errors': []
        }
        
        try:
            # Test avec collecte limitée
            sample_papers = await self.collect(limit=3)
            
            results['available'] = len(sample_papers) > 0
            results['sample_papers'] = [
                {
                    'title': paper.title[:100],
                    'authors': paper.author[:100] if paper.author else "N/A",
                    'date': paper.published_date.isoformat() if paper.published_date else None,
                    'categories': paper.tags[:5],  # Limite les catégories affichées
                    'arxiv_id': paper.raw_data.get('arxiv_id', ''),
                    'url': paper.url
                }
                for paper in sample_papers[:3]
            ]
            
        except Exception as e:
            results['errors'].append(str(e))
            self.logger.error(f"Test connexion ArXiv échoué: {e}")
        
        self.logger.info(f"✅ Test ArXiv terminé: {len(results['sample_papers'])} papers trouvés")
        return results
    
    def get_paper_pdf_url(self, content: RawContent) -> str:
        """
        Retourne l'URL du PDF pour un paper ArXiv.
        
        Args:
            content: Contenu ArXiv
            
        Returns:
            URL du PDF ou chaîne vide
        """
        if content.source != "arxiv":
            return ""
        
        return content.raw_data.get('pdf_url', '')
    
    def get_categories_info(self) -> Dict[str, str]:
        """
        Retourne les informations sur les catégories ArXiv surveillées.
        
        Returns:
            Dictionnaire {catégorie: description}
        """
        category_descriptions = {
            "cs.AI": "Artificial Intelligence",
            "cs.CL": "Computation and Language (NLP)",
            "cs.CV": "Computer Vision and Pattern Recognition",
            "cs.HC": "Human-Computer Interaction",
            "cs.IR": "Information Retrieval",
            "cs.LG": "Machine Learning",
            "cs.MA": "Multiagent Systems",
            "cs.NE": "Neural and Evolutionary Computing",
            "stat.ML": "Machine Learning (Statistics)"
        }
        
        return {cat: category_descriptions.get(cat, "Unknown category") for cat in self.categories}
