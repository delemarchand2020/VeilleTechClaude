"""
Tests unitaires pour le connecteur Medium.

Ces tests vérifient le fonctionnement du MediumConnector,
incluant la collecte via RSS, le parsing et la gestion d'erreurs.
"""
import pytest
import asyncio
import aiohttp
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
import feedparser
from agentic_lang_graph.src.connectors.medium_connector import MediumConnector
from agentic_lang_graph.src.connectors.base_connector import RawContent


class TestMediumConnector:
    """Tests pour la classe MediumConnector."""
    
    def test_connector_initialization(self):
        """Teste l'initialisation du connecteur Medium."""
        keywords = ["AI", "Machine Learning"]
        connector = MediumConnector(keywords)
        
        assert connector.source_name == "medium"
        assert connector.keywords == keywords
        assert connector.base_url == "https://medium.com/feed"
        assert connector.timeout == 30
        assert len(connector.feed_urls) > 0
        
        # Vérifie que les URLs sont bien construites
        assert any("tag/artificial-intelligence" in url for url in connector.feed_urls)
        assert any("towards-data-science" in url for url in connector.feed_urls)
    
    def test_connector_initialization_no_keywords(self):
        """Teste l'initialisation sans mots-clés."""
        connector = MediumConnector()
        assert connector.keywords == []
    
    def test_build_feed_urls(self):
        """Teste la construction des URLs de flux RSS."""
        connector = MediumConnector()
        urls = connector._build_feed_urls()
        
        # Vérifie qu'on a des URLs pour tags et publications
        tag_urls = [url for url in urls if "/tag/" in url]
        pub_urls = [url for url in urls if "/tag/" not in url and "feed/" in url]
        
        assert len(tag_urls) > 0
        assert len(pub_urls) > 0
        
        # Vérifie des URLs spécifiques
        assert "https://medium.com/feed/tag/artificial-intelligence" in urls
        assert "https://medium.com/feed/towards-data-science" in urls
    
    def test_extract_medium_post_id(self):
        """Teste l'extraction de l'ID de post Medium."""
        connector = MediumConnector()
        
        # URL typique Medium
        url1 = "https://medium.com/@author/article-title-123abc456def"
        assert connector._extract_medium_post_id(url1) == "123abc456def"
        
        # URL sans ID (sans tiret)
        url2 = "https://medium.com/@author/simple"
        assert connector._extract_medium_post_id(url2) == ""
        
        # URL avec tiret simple
        url3 = "https://medium.com/@author/simple-article"
        assert connector._extract_medium_post_id(url3) == "article"
        
        # URL invalide
        url4 = "invalid-url"
        assert connector._extract_medium_post_id(url4) == "url"
    
    def test_deduplicate(self):
        """Teste la déduplication des articles."""
        connector = MediumConnector()
        
        contents = [
            RawContent("Article 1", "https://medium.com/article1", "medium"),
            RawContent("Article 2", "https://medium.com/article2", "medium"),
            RawContent("Article 1 Duplicate", "https://medium.com/article1", "medium"),  # Doublon
            RawContent("Article 3", "https://medium.com/article3", "medium"),
        ]
        
        deduplicated = connector._deduplicate(contents)
        
        assert len(deduplicated) == 3
        urls = [content.url for content in deduplicated]
        assert len(set(urls)) == 3  # Toutes les URLs sont uniques
    
    @pytest.mark.asyncio
    async def test_fetch_feed_success(self):
        """Teste la récupération réussie d'un flux RSS."""
        connector = MediumConnector()
        
        # Mock RSS content
        mock_rss_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Medium - AI</title>
                <item>
                    <title>Understanding GPT Models</title>
                    <link>https://medium.com/@author/understanding-gpt-123abc</link>
                    <description>A deep dive into GPT architecture...</description>
                    <author>AI Expert</author>
                    <pubDate>Mon, 15 Jan 2024 10:00:00 GMT</pubDate>
                    <guid>https://medium.com/@author/understanding-gpt-123abc</guid>
                </item>
            </channel>
        </rss>'''
        
        # Mock de la session HTTP
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_rss_content)
        
        mock_session = Mock()
        mock_session.get = Mock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Test
        feed_url = "https://medium.com/feed/tag/artificial-intelligence"
        contents = await connector._fetch_feed(mock_session, feed_url)
        
        assert len(contents) == 1
        assert contents[0].title == "Understanding GPT Models"
        assert contents[0].url == "https://medium.com/@author/understanding-gpt-123abc"
        assert contents[0].source == "medium"
        assert contents[0].author == "AI Expert"
    
    @pytest.mark.asyncio
    async def test_fetch_feed_http_error(self):
        """Teste la gestion d'erreur HTTP lors de la récupération."""
        connector = MediumConnector()
        
        # Mock d'une réponse d'erreur
        mock_response = Mock()
        mock_response.status = 404
        
        mock_session = Mock()
        mock_session.get = Mock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Test
        feed_url = "https://medium.com/feed/tag/nonexistent"
        contents = await connector._fetch_feed(mock_session, feed_url)
        
        assert contents == []  # Retourne liste vide en cas d'erreur
    
    @pytest.mark.asyncio
    async def test_fetch_feed_timeout(self):
        """Teste la gestion du timeout."""
        connector = MediumConnector()
        
        # Mock session qui lève un TimeoutError
        mock_session = Mock()
        mock_session.get.side_effect = asyncio.TimeoutError()
        
        # Test
        feed_url = "https://medium.com/feed/tag/test"
        contents = await connector._fetch_feed(mock_session, feed_url)
        
        assert contents == []
    
    def test_parse_rss_entry_complete(self):
        """Teste le parsing d'une entrée RSS complète."""
        connector = MediumConnector()
        
        # Création d'un mock d'entrée feedparser
        mock_entry = Mock()
        mock_entry.title = "Complete RSS Entry"
        mock_entry.link = "https://medium.com/@author/complete-entry-123abc"
        mock_entry.summary = "This is a complete RSS entry with all fields..."
        mock_entry.author = "Test Author"
        mock_entry.published_parsed = (2024, 1, 15, 10, 30, 0, 0, 15, 0)
        
        # Mock tags
        mock_tag1 = Mock()
        mock_tag1.term = "AI"
        mock_tag2 = Mock()
        mock_tag2.term = "Machine Learning"
        mock_entry.tags = [mock_tag1, mock_tag2]
        
        mock_entry.id = "unique-guid-123"
        
        # Test
        source_url = "https://medium.com/feed/test"
        content = connector._parse_rss_entry(mock_entry, source_url)
        
        assert content is not None
        assert content.title == "Complete RSS Entry"
        assert content.url == "https://medium.com/@author/complete-entry-123abc"
        assert content.source == "medium"
        assert content.excerpt == "This is a complete RSS entry with all fields..."
        assert content.author == "Test Author"
        assert content.published_date == datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        assert "AI" in content.tags
        assert "Machine Learning" in content.tags
        assert content.raw_data["source_feed"] == source_url
        assert content.raw_data["guid"] == "unique-guid-123"
    
    def test_parse_rss_entry_minimal(self):
        """Teste le parsing d'une entrée RSS minimale."""
        connector = MediumConnector()
        
        # Entrée avec seulement les champs obligatoires
        mock_entry = Mock()
        mock_entry.title = "Minimal Entry"
        mock_entry.link = "https://medium.com/@author/minimal"
        # Simuler l'absence d'autres attributs
        mock_entry.summary = None
        mock_entry.description = None
        mock_entry.author = None
        mock_entry.published_parsed = None
        mock_entry.updated_parsed = None
        
        # Mock pour hasattr qui retourne False pour les attributs optionnels
        def mock_hasattr(obj, name):
            return name in ['title', 'link']
        
        # Mock pour getattr qui retourne les valeurs ou des défauts
        def mock_getattr(obj, name, default=''):
            if name == 'title':
                return "Minimal Entry"
            elif name == 'link':
                return "https://medium.com/@author/minimal"
            elif name in ['id', 'updated', 'published']:
                return ''
            else:
                return default
        
        with patch('builtins.hasattr', side_effect=mock_hasattr), \
             patch('agentic_lang_graph.src.connectors.medium_connector.getattr', side_effect=mock_getattr):
            content = connector._parse_rss_entry(mock_entry, "test_feed")
        
        assert content is not None
        assert content.title == "Minimal Entry"
        assert content.url == "https://medium.com/@author/minimal"
        assert content.excerpt == ""
        assert content.author == ""
        assert content.published_date is None
        assert content.tags == []
    
    def test_parse_rss_entry_invalid(self):
        """Teste le parsing d'une entrée RSS invalide."""
        connector = MediumConnector()
        
        # Entrée sans titre
        mock_entry_no_title = Mock()
        mock_entry_no_title.title = ""
        mock_entry_no_title.link = "https://medium.com/test"
        
        content = connector._parse_rss_entry(mock_entry_no_title, "test_feed")
        assert content is None
        
        # Entrée sans URL
        mock_entry_no_url = Mock()
        mock_entry_no_url.title = "Valid Title"
        mock_entry_no_url.link = ""
        
        content = connector._parse_rss_entry(mock_entry_no_url, "test_feed")
        assert content is None
    
    def test_is_available_success(self):
        """Teste la vérification de disponibilité réussie."""
        connector = MediumConnector()
        
        with patch('requests.get') as mock_get:
            # Mock d'une réponse RSS valide
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'content-type': 'application/rss+xml'}
            mock_get.return_value = mock_response
            
            assert connector.is_available() is True
    
    def test_is_available_failure(self):
        """Teste la vérification de disponibilité en cas d'échec."""
        connector = MediumConnector()
        
        with patch('requests.get') as mock_get:
            # Mock d'une réponse d'erreur
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response
            
            assert connector.is_available() is False
    
    def test_is_available_exception(self):
        """Teste la vérification de disponibilité avec exception."""
        connector = MediumConnector()
        
        with patch('requests.get', side_effect=Exception("Network error")):
            assert connector.is_available() is False
    
    @pytest.mark.asyncio
    async def test_collect_integration(self):
        """Teste d'intégration de la méthode collect."""
        connector = MediumConnector(["AI"])
        
        # Mock de contenus collectés
        mock_contents = [
            RawContent(
                "AI Article 1", 
                "https://medium.com/ai1", 
                "medium",
                excerpt="About artificial intelligence",
                published_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
            ),
            RawContent(
                "Python Article", 
                "https://medium.com/python1", 
                "medium",
                excerpt="About Python programming",
                published_date=datetime(2024, 1, 14, tzinfo=timezone.utc)
            ),
            RawContent(
                "AI Article 2", 
                "https://medium.com/ai2", 
                "medium",
                excerpt="More about AI development",
                published_date=datetime(2024, 1, 16, tzinfo=timezone.utc)
            ),
        ]
        
        # Mock de _fetch_feed pour retourner nos contenus de test
        async def mock_fetch_feed(session, url):
            if "artificial-intelligence" in url:
                return mock_contents[:2]  # 2 premiers articles
            elif "towards-data-science" in url:
                return [mock_contents[2]]  # 3ème article
            else:
                return []
        
        with patch.object(connector, '_fetch_feed', side_effect=mock_fetch_feed):
            results = await connector.collect(limit=5)
        
        # Vérifications
        assert len(results) <= 5
        # Les articles doivent être triés par date (plus récent d'abord)
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].published_date >= results[i + 1].published_date
        
        # Vérification du filtrage par mots-clés
        ai_articles = [r for r in results if "ai" in r.excerpt.lower() or "ai" in r.title.lower()]
        assert len(ai_articles) > 0  # Au moins un article AI trouvé
    
    @pytest.mark.asyncio
    async def test_test_connection(self):
        """Teste la méthode de test de connexion."""
        connector = MediumConnector()
        
        # Mock de collect qui retourne des exemples
        sample_contents = [
            RawContent(
                "Test Article", 
                "https://medium.com/test", 
                "medium",
                author="Test Author",
                published_date=datetime.now(timezone.utc)
            )
        ]
        
        with patch.object(connector, 'collect', return_value=sample_contents):
            result = await connector.test_connection()
        
        assert isinstance(result, dict)
        assert 'available' in result
        assert 'working_feeds' in result
        assert 'total_feeds' in result
        assert 'sample_articles' in result
        assert 'errors' in result
        
        assert result['available'] is True
        assert len(result['sample_articles']) > 0
        assert result['sample_articles'][0]['title'] == "Test Article"


# Fixtures pour les tests
@pytest.fixture
def sample_rss_content():
    """Fixture avec un contenu RSS d'exemple."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Medium - AI Articles</title>
            <description>Latest AI articles from Medium</description>
            <item>
                <title>The Future of Large Language Models</title>
                <link>https://medium.com/@expert/future-llm-abc123</link>
                <description><![CDATA[
                    Large Language Models are revolutionizing AI...
                ]]></description>
                <author>AI Expert</author>
                <pubDate>Mon, 15 Jan 2024 14:30:00 GMT</pubDate>
                <guid>future-llm-abc123</guid>
                <category>AI</category>
                <category>Machine Learning</category>
            </item>
            <item>
                <title>Building AI Agents with Python</title>
                <link>https://medium.com/@dev/ai-agents-python-def456</link>
                <description>Learn how to create intelligent agents...</description>
                <author>Python Developer</author>
                <pubDate>Sun, 14 Jan 2024 09:15:00 GMT</pubDate>
                <guid>ai-agents-python-def456</guid>
                <category>Python</category>
                <category>AI</category>
            </item>
        </channel>
    </rss>'''


