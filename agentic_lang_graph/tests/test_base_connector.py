"""
Tests unitaires pour le connecteur de base.

Ces tests vérifient le comportement de la classe BaseConnector
et ses méthodes utilitaires communes à tous les connecteurs.
"""
import pytest
from datetime import datetime, timezone
from agentic_lang_graph.src.connectors.base_connector import BaseConnector, RawContent


class MockConnector(BaseConnector):
    """Connecteur mock pour les tests de BaseConnector."""
    
    async def collect(self, limit: int = 10):
        """Implementation mock pour les tests."""
        return []
    
    def is_available(self):
        """Implementation mock pour les tests."""
        return True


class TestRawContent:
    """Tests pour la classe RawContent."""
    
    def test_raw_content_creation(self):
        """Teste la création d'un objet RawContent basique."""
        content = RawContent(
            title="Test Article",
            url="https://example.com/test",
            source="test"
        )
        
        assert content.title == "Test Article"
        assert content.url == "https://example.com/test"
        assert content.source == "test"
        assert content.tags == []  # Initialisé automatiquement
        assert content.raw_data == {}  # Initialisé automatiquement
    
    def test_raw_content_with_all_fields(self):
        """Teste la création avec tous les champs."""
        pub_date = datetime.now(timezone.utc)
        content = RawContent(
            title="Complete Article",
            url="https://example.com/complete",
            source="medium",
            content="Full article content here...",
            excerpt="Short excerpt",
            published_date=pub_date,
            author="Test Author",
            tags=["AI", "ML"],
            raw_data={"custom": "data"}
        )
        
        assert content.title == "Complete Article"
        assert content.author == "Test Author"
        assert content.tags == ["AI", "ML"]
        assert content.published_date == pub_date
        assert content.raw_data == {"custom": "data"}


class TestBaseConnector:
    """Tests pour la classe BaseConnector."""
    
    def test_connector_initialization(self):
        """Teste l'initialisation d'un connecteur."""
        keywords = ["AI", "Machine Learning"]
        connector = MockConnector("test", keywords)
        
        assert connector.source_name == "test"
        assert connector.keywords == keywords
        assert hasattr(connector, 'logger')
    
    def test_connector_without_keywords(self):
        """Teste l'initialisation sans mots-clés."""
        connector = MockConnector("test")
        assert connector.keywords == []
    
    def test_filter_by_keywords_empty_keywords(self):
        """Teste le filtrage sans mots-clés configurés."""
        connector = MockConnector("test")
        
        contents = [
            RawContent("Article 1", "url1", "test"),
            RawContent("Article 2", "url2", "test")
        ]
        
        filtered = connector.filter_by_keywords(contents)
        assert len(filtered) == 2  # Tous gardés si pas de mots-clés
    
    def test_filter_by_keywords_with_matching(self):
        """Teste le filtrage avec des mots-clés qui matchent."""
        connector = MockConnector("test", ["AI", "Python"])
        
        contents = [
            RawContent("AI Revolution", "url1", "test", excerpt="About artificial intelligence"),
            RawContent("Java Tutorial", "url2", "test", excerpt="Learn Java programming"),
            RawContent("Python Guide", "url3", "test", excerpt="Python for beginners"),
        ]
        
        filtered = connector.filter_by_keywords(contents)
        assert len(filtered) == 2  # AI Revolution et Python Guide
        assert any("AI Revolution" in c.title for c in filtered)
        assert any("Python Guide" in c.title for c in filtered)
    
    def test_filter_by_keywords_case_insensitive(self):
        """Teste que le filtrage est insensible à la casse."""
        connector = MockConnector("test", ["ai"])  # Minuscule
        
        contents = [
            RawContent("AI Article", "url1", "test"),  # Majuscule
            RawContent("machine learning", "url2", "test")
        ]
        
        filtered = connector.filter_by_keywords(contents)
        assert len(filtered) == 1
        assert filtered[0].title == "AI Article"
    
    def test_filter_by_keywords_searches_tags(self):
        """Teste que le filtrage cherche aussi dans les tags."""
        connector = MockConnector("test", ["ML"])
        
        content = RawContent(
            "Generic Title", 
            "url1", 
            "test",
            excerpt="Nothing relevant here",
            tags=["ML", "Data Science"]
        )
        
        filtered = connector.filter_by_keywords([content])
        assert len(filtered) == 1
    
    def test_validate_content_valid(self):
        """Teste la validation d'un contenu valide."""
        connector = MockConnector("test")
        
        content = RawContent(
            "Valid Article Title",
            "https://example.com/valid",
            "test"
        )
        
        assert connector.validate_content(content) is True
    
    def test_validate_content_missing_title(self):
        """Teste la validation avec titre manquant."""
        connector = MockConnector("test")
        
        content = RawContent("", "https://example.com", "test")
        assert connector.validate_content(content) is False
    
    def test_validate_content_missing_url(self):
        """Teste la validation avec URL manquante."""
        connector = MockConnector("test")
        
        content = RawContent("Valid Title", "", "test")
        assert connector.validate_content(content) is False
    
    def test_validate_content_title_too_short(self):
        """Teste la validation avec titre trop court."""
        connector = MockConnector("test")
        
        content = RawContent("Short", "https://example.com", "test")
        assert connector.validate_content(content) is False
    
    def test_clean_and_validate(self):
        """Teste le nettoyage et validation d'une liste de contenus."""
        connector = MockConnector("test")
        
        contents = [
            RawContent("  Valid Article  ", "https://example.com/1", "test"),  # À nettoyer
            RawContent("", "https://example.com/2", "test"),  # Invalide
            RawContent("Another Valid Article", "https://example.com/3", "test"),  # Valide
            RawContent("Short", "", "test")  # Invalide
        ]
        
        cleaned = connector.clean_and_validate(contents)
        
        assert len(cleaned) == 2
        assert cleaned[0].title == "Valid Article"  # Nettoyé
        assert cleaned[1].title == "Another Valid Article"


# Fixtures pour les tests d'intégration si nécessaire
@pytest.fixture
def sample_raw_contents():
    """Fixture fournissant des contenus d'exemple pour les tests."""
    return [
        RawContent(
            "Understanding Large Language Models",
            "https://medium.com/example/llm-article",
            "medium",
            excerpt="Deep dive into LLM architecture...",
            author="AI Expert",
            tags=["AI", "LLM", "NLP"],
            published_date=datetime(2024, 1, 15, tzinfo=timezone.utc)
        ),
        RawContent(
            "Python Best Practices",
            "https://medium.com/example/python-practices",
            "medium",
            excerpt="How to write better Python code...",
            author="Python Dev",
            tags=["Python", "Programming"],
            published_date=datetime(2024, 1, 14, tzinfo=timezone.utc)
        )
    ]


@pytest.fixture
def mock_connector():
    """Fixture fournissant un connecteur mock configuré."""
    return MockConnector("test", ["AI", "Python", "Machine Learning"])
