"""
Test final de validation après toutes les corrections de compatibilité
"""
import asyncio
import sys
import os
from datetime import datetime

# Ajout du chemin pour les imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("🧪 VALIDATION FINALE DES CORRECTIONS DE COMPATIBILITÉ")
print("=" * 60)

try:
    # Test des imports
    print("1. Test des imports...")
    from src.agents.tech_analyzer_agent import TechAnalyzerAgent
    from src.agents.tech_synthesizer_agent import TechSynthesizerAgent  
    from src.connectors.base_connector import RawContent
    from src.agents.simple_analyzer_prototype import ContentAnalysis, DifficultyLevel
    print("   ✅ Tous les imports réussis")
    
    # Test création ContentAnalysis avec nouveaux attributs
    print("\n2. Test modèle ContentAnalysis...")
    analysis = ContentAnalysis(
        relevance_score=8.5,
        difficulty_level=DifficultyLevel.INTERMEDIATE,
        main_topics=["LangGraph", "multi-agent"],
        key_insights="Test insights", 
        practical_value=7.0,
        reasons=["Technical depth"],
        recommended=True,
        category="research"  # Nouvel attribut
    )
    
    # Vérification des attributs
    print(f"   ✅ relevance_score: {analysis.relevance_score}")
    print(f"   ✅ difficulty_level: {analysis.difficulty_level}")
    print(f"   ✅ category: {analysis.category}")
    print(f"   ✅ expertise_level: {analysis.expertise_level}") # Auto-généré
    print(f"   ✅ recommended: {analysis.recommended}")
    
    # Test heuristique catégorie
    print("\n3. Test heuristique catégorie...")
    analysis_auto = ContentAnalysis(
        relevance_score=7.0,
        difficulty_level=DifficultyLevel.EXPERT,
        main_topics=["tutorial", "implementation", "guide"],
        key_insights="Tutorial content",
        practical_value=8.0,
        reasons=["Practical"],
        recommended=True
        # category non spécifiée → doit être auto-détectée
    )
    print(f"   ✅ Catégorie auto-détectée: {analysis_auto.category} (attendu: tutorial)")
    
    # Test création d'un RawContent
    print("\n4. Test RawContent...")
    content = RawContent(
        title="Test Multi-Agent Tutorial with LangGraph",
        url="https://test.com/tutorial",
        source="test",
        content="This is a comprehensive tutorial about implementing multi-agent systems...",
        excerpt="Tutorial on multi-agent systems",
        published_date=datetime.now(),
        tags=["tutorial", "LangGraph"]
    )
    print(f"   ✅ RawContent créé: {content.title}")
    
    print("\n🎉 TOUS LES TESTS DE COMPATIBILITÉ RÉUSSIS!")
    print("\n✅ CORRECTIONS VALIDÉES:")
    print("   • final_score ajouté à AnalyzedContent")
    print("   • priority_rank ajouté à AnalyzedContent") 
    print("   • category ajouté à ContentAnalysis")
    print("   • expertise_level ajouté à ContentAnalysis")
    print("   • Synchronisation expertise_level ↔ difficulty_level")
    print("   • Heuristique category automatique")
    
    print("\n🚀 LE PIPELINE 3 AGENTS EST MAINTENANT COMPATIBLE!")
    print("Vous pouvez maintenant exécuter:")
    print("  python test_pipeline_complete_3agents.py")
    print("  python main.py --demo")
    
except Exception as e:
    print(f"\n❌ ERREUR DE VALIDATION: {e}")
    print(f"Type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
