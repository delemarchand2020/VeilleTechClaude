"""
Tests unitaires pour le connecteur ArXiv.

Tests essentiels pour vérifier le fonctionnement du ArxivConnector.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from agentic_lang_graph.src.connectors.arxiv_connector import ArxivConnector
from agentic_lang_graph.src.connectors.base_connector import RawContent


class TestArxivConnector:
    """Tests pour la classe ArxivConnector."""
    
    def test_connector_initialization(self):
        """Teste l'initialisation du connecteur ArXiv."""
        keywords = ["transformer", "attention"]
        categories = ["cs.AI", "cs.CL"]
        connector = ArxivConnector(keywords, categories)
        
        assert connector.source_name == "arxiv"
        assert connector.keywords == keywords
        assert connector.categories == categories
        assert connector.base_url == "http://export.arxiv.org/api/query"
        assert len(connector.search_keywords) > len(keywords)
        assert "transformer" in connector.search_keywords
        assert "large language model" in connector.search_keywords
    
    def test_extract_arxiv_id(self):
        """Teste l'extraction de l'ID ArXiv."""
        connector = ArxivConnector()
        
        # URL standard ArXiv
        url1 = "http://arxiv.org/abs/2401.12345v1"
        assert connector._extract_arxiv_id(url1) == "2401.12345v1"
        
        # URL invalide
        url2 = "https://example.com/paper"
        assert connector._extract_arxiv_id(url2) == ""
    
    @pytest.mark.asyncio
    async def test_execute_search_success(self):
        """Teste l'exécution réussie d'une recherche ArXiv."""
        connector = ArxivConnector()
        
        # Mock de la réponse XML ArXiv
        mock_xml_response = '''<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <id>http://arxiv.org/abs/2401.12345v1</id>
                <title>Large Language Models: A Survey</title>
                <summary>This paper provides a comprehensive survey of large language models...</summary>
                <published>2024-01-15T09:00:00Z</published>
                <author>
                    <name>John Researcher</name>
                </author>
                <category term="cs.AI"/>
            </entry>
        </feed>'''
        
        # Mock de la session HTTP
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_xml_response)
        
        mock_session = Mock()
        mock_session.get = Mock()
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
        
        # Test
        query = "cat:cs.AI"
        papers = await connector._execute_search(mock_session, query, 10)
        
        assert len(papers) == 1
        paper = papers[0]
        assert paper.title == "Large Language Models: A Survey"
        assert paper.url == "http://arxiv.org/abs/2401.12345v1"
        assert paper.source == "arxiv"
        assert "cs.AI" in paper.tags
        assert paper.raw_data['arxiv_id'] == '2401.12345v1'
    
    def test_is_available(self):
        """Teste la vérification de disponibilité."""
        connector = ArxivConnector()
        
        with patch('requests.get') as mock_get:
            # Mock d'une réponse ArXiv valide
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'
            mock_get.return_value = mock_response
            
            assert connector.is_available() is True
    
    @pytest.mark.asyncio
    async def test_collect_integration(self):
        """Test d'intégration de la méthode collect."""
        connector = ArxivConnector(["transformer"], categories=["cs.AI"])
        
        # Mock de papers collectés
        mock_papers = [
            RawContent(
                "Transformer Architecture Analysis",
                "http://arxiv.org/abs/2401.001",
                "arxiv",
                content="This paper analyzes transformer architectures...",
                published_date=datetime(2024, 1, 16, tzinfo=timezone.utc),
                raw_data={'arxiv_id': '2401.001'}
            )
        ]
        
        # Mock de _execute_search
        async def mock_execute_search(session, query, max_results):
            return mock_papers if "cs.AI" in query or "transformer" in query else []
        
        with patch.object(connector, '_execute_search', side_effect=mock_execute_search):
            results = await connector.collect(limit=5)
        
        assert len(results) <= 5
        assert len(results) > 0
        # Vérification qu'on a des papers avec "transformer"
        transformer_papers = [
            r for r in results 
            if "transformer" in r.title.lower() or "transformer" in r.content.lower()
        ]
        assert len(transformer_papers) > 0


# Fixtures pour les tests
@pytest.fixture
def arxiv_connector():
    """Fixture fournissant un connecteur ArXiv configuré pour les tests."""
    return ArxivConnector(["transformer", "attention"], ["cs.AI", "cs.CL"])
