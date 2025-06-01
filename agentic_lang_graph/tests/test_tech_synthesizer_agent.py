"""
Tests pour l'Agent Synthétiseur Tech.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.agents.tech_synthesizer_agent import TechSynthesizerAgent
from src.agents.tech_analyzer_agent import AnalyzedContent, ContentAnalysis, DifficultyLevel
from src.connectors.base_connector import RawContent


class TestTechSynthesizerAgent:
    
    @pytest.fixture
    def sample_analyzed_articles(self):
        """Articles analysés pour les tests."""
        
        # Article 1 - Recherche avancée
        content1 = RawContent(
            title="Advanced Multi-Agent Systems with LangGraph",
            url="https://arxiv.org/abs/2024.001",
            source="arxiv",
            content="This paper presents novel approaches to multi-agent orchestration using LangGraph framework...",
            excerpt="Novel multi-agent orchestration with LangGraph",
            published_date=datetime.now()
        )
        
        analysis1 = ContentAnalysis(
            relevance_score=0.9,
            difficulty_level=DifficultyLevel.EXPERT,
            main_topics=["multi-agent", "LangGraph", "orchestration"],
            key_insights="Advanced patterns for production multi-agent systems",
            practical_value=0.85,
            reasons=["Detailed implementation patterns", "Production-ready examples"],
            recommended=True
        )
        
        article1 = AnalyzedContent(
            raw_content=content1,
            analysis=analysis1
        )
        article1.final_score = 0.88
        article1.priority_rank = 1
        
        # Article 2 - Tutorial intermédiaire
        content2 = RawContent(
            title="Optimizing LLM Performance in Production",
            url="https://medium.com/tech/llm-optimization",
            source="medium",
            content="This tutorial covers essential techniques for optimizing LLM performance in production environments...",
            excerpt="LLM optimization techniques for production",
            published_date=datetime.now()
        )
        
        analysis2 = ContentAnalysis(
            relevance_score=0.8,
            difficulty_level=DifficultyLevel.INTERMEDIATE,
            main_topics=["LLM", "optimization", "production"],
            key_insights="Performance optimization strategies for production LLMs",
            practical_value=0.9,
            reasons=["Practical optimization techniques", "Real-world examples"],
            recommended=True
        )
        
        article2 = AnalyzedContent(
            raw_content=content2,
            analysis=analysis2
        )
        article2.final_score = 0.81
        article2.priority_rank = 2
        
        return [article1, article2]
    
    @pytest.fixture
    def synthesizer_agent(self):
        """Agent synthétiseur pour les tests."""
        return TechSynthesizerAgent()
    
    @pytest.mark.asyncio
    async def test_create_daily_digest_basic(self, synthesizer_agent, sample_analyzed_articles):
        """Test de création de digest basique."""
        
        # Mock LLM pour éviter les appels API
        synthesizer_agent.llm = AsyncMock()
        
        # Mock des réponses LLM
        mock_responses = [
            # Executive summary
            MagicMock(content="Les développements d'aujourd'hui montrent une progression notable dans l'orchestration multi-agents et l'optimisation LLM pour la production."),
            
            # Article synthesis 1
            MagicMock(content='{"title_refined": "Architecture Multi-Agent Avancée avec LangGraph", "executive_summary": "Patterns d\'architecture pour systèmes multi-agents en production", "key_takeaways": ["Orchestration avancée", "Patterns production"], "technical_highlights": ["StateGraph", "Monitoring"], "complexity_level": "advanced", "innovation_level": "significant"}'),
            
            # Article synthesis 2  
            MagicMock(content='{"title_refined": "Optimisation LLM en Production", "executive_summary": "Techniques d\'optimisation pour LLMs en production", "key_takeaways": ["Performance optimization", "Production deployment"], "technical_highlights": ["Memory optimization", "Latency reduction"], "complexity_level": "intermediate", "innovation_level": "incremental"}'),
            
            # Insights extraction
            MagicMock(content="- L'orchestration multi-agents se standardise\n- L'optimisation LLM se concentre sur la production\n- Les patterns d'architecture émergent"),
            
            # Recommendations
            MagicMock(content='{"recommendations": [{"title": "Évaluer LangGraph", "description": "Explorer les capacités d\'orchestration", "action_items": ["Analyser l\'architecture actuelle", "Créer un POC"], "category": "learning", "priority": "high", "time_investment": "1-4h"}]}')
        ]
        
        synthesizer_agent.llm.ainvoke = AsyncMock(side_effect=mock_responses)
        
        # Exécution du test
        digest = await synthesizer_agent.create_daily_digest(sample_analyzed_articles)
        
        # Assertions
        assert digest is not None
        assert digest.title is not None
        assert "Tech Digest" in digest.title
        assert len(digest.top_articles) == 2
        assert digest.executive_summary is not None
        assert len(digest.key_insights) > 0
        assert len(digest.recommendations) > 0
        assert digest.markdown_content is not None
        assert digest.word_count > 0
        assert digest.estimated_read_time > 0
        
        # Vérification structure Markdown
        assert "# " in digest.markdown_content
        assert "## " in digest.markdown_content
        assert "📊 Résumé Exécutif" in digest.markdown_content
        assert "🏆 Top Articles" in digest.markdown_content
        
        # Vérification articles
        assert digest.top_articles[0].title_refined == "Architecture Multi-Agent Avancée avec LangGraph"
        assert digest.top_articles[1].title_refined == "Optimisation LLM en Production"
        
        # Vérification recommandations
        assert len(digest.recommendations) == 1
        assert digest.recommendations[0].title == "Évaluer LangGraph"
        assert digest.recommendations[0].priority == "high"
    
    @pytest.mark.asyncio
    async def test_digest_with_no_articles(self, synthesizer_agent):
        """Test avec aucun article - doit lever une exception."""
        
        with pytest.raises(ValueError, match="Aucun article analysé fourni"):
            await synthesizer_agent.create_daily_digest([])
    
    @pytest.mark.asyncio
    async def test_digest_with_non_recommended_articles(self, synthesizer_agent, sample_analyzed_articles):
        """Test avec articles non recommandés."""
        
        # Marquer tous les articles comme non recommandés
        for article in sample_analyzed_articles:
            article.analysis.recommended = False
        
        # Mock LLM
        synthesizer_agent.llm = AsyncMock()
        synthesizer_agent.llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="Test content")
        )
        
        # Doit utiliser les articles même s'ils ne sont pas recommandés
        digest = await synthesizer_agent.create_daily_digest(sample_analyzed_articles)
        
        assert digest is not None
        assert len(digest.top_articles) > 0
    
    @pytest.mark.asyncio
    async def test_digest_markdown_structure(self, synthesizer_agent, sample_analyzed_articles):
        """Test de la structure Markdown générée."""
        
        # Mock LLM simple
        synthesizer_agent.llm = AsyncMock()
        synthesizer_agent.llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="Test response")
        )
        
        digest = await synthesizer_agent.create_daily_digest(sample_analyzed_articles)
        markdown = digest.markdown_content
        
        # Vérifications structure
        assert markdown.startswith("# Tech Digest")
        assert "## 📊 Résumé Exécutif" in markdown
        assert "## 🏆 Top Articles" in markdown
        assert "## 💡 Insights Clés" in markdown
        assert "## 🎯 Recommandations Actionables" in markdown
        assert "## 📚 Ressources" in markdown
        
        # Vérifications métadonnées
        assert "📅" in markdown  # Date
        assert "⏱️" in markdown  # Temps de lecture
        assert "🎯" in markdown  # Audience
        
        # Vérifications liens
        assert "https://arxiv.org/abs/2024.001" in markdown
        assert "https://medium.com/tech/llm-optimization" in markdown
    
    def test_synthesizer_configuration(self):
        """Test de la configuration du synthétiseur."""
        
        custom_config = {
            "max_articles_in_digest": 5,
            "max_insights": 3,
            "target_audience": "tech_lead"
        }
        
        synthesizer = TechSynthesizerAgent(custom_config)
        
        assert synthesizer.config["max_articles_in_digest"] == 5
        assert synthesizer.config["max_insights"] == 3
        assert synthesizer.config["target_audience"] == "tech_lead"
    
    @pytest.mark.asyncio
    async def test_save_digest_to_file(self, synthesizer_agent, sample_analyzed_articles, tmp_path):
        """Test de sauvegarde du digest."""
        
        # Mock LLM
        synthesizer_agent.llm = AsyncMock()
        synthesizer_agent.llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="Test content")
        )
        
        # Création du digest
        digest = await synthesizer_agent.create_daily_digest(sample_analyzed_articles)
        
        # Sauvegarde dans un répertoire temporaire
        output_dir = str(tmp_path / "test_output")
        file_path = await synthesizer_agent.save_digest_to_file(digest, output_dir)
        
        # Vérifications
        assert file_path.endswith(".md")
        assert "tech_digest_" in file_path
        
        # Vérification contenu fichier
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "# Tech Digest" in content
            assert digest.markdown_content == content


# Tests d'intégration
class TestSynthesizerIntegration:
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_pipeline_simulation(self):
        """Test d'intégration simulé du pipeline complet."""
        
        # Ce test simule le pipeline sans appels API réels
        from src.agents import TechCollectorAgent, TechAnalyzerAgent, TechSynthesizerAgent, CollectionConfig
        
        # Mock des agents
        collector = TechCollectorAgent()
        analyzer = TechAnalyzerAgent()
        synthesizer = TechSynthesizerAgent()
        
        # Mock data
        mock_raw_content = RawContent(
            title="Test Article",
            url="https://test.com",
            source="test",
            content="Test content"
        )
        
        mock_analysis = ContentAnalysis(
            relevance_score=0.8,
            difficulty_level=DifficultyLevel.INTERMEDIATE,
            main_topics=["test"],
            key_insights="Test insights",
            practical_value=0.7,
            reasons=["Test reasons"],
            recommended=True
        )
        
        mock_analyzed = AnalyzedContent(
            raw_content=mock_raw_content,
            analysis=mock_analysis
        )
        mock_analyzed.final_score = 0.75
        
        # Mock LLM pour synthétiseur
        synthesizer.llm = AsyncMock()
        synthesizer.llm.ainvoke = AsyncMock(
            return_value=MagicMock(content="Mock LLM response")
        )
        
        # Test pipeline
        digest = await synthesizer.create_daily_digest([mock_analyzed])
        
        assert digest is not None
        assert digest.title is not None
        assert len(digest.top_articles) == 1


if __name__ == "__main__":
    # Exécution des tests
    pytest.main([__file__, "-v"])
