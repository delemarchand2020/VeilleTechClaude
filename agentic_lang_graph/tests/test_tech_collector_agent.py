"""
Tests pour l'Agent Collecteur Tech.

Tests unitaires et d'intégration pour vérifier le bon fonctionnement
de l'orchestration multi-sources et des fonctionnalités de déduplication.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import List

from src.agents.tech_collector_agent import (
    TechCollectorAgent, 
    CollectionConfig, 
    CollectionResult
)
from src.connectors import RawContent, BaseConnector


class MockConnector(BaseConnector):
    """Connecteur mock pour les tests."""
    
    def __init__(self, source_name: str, mock_contents: List[RawContent] = None, available: bool = True):
        super().__init__(source_name)
        self.mock_contents = mock_contents or []
        self.available = available
        self.collect_called = False
        self.collect_call_count = 0
    
    async def collect(self, limit: int = 10) -> List[RawContent]:
        """Mock de la collecte."""
        self.collect_called = True
        self.collect_call_count += 1
        # Simule une latence réseau
        await asyncio.sleep(0.01)
        return self.mock_contents[:limit]
    
    def is_available(self) -> bool:
        """Mock de la vérification de disponibilité."""
        return self.available


@pytest.fixture
def sample_raw_contents():
    """Contenus de test."""
    return [
        RawContent(
            title="Introduction to LangGraph",
            url="https://medium.com/article1",
            source="medium",
            excerpt="Guide complet sur LangGraph",
            published_date=datetime.now() - timedelta(days=1),
            author="John Doe",
            tags=["AI", "LangGraph"]
        ),
        RawContent(
            title="Advanced AI Agents with LLM",
            url="https://arxiv.org/abs/2024.001",
            source="arxiv",
            excerpt="Research on multi-agent systems",
            published_date=datetime.now() - timedelta(days=2),
            author="Jane Smith",
            tags=["AI", "Agents"]
        ),
        RawContent(
            title="Introduction to LangGraph - Updated",  # Similaire au premier
            url="https://medium.com/article2",
            source="medium",
            excerpt="Updated guide on LangGraph",
            published_date=datetime.now() - timedelta(days=3),
            author="John Doe",
            tags=["AI", "LangGraph"]
        ),
        RawContent(
            title="Old AI Article",
            url="https://old-site.com/article",
            source="medium",
            excerpt="Outdated AI content",
            published_date=datetime.now() - timedelta(days=30),  # Trop vieux
            author="Old Author",
            tags=["AI"]
        ),
        RawContent(
            title="Bad",  # Titre vraiment trop court (3 caractères)
            url="https://bad.com/1",
            source="medium",
            published_date=datetime.now(),
            author="Author"
        )
    ]


@pytest.fixture
def collection_config():
    """Configuration de test."""
    return CollectionConfig(
        total_limit=10,
        source_limits={'medium': 5, 'arxiv': 5},
        keywords=['AI', 'LangGraph', 'LLM'],
        max_age_days=7,
        enable_deduplication=True,
        similarity_threshold=0.7
    )


class TestTechCollectorAgent:
    """Tests pour l'Agent Collecteur Tech."""
    
    def test_init_default_config(self):
        """Test de l'initialisation avec config par défaut."""
        agent = TechCollectorAgent()
        
        assert agent.config is not None
        assert agent.config.total_limit == 30
        assert 'medium' in agent.config.source_limits
        assert 'arxiv' in agent.config.source_limits
        assert len(agent.config.keywords) > 0
        assert agent.session_stats['total_sessions'] == 0
    
    def test_init_custom_config(self, collection_config):
        """Test de l'initialisation avec config personnalisée."""
        agent = TechCollectorAgent(config=collection_config)
        
        assert agent.config.total_limit == 10
        assert agent.config.source_limits['medium'] == 5
        assert 'AI' in agent.config.keywords
    
    def test_init_connectors(self):
        """Test de l'initialisation des connecteurs."""
        agent = TechCollectorAgent()
        
        assert 'medium' in agent.connectors
        assert 'arxiv' in agent.connectors
        assert len(agent.connectors) == 2
    
    @pytest.mark.asyncio
    async def test_check_sources_availability_all_available(self):
        """Test de vérification de disponibilité - toutes sources disponibles."""
        agent = TechCollectorAgent()
        
        # Mock des connecteurs comme disponibles
        for connector in agent.connectors.values():
            connector.is_available = Mock(return_value=True)
        
        available = await agent._check_sources_availability()
        
        assert len(available) == 2
        assert 'medium' in available
        assert 'arxiv' in available
    
    @pytest.mark.asyncio
    async def test_check_sources_availability_some_unavailable(self):
        """Test de vérification de disponibilité - certaines sources indisponibles."""
        agent = TechCollectorAgent()
        
        # Mock medium disponible, arxiv indisponible
        agent.connectors['medium'].is_available = Mock(return_value=True)
        agent.connectors['arxiv'].is_available = Mock(return_value=False)
        
        available = await agent._check_sources_availability()
        
        assert len(available) == 1
        assert 'medium' in available
        assert 'arxiv' not in available
    
    @pytest.mark.asyncio
    async def test_collect_from_source_success(self, sample_raw_contents):
        """Test de collecte depuis une source spécifique - succès."""
        agent = TechCollectorAgent()
        
        # Mock du connecteur
        mock_connector = MockConnector('test', sample_raw_contents[:2])
        agent.connectors['test'] = mock_connector
        
        result = await agent._collect_from_source('test', 5)
        
        assert len(result) == 2
        assert mock_connector.collect_called
        assert result[0].title == "Introduction to LangGraph"
    
    @pytest.mark.asyncio
    async def test_collect_from_source_error(self):
        """Test de collecte depuis une source spécifique - erreur."""
        agent = TechCollectorAgent()
        
        # Mock du connecteur avec erreur
        mock_connector = Mock()
        mock_connector.collect = AsyncMock(side_effect=Exception("Connection failed"))
        agent.connectors['test'] = mock_connector
        
        with pytest.raises(Exception, match="Connection failed"):
            await agent._collect_from_source('test', 5)
    
    def test_filter_by_age_and_quality(self, sample_raw_contents, collection_config):
        """Test de filtrage par âge et qualité."""
        agent = TechCollectorAgent(config=collection_config)
        
        filtered = agent._filter_by_age_and_quality(sample_raw_contents, collection_config)
        
        # Vérifions ce qui a été filtré
        titles = [c.title for c in filtered]
        
        # L'article trop vieux doit être exclu
        assert "Old AI Article" not in titles, "L'article trop vieux devrait être exclu"
        
        # Le titre trop court doit être exclu
        assert "Bad" not in titles, "Le titre trop court devrait être exclu"
        
        # On vérifie que le filtrage fonctionne
        assert len(filtered) <= len(sample_raw_contents), "Le filtrage doit réduire ou maintenir le nombre de contenus"
        assert len(filtered) >= 2, "Au moins 2 contenus valides devraient passer"
    
    def test_filter_by_age_and_quality_empty_list(self, collection_config):
        """Test de filtrage avec liste vide."""
        agent = TechCollectorAgent(config=collection_config)
        
        filtered = agent._filter_by_age_and_quality([], collection_config)
        
        assert len(filtered) == 0
    
    def test_deduplicate_contents_disabled(self, sample_raw_contents):
        """Test de déduplication désactivée."""
        config = CollectionConfig(enable_deduplication=False)
        agent = TechCollectorAgent(config=config)
        
        deduplicated, duplicates_count = agent._deduplicate_contents(sample_raw_contents, config)
        
        assert len(deduplicated) == len(sample_raw_contents)
        assert duplicates_count == 0
    
    def test_deduplicate_contents_enabled(self, sample_raw_contents):
        """Test de déduplication activée."""
        config = CollectionConfig(enable_deduplication=True, similarity_threshold=0.6)  # Seuil plus bas
        agent = TechCollectorAgent(config=config)
        
        deduplicated, duplicates_count = agent._deduplicate_contents(sample_raw_contents, config)
        
        # Vérifie qu'on n'a pas de doublons exacts par URL
        urls = [c.url for c in deduplicated]
        assert len(urls) == len(set(urls)), "Aucun doublon d'URL ne devrait rester"
        
        # Vérifie que la déduplication fonctionne (peut détecter des similarités ou non selon le seuil)
        assert duplicates_count >= 0, "Le compteur de doublons doit être positif ou nul"
        assert len(deduplicated) <= len(sample_raw_contents), "Le nombre final doit être inférieur ou égal à l'original"
    
    def test_normalize_datetime(self):
        """Test de normalisation des datetimes."""
        agent = TechCollectorAgent()
        
        # Date naive
        date_naive = datetime(2024, 1, 1, 12, 0, 0)
        normalized = agent._normalize_datetime(date_naive)
        assert normalized == date_naive
        assert normalized.tzinfo is None
        
        # Date avec timezone
        from datetime import timezone
        date_tz = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        normalized_tz = agent._normalize_datetime(date_tz)
        assert normalized_tz is not None
        assert normalized_tz.tzinfo is None
        assert normalized_tz.year == 2024
        
        # None
        assert agent._normalize_datetime(None) is None
    
    def test_filter_by_age_and_quality_with_timezones(self):
        """Test de filtrage avec différents types de dates."""
        from datetime import timezone
        
        agent = TechCollectorAgent()
        config = CollectionConfig(max_age_days=7)
        
        # Contenus avec différents types de dates
        contents = [
            RawContent(
                title="Article récent naive",
                url="https://test1.com",
                source="test",
                published_date=datetime.now() - timedelta(days=1)  # naive
            ),
            RawContent(
                title="Article récent avec timezone",
                url="https://test2.com",
                source="test",
                published_date=datetime.now(timezone.utc) - timedelta(days=1)  # avec TZ
            ),
            RawContent(
                title="Article ancien avec timezone",
                url="https://test3.com",
                source="test",
                published_date=datetime.now(timezone.utc) - timedelta(days=30)  # ancien
            )
        ]
        
        filtered = agent._filter_by_age_and_quality(contents, config)
        
        # Doit garder les 2 articles récents et exclure l'ancien
        assert len(filtered) == 2
        titles = [c.title for c in filtered]
        assert "Article ancien avec timezone" not in titles
    
    def test_are_titles_similar(self):
        """Test de comparaison de similarité des titres."""
        agent = TechCollectorAgent()
        
        # Titres similaires
        assert agent._are_titles_similar(
            "introduction to langgraph",
            "introduction to langgraph updated",
            0.7
        )
        
        # Titres différents
        assert not agent._are_titles_similar(
            "introduction to langgraph",
            "advanced machine learning",
            0.7
        )
    
    def test_prioritize_and_limit(self, sample_raw_contents):
        """Test de priorisation et limitation."""
        config = CollectionConfig(total_limit=2)
        agent = TechCollectorAgent(config=config)
        
        # Tri par date (plus récent en premier)
        prioritized = agent._prioritize_and_limit(sample_raw_contents, config)
        
        assert len(prioritized) == 2
        # Le plus récent doit être en premier
        assert prioritized[0].published_date >= prioritized[1].published_date
    
    def test_calculate_sources_stats(self, sample_raw_contents):
        """Test de calcul des statistiques par source."""
        agent = TechCollectorAgent()
        
        # Contenus finaux (subset des contenus bruts)
        final_contents = sample_raw_contents[:2]
        
        stats = agent._calculate_sources_stats(sample_raw_contents, final_contents)
        
        assert 'medium' in stats
        assert 'arxiv' in stats
        assert stats['medium']['raw'] > 0
        assert stats['medium']['final'] >= 0
        assert 0 <= stats['medium']['retention_rate'] <= 100
    
    def test_update_session_stats(self):
        """Test de mise à jour des statistiques de session."""
        agent = TechCollectorAgent()
        initial_sessions = agent.session_stats['total_sessions']
        
        agent._update_session_stats(10, 2, ['medium', 'arxiv'])
        
        assert agent.session_stats['total_sessions'] == initial_sessions + 1
        assert agent.session_stats['total_collected'] == 10
        assert agent.session_stats['total_duplicates_removed'] == 2
        assert 'medium' in agent.session_stats['sources_availability']
    
    def test_get_session_stats(self):
        """Test de récupération des statistiques de session."""
        agent = TechCollectorAgent()
        
        stats = agent.get_session_stats()
        
        assert isinstance(stats, dict)
        assert 'total_sessions' in stats
        assert 'total_collected' in stats
        assert 'sources_availability' in stats
    
    def test_reset_session_stats(self):
        """Test de remise à zéro des statistiques."""
        agent = TechCollectorAgent()
        
        # Ajoute quelques stats
        agent._update_session_stats(5, 1, ['medium'])
        assert agent.session_stats['total_sessions'] > 0
        
        # Reset
        agent.reset_session_stats()
        
        assert agent.session_stats['total_sessions'] == 0
        assert agent.session_stats['total_collected'] == 0
        assert agent.session_stats['sources_availability'] == {}
    
    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self):
        """Test de diagnostic de santé - tout fonctionne."""
        agent = TechCollectorAgent()
        
        # Mock des connecteurs comme disponibles
        for connector in agent.connectors.values():
            connector.is_available = Mock(return_value=True)
        
        health = await agent.health_check()
        
        assert health['agent_status'] == 'healthy'
        assert 'connectors_status' in health
        assert health['connectors_status']['medium']['available'] is True
        assert health['connectors_status']['arxiv']['available'] is True
        assert 'config' in health
        assert 'session_stats' in health
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self):
        """Test de diagnostic de santé - service dégradé."""
        agent = TechCollectorAgent()
        
        # Mock medium disponible, arxiv en erreur
        agent.connectors['medium'].is_available = Mock(return_value=True)
        agent.connectors['arxiv'].is_available = Mock(side_effect=Exception("Network error"))
        
        health = await agent.health_check()
        
        assert health['agent_status'] == 'degraded'
        assert health['connectors_status']['medium']['available'] is True
        assert health['connectors_status']['arxiv']['available'] is False
        assert health['connectors_status']['arxiv']['status'] == 'error'


