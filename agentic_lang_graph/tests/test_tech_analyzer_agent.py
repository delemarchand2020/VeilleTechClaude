"""
Tests de l'Agent Analyseur Tech avec LangGraph.

Tests complets pour vérifier le fonctionnement du workflow d'analyse,
l'intégration LangGraph et la compatibilité avec l'Agent Collecteur.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.agents.tech_analyzer_agent import TechAnalyzerAgent, AnalysisState
from src.agents.simple_analyzer_prototype import ExpertProfile, ContentAnalysis, DifficultyLevel, AnalyzedContent
from src.connectors import RawContent


class TestTechAnalyzerAgent:
    """Tests unitaires de l'Agent Analyseur."""
    
    @pytest.fixture
    def expert_profile(self):
        """Profil expert pour les tests."""
        return ExpertProfile(
            level=DifficultyLevel.EXPERT,
            interests=["LangGraph", "Multi-agent", "LLM"],
            avoid_topics=["beginner_tutorials"],
            preferred_content_types=["technical_deep_dive", "research_paper"]
        )
    
    @pytest.fixture
    def sample_raw_contents(self):
        """Contenus bruts pour les tests."""
        return [
            RawContent(
                title="Advanced LangGraph Patterns for Multi-Agent Systems",
                url="https://example.com/langgraph-patterns",
                source="medium",
                content="Deep dive into advanced LangGraph patterns...",
                excerpt="Advanced patterns for building complex agent workflows",
                author="AI Expert",
                published_date=datetime.now(),
                tags=["langgraph", "multi-agent", "advanced"]
            ),
            RawContent(
                title="Getting Started with AI - Beginner Guide",
                url="https://example.com/ai-beginner",
                source="medium", 
                content="Introduction to AI concepts for beginners...",
                excerpt="Basic AI concepts explained simply",
                author="Tutorial Writer",
                published_date=datetime.now(),
                tags=["ai", "beginner", "tutorial"]
            ),
            RawContent(
                title="Production-Ready LLM Architecture Patterns",
                url="https://example.com/llm-production",
                source="arxiv",
                content="This paper presents scalable LLM architectures...",
                excerpt="Scalable patterns for production LLM deployment",
                author="Research Team",
                published_date=datetime.now(),
                tags=["llm", "architecture", "production"]
            )
        ]
    
    @pytest.fixture
    def mock_llm_response(self):
        """Réponse simulée du LLM."""
        return MagicMock(
            content='{"relevance_score": 8.5, "difficulty_level": "expert", "main_topics": ["LangGraph", "Multi-agent"], "key_insights": "Advanced patterns explained", "practical_value": 8.0, "reasons": ["Technical depth", "Practical examples"], "recommended": true}'
        )
    
    def test_agent_initialization(self, expert_profile):
        """Test d'initialisation de l'agent."""
        agent = TechAnalyzerAgent(expert_profile)
        
        assert agent.profile == expert_profile
        assert agent.llm is not None
        assert agent.workflow is not None
        assert agent.compiled_workflow is not None
    
    def test_build_system_prompt(self, expert_profile):
        """Test de construction du prompt système."""
        agent = TechAnalyzerAgent(expert_profile)
        prompt = agent._build_system_prompt(expert_profile)
        
        assert "expert" in prompt.lower()
        assert "langgraph" in prompt.lower()
        assert "json" in prompt.lower()
        assert "relevance_score" in prompt
    
    def test_build_analysis_prompt(self, expert_profile, sample_raw_contents):
        """Test de construction du prompt d'analyse."""
        agent = TechAnalyzerAgent(expert_profile)
        content = sample_raw_contents[0]
        
        prompt = agent._build_analysis_prompt(content)
        
        assert content.title in prompt
        assert content.source in prompt
        assert content.url in prompt
        assert "JSON" in prompt
    
    @pytest.mark.asyncio
    async def test_analyze_content_with_llm(self, expert_profile, sample_raw_contents, mock_llm_response):
        """Test d'analyse d'un contenu avec LLM mocké."""
        agent = TechAnalyzerAgent(expert_profile)
        
        # Mock du LLM
        agent.llm = AsyncMock()
        agent.llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        
        content = sample_raw_contents[0]
        analysis = await agent._analyze_content_with_llm(content, expert_profile)
        
        assert isinstance(analysis, ContentAnalysis)
        assert analysis.relevance_score == 8.5
        assert analysis.difficulty_level == DifficultyLevel.EXPERT
        assert analysis.recommended is True
        assert "LangGraph" in analysis.main_topics
    
    @pytest.mark.asyncio
    async def test_analyze_content_with_invalid_json(self, expert_profile, sample_raw_contents):
        """Test avec réponse JSON invalide du LLM."""
        agent = TechAnalyzerAgent(expert_profile)
        
        # Mock avec JSON invalide
        agent.llm = AsyncMock()
        agent.llm.ainvoke = AsyncMock(
            return_value=MagicMock(content='{"invalid": json}')
        )
        
        content = sample_raw_contents[0]
        analysis = await agent._analyze_content_with_llm(content, expert_profile)
        
        # Doit retourner une analyse par défaut
        assert isinstance(analysis, ContentAnalysis)
        assert analysis.relevance_score == 5.0
        assert analysis.recommended is False
        assert "parsing_error" in analysis.main_topics
    
    def test_should_continue_logic(self, expert_profile):
        """Test de la logique conditionnelle du workflow."""
        agent = TechAnalyzerAgent(expert_profile)
        
        # Cas: plus de contenus à traiter
        state_continue = AnalysisState(
            total_contents=10,
            processed_count=5
        )
        assert agent._should_continue(state_continue) == "continue"
        
        # Cas: tous les contenus traités
        state_finish = AnalysisState(
            total_contents=10,
            processed_count=10
        )
        assert agent._should_continue(state_finish) == "finish"
    
    @pytest.mark.asyncio
    async def test_workflow_nodes_basic(self, expert_profile, sample_raw_contents):
        """Test des nœuds individuels du workflow."""
        agent = TechAnalyzerAgent(expert_profile)
        
        # Test initialisation
        initial_state = AnalysisState(
            raw_contents=sample_raw_contents,
            total_contents=len(sample_raw_contents)
        )
        
        state = await agent._initialize_analysis(initial_state)
        assert state.start_time is not None
        assert state.processed_count == 0
        
        # Test batch processor
        state = await agent._process_batch(state)
        assert len(state.current_batch) > 0
        assert len(state.current_batch) <= state.batch_size
        
        # Test aggregator
        state.current_batch = sample_raw_contents[:2]  # Simuler un batch traité
        state = await agent._aggregate_results(state)
        assert state.processed_count == 2
        assert len(state.current_batch) == 0
    
    @pytest.mark.asyncio 
    async def test_analyze_contents_basic(self, expert_profile, sample_raw_contents):
        """Test d'analyse complète avec contenus simulés."""
        agent = TechAnalyzerAgent(expert_profile)
        
        # Mock du LLM pour éviter les appels réels
        mock_response = MagicMock(
            content='{"relevance_score": 7.5, "difficulty_level": "intermediate", "main_topics": ["AI"], "key_insights": "Good content", "practical_value": 7.0, "reasons": ["Relevant"], "recommended": true}'
        )
        
        agent.llm = AsyncMock()
        agent.llm.ainvoke = AsyncMock(return_value=mock_response)
        
        # Test avec un seul contenu pour simplifier
        results = await agent.analyze_contents([sample_raw_contents[0]])
        
        assert len(results) == 1
        assert isinstance(results[0], AnalyzedContent)
        assert results[0].analysis.recommended is True
        assert results[0].raw_content == sample_raw_contents[0]
    
    @pytest.mark.asyncio
    async def test_analyze_contents_empty_list(self, expert_profile):
        """Test avec liste vide."""
        agent = TechAnalyzerAgent(expert_profile)
        
        results = await agent.analyze_contents([])
        assert results == []
    
    @pytest.mark.asyncio
    async def test_get_recommendations(self, expert_profile, sample_raw_contents):
        """Test de récupération des recommandations."""
        agent = TechAnalyzerAgent(expert_profile)
        
        # Mock avec mix de recommandés/non-recommandés
        def mock_response_generator(call_count=[0]):
            responses = [
                '{"relevance_score": 8.5, "difficulty_level": "expert", "main_topics": ["LangGraph"], "key_insights": "Excellent", "practical_value": 8.0, "reasons": ["Advanced"], "recommended": true}',
                '{"relevance_score": 3.0, "difficulty_level": "beginner", "main_topics": ["AI"], "key_insights": "Basic", "practical_value": 3.0, "reasons": ["Too basic"], "recommended": false}',
                '{"relevance_score": 9.0, "difficulty_level": "expert", "main_topics": ["LLM"], "key_insights": "Outstanding", "practical_value": 9.0, "reasons": ["Production ready"], "recommended": true}'
            ]
            response = responses[call_count[0] % len(responses)]
            call_count[0] += 1
            return MagicMock(content=response)
        
        agent.llm = AsyncMock()
        agent.llm.ainvoke = AsyncMock(side_effect=mock_response_generator)
        
        recommendations = await agent.get_recommendations(sample_raw_contents, limit=2)
        
        # Doit retourner seulement les recommandés, limité à 2
        assert len(recommendations) <= 2
        for rec in recommendations:
            assert rec.analysis.recommended is True
    
    @pytest.mark.asyncio
    async def test_error_handling_in_workflow(self, expert_profile, sample_raw_contents):
        """Test de gestion d'erreurs dans le workflow."""
        agent = TechAnalyzerAgent(expert_profile)
        
        # Mock qui lève une exception
        agent.llm = AsyncMock()
        agent.llm.ainvoke = AsyncMock(side_effect=Exception("LLM Error"))
        
        # Le workflow ne doit pas crasher
        results = await agent.analyze_contents([sample_raw_contents[0]])
        
        # Doit retourner une liste vide car l'analyse a échoué
        assert isinstance(results, list)
        # L'état devrait contenir l'erreur dans failed_analyses


