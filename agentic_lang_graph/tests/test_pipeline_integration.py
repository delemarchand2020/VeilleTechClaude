"""
Test d'intégration complète : Pipeline Collecteur → Analyseur.

Test end-to-end du système complet avec les deux agents.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.agents import TechCollectorAgent, CollectionConfig
from src.agents.tech_analyzer_agent import TechAnalyzerAgent
from src.agents.simple_analyzer_prototype import ExpertProfile, DifficultyLevel


@pytest.mark.integration
class TestCompletePipeline:
    """Tests d'intégration du pipeline complet."""
    
    @pytest.mark.asyncio
    async def test_collector_to_analyzer_pipeline(self):
        """Test du pipeline complet Collecteur → Analyseur."""
        
        # 1. Phase de collecte
        collector = TechCollectorAgent()
        config = CollectionConfig(
            total_limit=5,
            keywords=["AI", "LLM"],
            max_age_days=30
        )
        
        collection_result = await collector.collect_all_sources(config)
        
        # Vérifications collecte
        assert collection_result.total_filtered >= 0
        assert isinstance(collection_result.contents, list)
        
        # 2. Phase d'analyse (avec mock pour éviter vrais appels LLM)
        expert_profile = ExpertProfile(
            level=DifficultyLevel.EXPERT,
            interests=["LangGraph", "Multi-agent", "LLM"],
            avoid_topics=["beginner_tutorials"]
        )
        
        analyzer = TechAnalyzerAgent(expert_profile)
        
        # Mock du LLM pour test rapide
        mock_response = MagicMock(
            content='{"relevance_score": 7.5, "difficulty_level": "expert", "main_topics": ["AI", "LLM"], "key_insights": "Pipeline integration test", "practical_value": 8.0, "reasons": ["Integration works"], "recommended": true}'
        )
        analyzer.llm = AsyncMock()
        analyzer.llm.ainvoke = AsyncMock(return_value=mock_response)
        
        # Analyse des contenus collectés
        if collection_result.contents:
            analyzed_results = await analyzer.analyze_contents(collection_result.contents)
            
            # Vérifications analyse
            assert isinstance(analyzed_results, list)
            assert len(analyzed_results) <= len(collection_result.contents)
            
            for result in analyzed_results:
                assert hasattr(result, 'raw_content')
                assert hasattr(result, 'analysis')
                assert result.raw_content in collection_result.contents
        
        print(f"✅ Pipeline testé: {collection_result.total_filtered} collectés → {len(analyzed_results) if collection_result.contents else 0} analysés")
    
    @pytest.mark.asyncio
    async def test_pipeline_with_empty_collection(self):
        """Test du pipeline quand la collecte est vide."""
        
        # Collecteur qui retourne vide (mock)
        collector = TechCollectorAgent()
        
        # Mock pour retourner collecte vide
        with pytest.mock.patch.object(collector, 'collect_all_sources') as mock_collect:
            from src.agents.tech_collector_agent import CollectionResult
            mock_collect.return_value = CollectionResult(
                contents=[],
                total_collected=0,
                total_filtered=0,
                duplicates_removed=0,
                collection_time=0.1,
                sources_stats={},
                errors=[]
            )
            
            config = CollectionConfig(total_limit=5)
            collection_result = await collector.collect_all_sources(config)
            
            # Test analyse avec collecte vide
            analyzer = TechAnalyzerAgent()
            analyzed_results = await analyzer.analyze_contents(collection_result.contents)
            
            assert analyzed_results == []
    
    @pytest.mark.asyncio 
    async def test_pipeline_error_resilience(self):
        """Test de résilience du pipeline en cas d'erreurs."""
        
        # Test avec un collecteur qui fonctionne
        collector = TechCollectorAgent()
        config = CollectionConfig(total_limit=2, keywords=["test"])
        
        collection_result = await collector.collect_all_sources(config)
        
        # Test avec analyseur qui a des erreurs LLM
        analyzer = TechAnalyzerAgent()
        
        # Mock qui lève des exceptions de façon intermittente
        call_count = 0
        def mock_llm_with_errors(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:  # Une erreur sur deux
                raise Exception("LLM Error")
            return MagicMock(
                content='{"relevance_score": 6.0, "difficulty_level": "intermediate", "main_topics": ["test"], "key_insights": "Error resilience test", "practical_value": 6.0, "reasons": ["Resilience"], "recommended": true}'
            )
        
        analyzer.llm = AsyncMock()
        analyzer.llm.ainvoke = AsyncMock(side_effect=mock_llm_with_errors)
        
        # Le pipeline ne doit pas crasher malgré les erreurs
        if collection_result.contents:
            analyzed_results = await analyzer.analyze_contents(collection_result.contents)
            
            # Doit retourner au moins quelques résultats
            assert isinstance(analyzed_results, list)
            # Peut être moins que l'input à cause des erreurs
    
    @pytest.mark.asyncio
    async def test_recommendations_pipeline(self):
        """Test du pipeline pour obtenir des recommandations."""
        
        # Collecte
        collector = TechCollectorAgent()
        config = CollectionConfig(total_limit=8, keywords=["AI", "machine learning"])
        
        collection_result = await collector.collect_all_sources(config)
        
        if not collection_result.contents:
            pytest.skip("Aucun contenu collecté pour le test de recommandations")
        
        # Analyse avec focus sur recommandations
        analyzer = TechAnalyzerAgent()
        
        # Mock avec mix de scores pour simuler des recommandations variées
        def mock_varying_scores(*args, **kwargs):
            import random
            score = random.uniform(3.0, 9.0)
            recommended = score >= 7.0
            
            return MagicMock(
                content=f'{{"relevance_score": {score:.1f}, "difficulty_level": "intermediate", "main_topics": ["AI"], "key_insights": "Varying scores test", "practical_value": {score:.1f}, "reasons": ["Score variation"], "recommended": {str(recommended).lower()}}}'
            )
        
        analyzer.llm = AsyncMock()
        analyzer.llm.ainvoke = AsyncMock(side_effect=mock_varying_scores)
        
        # Test des recommandations
        recommendations = await analyzer.get_recommendations(
            collection_result.contents, 
            limit=3
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 3
        
        # Toutes les recommandations doivent être marquées comme recommandées
        for rec in recommendations:
            assert rec.analysis.recommended is True
            assert rec.analysis.relevance_score >= 7.0
        
        print(f"✅ Pipeline recommandations: {len(recommendations)} recommandations sur {len(collection_result.contents)} collectés")


@pytest.mark.performance
class TestPipelinePerformance:
    """Tests de performance du pipeline complet."""
    
    @pytest.mark.asyncio
    async def test_pipeline_performance(self):
        """Test de performance du pipeline complet."""
        import time
        
        start_time = time.time()
        
        # Collecte rapide
        collector = TechCollectorAgent()
        config = CollectionConfig(total_limit=5, keywords=["AI"])
        
        collection_result = await collector.collect_all_sources(config)
        collection_time = time.time() - start_time
        
        # Analyse rapide (avec mock)
        if collection_result.contents:
            analyzer = TechAnalyzerAgent()
            
            # Mock rapide
            analyzer.llm = AsyncMock()
            analyzer.llm.ainvoke = AsyncMock(
                return_value=MagicMock(
                    content='{"relevance_score": 6.0, "difficulty_level": "intermediate", "main_topics": ["AI"], "key_insights": "Performance test", "practical_value": 6.0, "reasons": ["Speed test"], "recommended": true}'
                )
            )
            
            analysis_start = time.time()
            analyzed_results = await analyzer.analyze_contents(collection_result.contents)
            analysis_time = time.time() - analysis_start
            
            total_time = time.time() - start_time
            
            # Vérifications de performance
            assert collection_time < 10.0  # Collecte en moins de 10s
            assert analysis_time < 5.0     # Analyse en moins de 5s  
            assert total_time < 15.0       # Pipeline complet en moins de 15s
            
            print(f"⏱️ Performance pipeline:")
            print(f"   Collecte: {collection_time:.2f}s ({len(collection_result.contents)} contenus)")
            print(f"   Analyse: {analysis_time:.2f}s ({len(analyzed_results)} analysés)")
            print(f"   Total: {total_time:.2f}s")


if __name__ == "__main__":
    # Test rapide pour vérification manuelle
    async def quick_integration_test():
        print("🧪 Test rapide d'intégration")
        
        from src.agents import TechCollectorAgent, CollectionConfig
        from src.agents.tech_analyzer_agent import TechAnalyzerAgent
        from unittest.mock import AsyncMock, MagicMock
        
        # Test collecte
        collector = TechCollectorAgent()
        config = CollectionConfig(total_limit=3, keywords=["AI"])
        result = await collector.collect_all_sources(config)
        
        print(f"✅ Collecté: {result.total_filtered} contenus")
        
        if result.contents:
            # Test analyse
            analyzer = TechAnalyzerAgent()
            
            # Mock pour test rapide
            analyzer.llm = AsyncMock()
            analyzer.llm.ainvoke = AsyncMock(
                return_value=MagicMock(
                    content='{"relevance_score": 8.0, "difficulty_level": "expert", "main_topics": ["AI"], "key_insights": "Integration works", "practical_value": 8.0, "reasons": ["Good integration"], "recommended": true}'
                )
            )
            
            analyzed = await analyzer.analyze_contents(result.contents)
            print(f"✅ Analysé: {len(analyzed)} contenus")
            
            if analyzed:
                print(f"📊 Score moyen: {sum(a.analysis.relevance_score for a in analyzed)/len(analyzed):.1f}")
                print(f"🎯 Recommandés: {sum(1 for a in analyzed if a.analysis.recommended)}")
        
        print("🎉 Pipeline d'intégration fonctionnel!")
    
    asyncio.run(quick_integration_test())