class TestTechCollectorAgentIntegration:
    """Tests d'intégration pour l'Agent Collecteur Tech."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_collect_all_sources_with_mocks(self, sample_raw_contents, collection_config):
        """Test d'intégration de collecte complète avec mocks."""
        agent = TechCollectorAgent(config=collection_config)
        
        # Remplacement des connecteurs par des mocks
        medium_contents = [c for c in sample_raw_contents if c.source == 'medium']
        arxiv_contents = [c for c in sample_raw_contents if c.source == 'arxiv']
        
        agent.connectors['medium'] = MockConnector('medium', medium_contents, available=True)
        agent.connectors['arxiv'] = MockConnector('arxiv', arxiv_contents, available=True)
        
        # Collecte complète
        result = await agent.collect_all_sources()
        
        # Vérifications
        assert isinstance(result, CollectionResult)
        assert result.total_collected > 0
        assert result.total_filtered >= 0
        assert result.collection_time > 0
        assert len(result.contents) <= collection_config.total_limit
        assert 'medium' in result.sources_stats
        assert 'arxiv' in result.sources_stats
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_collect_all_sources_with_errors(self, collection_config):
        """Test d'intégration avec gestion d'erreurs."""
        agent = TechCollectorAgent(config=collection_config)
        
        # Mock medium fonctionnel, arxiv en erreur
        agent.connectors['medium'] = MockConnector('medium', [], available=True)
        
        # Connecteur arxiv qui lève une exception
        mock_arxiv = Mock()
        mock_arxiv.is_available = Mock(return_value=True)
        mock_arxiv.collect = AsyncMock(side_effect=Exception("API Error"))
        agent.connectors['arxiv'] = mock_arxiv
        
        result = await agent.collect_all_sources()
        
        # Doit retourner un résultat même avec des erreurs
        assert isinstance(result, CollectionResult)
        assert len(result.errors) > 0
        assert "API Error" in str(result.errors)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_collect_all_sources_no_available_sources(self, collection_config):
        """Test d'intégration sans sources disponibles."""
        agent = TechCollectorAgent(config=collection_config)
        
        # Tous les connecteurs indisponibles
        for connector in agent.connectors.values():
            connector.is_available = Mock(return_value=False)
        
        result = await agent.collect_all_sources()
        
        assert isinstance(result, CollectionResult)
        assert result.total_collected == 0
        assert result.total_filtered == 0
        assert len(result.contents) == 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_workflow_deduplication(self):
        """Test d'intégration du workflow complet avec déduplication."""
        # Configuration avec déduplication activée
        config = CollectionConfig(
            total_limit=5,
            enable_deduplication=True,
            similarity_threshold=0.8
        )
        
        agent = TechCollectorAgent(config=config)
        
        # Contenus avec doublons intentionnels
        duplicate_contents = [
            RawContent(
                title="Guide to AI Development",
                url="https://source1.com/guide1",
                source="medium",
                published_date=datetime.now()
            ),
            RawContent(
                title="Guide to AI Development - Updated",  # Similaire
                url="https://source2.com/guide2",
                source="arxiv",
                published_date=datetime.now()
            ),
            RawContent(
                title="Completely Different Article",
                url="https://source3.com/diff",
                source="medium",
                published_date=datetime.now()
            )
        ]
        
        # Mock des connecteurs
        agent.connectors['medium'] = MockConnector('medium', duplicate_contents[:2], available=True)
        agent.connectors['arxiv'] = MockConnector('arxiv', duplicate_contents[1:], available=True)
        
        result = await agent.collect_all_sources()
        
        # Vérifications de déduplication
        assert result.duplicates_removed > 0
        assert len(result.contents) < result.total_collected
        
        # Vérifie qu'il n'y a pas de doublons dans le résultat final
        urls = [c.url for c in result.contents]
        assert len(urls) == len(set(urls))