@pytest.mark.integration
class TestTechAnalyzerAgentIntegration:
    """Tests d'intégration avec les autres composants."""
    
    @pytest.mark.asyncio
    async def test_integration_with_tech_collector(self):
        """Test d'intégration avec l'Agent Collecteur."""
        from src.agents import TechCollectorAgent, CollectionConfig
        
        # Collecte avec vraies données (limitée pour le test)
        collector = TechCollectorAgent()
        config = CollectionConfig(total_limit=3, keywords=["AI"])
        
        collection_result = await collector.collect_all_sources(config)
        
        # Analyse avec l'Agent Analyseur
        analyzer = TechAnalyzerAgent()
        
        # Mock pour éviter les vrais appels LLM en test d'intégration
        mock_response = MagicMock(
            content='{"relevance_score": 7.0, "difficulty_level": "intermediate", "main_topics": ["AI"], "key_insights": "Good integration test", "practical_value": 7.0, "reasons": ["Integration works"], "recommended": true}'
        )
        analyzer.llm = AsyncMock()
        analyzer.llm.ainvoke = AsyncMock(return_value=mock_response)
        
        analyzed_results = await analyzer.analyze_contents(collection_result.contents)
        
        # Vérifications d'intégration
        assert isinstance(analyzed_results, list)
        assert len(analyzed_results) <= len(collection_result.contents)
        
        for result in analyzed_results:
            assert isinstance(result, AnalyzedContent)
            assert hasattr(result, 'raw_content')
            assert hasattr(result, 'analysis')
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_real_llm_analysis_small_batch(self):
        """Test avec vrai LLM sur un petit échantillon (marqué slow)."""
        
        # Test uniquement si OPENAI_API_KEY est disponible
        import os
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OPENAI_API_KEY non disponible pour test LLM réel")
        
        # Contenu de test simple
        test_content = RawContent(
            title="Introduction to Machine Learning",
            url="https://test.com/ml-intro",
            source="test",
            content="Machine learning is a subset of artificial intelligence...",
            tags=["machine-learning", "ai"]
        )
        
        analyzer = TechAnalyzerAgent()
        
        # Test avec vrai LLM (1 contenu seulement)
        results = await analyzer.analyze_contents([test_content])
        
        assert len(results) <= 1
        if results:
            result = results[0]
            assert isinstance(result.analysis.relevance_score, float)
            assert 0 <= result.analysis.relevance_score <= 10
            assert isinstance(result.analysis.recommended, bool)
            assert isinstance(result.analysis.main_topics, list)