@pytest.fixture
def medium_connector():
    """Fixture fournissant un connecteur Medium configuré pour les tests."""
    return MediumConnector(["AI", "Machine Learning", "Python"])


@pytest.fixture
def sample_medium_contents():
    """Fixture avec des contenus Medium d'exemple."""
    return [
        RawContent(
            title="Advanced AI Techniques in 2024",
            url="https://medium.com/@expert/ai-techniques-2024",
            source="medium",
            excerpt="Exploring cutting-edge AI methodologies...",
            author="AI Researcher",
            tags=["AI", "Research", "2024"],
            published_date=datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc),
            raw_data={
                "source_feed": "https://medium.com/feed/tag/artificial-intelligence",
                "medium_post_id": "ai-techniques-2024"
            }
        ),
        RawContent(
            title="Python for Machine Learning Beginners",
            url="https://medium.com/@tutor/python-ml-beginners",
            source="medium",
            excerpt="Step-by-step guide to ML with Python...",
            author="ML Tutor",
            tags=["Python", "Machine Learning", "Tutorial"],
            published_date=datetime(2024, 1, 14, 15, 30, tzinfo=timezone.utc),
            raw_data={
                "source_feed": "https://medium.com/feed/towards-data-science",
                "medium_post_id": "python-ml-beginners"
            }
        )
    ]