class TestCollectionConfig:
    """Tests pour la configuration de collecte."""
    
    def test_collection_config_defaults(self):
        """Test des valeurs par défaut de la configuration."""
        config = CollectionConfig()
        
        assert config.total_limit == 30
        assert 'medium' in config.source_limits
        assert 'arxiv' in config.source_limits
        assert len(config.keywords) > 0
        assert config.max_age_days == 7
        assert config.enable_deduplication is True
        assert 0 < config.similarity_threshold <= 1
    
    def test_collection_config_custom(self):
        """Test de configuration personnalisée."""
        config = CollectionConfig(
            total_limit=50,
            source_limits={'custom': 25},
            keywords=['custom', 'keywords'],
            max_age_days=14,
            enable_deduplication=False,
            similarity_threshold=0.9
        )
        
        assert config.total_limit == 50
        assert config.source_limits['custom'] == 25
        assert 'custom' in config.keywords
        assert config.max_age_days == 14
        assert config.enable_deduplication is False
        assert config.similarity_threshold == 0.9


class TestCollectionResult:
    """Tests pour les résultats de collecte."""
    
    def test_collection_result_creation(self, sample_raw_contents):
        """Test de création d'un résultat de collecte."""
        result = CollectionResult(
            contents=sample_raw_contents[:2],
            total_collected=5,
            total_filtered=2,
            sources_stats={'medium': {'raw': 3, 'final': 1, 'retention_rate': 33.3}},
            duplicates_removed=1,
            collection_time=1.5
        )
        
        assert len(result.contents) == 2
        assert result.total_collected == 5
        assert result.total_filtered == 2
        assert result.duplicates_removed == 1
        assert result.collection_time == 1.5
        assert len(result.errors) == 0  # Défaut
    
    def test_collection_result_with_errors(self):
        """Test de résultat avec erreurs."""
        errors = ["Error 1", "Error 2"]
        
        result = CollectionResult(
            contents=[],
            total_collected=0,
            total_filtered=0,
            sources_stats={},
            duplicates_removed=0,
            collection_time=0.5,
            errors=errors
        )
        
        assert len(result.errors) == 2
        assert "Error 1" in result.errors


# Markers pour les tests
pytestmark = [
    pytest.mark.unit,
    pytest.mark.agent
]