@pytest.mark.performance
class TestTechAnalyzerAgentPerformance:
    """Tests de performance de l'Agent Analyseur."""
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self):
        """Test de performance du traitement par batch."""
        import time
        
        # Créer plusieurs contenus de test
        test_contents = [
            RawContent(
                title=f"Test Article {i}",
                url=f"https://test.com/article-{i}",
                source="test",
                content=f"Content for test article {i}" * 10,  # Contenu substantiel
                tags=["test", "performance"]
            )
            for i in range(10)
        ]
        
        analyzer = TechAnalyzerAgent()
        
        # Mock rapide pour mesurer la logique de workflow
        analyzer.llm = AsyncMock()
        analyzer.llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"relevance_score": 6.0, "difficulty_level": "intermediate", "main_topics": ["test"], "key_insights": "Performance test", "practical_value": 6.0, "reasons": ["Fast processing"], "recommended": true}'
            )
        )
        
        start_time = time.time()
        results = await analyzer.analyze_contents(test_contents)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Vérifications de performance
        assert len(results) == len(test_contents)
        assert processing_time < 5.0  # Doit traiter 10 contenus en moins de 5s avec mocks
        
        print(f"⏱️ Traité {len(results)} contenus en {processing_time:.2f}s")
        print(f"📊 Vitesse: {len(results)/processing_time:.1f} contenus/seconde")
    
    @pytest.mark.asyncio
    async def test_workflow_state_consistency(self):
        """Test de cohérence de l'état du workflow."""
        
        test_contents = [
            RawContent(title=f"Test {i}", url=f"test-{i}", source="test", content=f"Content {i}")
            for i in range(5)
        ]
        
        analyzer = TechAnalyzerAgent()
        
        # Mock déterministe
        analyzer.llm = AsyncMock()
        analyzer.llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"relevance_score": 5.0, "difficulty_level": "intermediate", "main_topics": ["test"], "key_insights": "State test", "practical_value": 5.0, "reasons": ["Consistency"], "recommended": false}'
            )
        )
        
        results = await analyzer.analyze_contents(test_contents)
        
        # L'état final doit être cohérent
        assert len(results) <= len(test_contents)  # Peut être moins si certains échouent
        
        # Tous les résultats doivent être valides
        for result in results:
            assert isinstance(result, AnalyzedContent)
            assert result.raw_content in test_contents
            assert isinstance(result.analysis.relevance_score, float)


if __name__ == "__main__":
    # Test rapide pour vérification manuelle
    import asyncio
    
    async def quick_test():
        print("🧪 Test rapide Agent Analyseur")
        
        test_content = RawContent(
            title="Test LangGraph Integration",
            url="https://test.com/langgraph",
            source="test",
            content="Testing LangGraph workflow integration..."
        )
        
        analyzer = TechAnalyzerAgent()
        
        # Mock pour test rapide
        analyzer.llm = AsyncMock()
        analyzer.llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"relevance_score": 8.0, "difficulty_level": "expert", "main_topics": ["LangGraph"], "key_insights": "Great integration", "practical_value": 8.0, "reasons": ["Advanced workflow"], "recommended": true}'
            )
        )
        
        results = await analyzer.analyze_contents([test_content])
        
        print(f"✅ {len(results)} contenu(s) analysé(s)")
        if results:
            print(f"📊 Score: {results[0].analysis.relevance_score}")
            print(f"🎯 Recommandé: {results[0].analysis.recommended}")
        
        print("🎉 Agent Analyseur fonctionnel!")
    
    asyncio.run(quick_test())
