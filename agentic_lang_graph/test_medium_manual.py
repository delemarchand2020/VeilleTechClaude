"""
Script de test pour valider le connecteur Medium.

Ce script peut être utilisé pour :
1. Tester les imports et la configuration
2. Exécuter des tests basiques manuellement
3. Valider le connecteur en conditions réelles (optionnel)
"""
import sys
import os
import asyncio
from pathlib import Path

# Ajouter le chemin du projet au PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.connectors.medium_connector import MediumConnector
    from src.connectors.base_connector import RawContent
    print("✅ Imports réussis")
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    sys.exit(1)


async def test_medium_connector_basic():
    """Test basique du connecteur Medium."""
    print("\n🧪 Test basique du connecteur Medium...")
    
    try:
        # Initialisation
        connector = MediumConnector(["AI", "Python"])
        print(f"✅ Connecteur initialisé avec {len(connector.feed_urls)} flux RSS")
        
        # Test de disponibilité (sans vraie requête réseau)
        print("🔍 Test de construction des URLs...")
        assert len(connector.feed_urls) > 0
        assert any("artificial-intelligence" in url for url in connector.feed_urls)
        print("✅ URLs de flux construites correctement")
        
        # Test des méthodes utilitaires
        print("🔧 Test des méthodes utilitaires...")
        
        # Test extract_medium_post_id
        test_url = "https://medium.com/@author/article-title-123abc456def"
        post_id = connector._extract_medium_post_id(test_url)
        assert post_id == "123abc456def"
        print("✅ Extraction d'ID de post fonctionne")
        
        # Test deduplicate
        test_contents = [
            RawContent("Article 1", "https://medium.com/test1", "medium"),
            RawContent("Article 2", "https://medium.com/test2", "medium"),
            RawContent("Article 1 Duplicate", "https://medium.com/test1", "medium"),  # Doublon
        ]
        deduplicated = connector._deduplicate(test_contents)
        assert len(deduplicated) == 2
        print("✅ Déduplication fonctionne")
        
        # Test filtrage par mots-clés
        test_contents_filter = [
            RawContent("AI Revolution", "url1", "medium", excerpt="About AI"),
            RawContent("Java Tutorial", "url2", "medium", excerpt="Learn Java"),
            RawContent("Python Guide", "url3", "medium", excerpt="Python tips"),
        ]
        filtered = connector.filter_by_keywords(test_contents_filter)
        assert len(filtered) == 2  # AI et Python articles
        print("✅ Filtrage par mots-clés fonctionne")
        
        print("🎉 Tous les tests basiques réussis !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur dans les tests basiques: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_medium_connector_mock_rss():
    """Test avec des données RSS mockées."""
    print("\n🧪 Test avec données RSS mockées...")
    
    try:
        connector = MediumConnector()
        
        # Création d'un mock d'entrée RSS
        class MockEntry:
            def __init__(self):
                self.title = "Test AI Article"
                self.link = "https://medium.com/@test/ai-article-123"
                self.summary = "This is a test article about AI"
                self.author = "Test Author"
                self.published_parsed = (2024, 1, 15, 10, 30, 0, 0, 15, 0)
                self.id = "test-guid-123"
        
        # Test du parsing d'entrée
        mock_entry = MockEntry()
        content = connector._parse_rss_entry(mock_entry, "test_feed")
        
        assert content is not None
        assert content.title == "Test AI Article"
        assert content.url == "https://medium.com/@test/ai-article-123"
        assert content.source == "medium"
        assert content.author == "Test Author"
        print("✅ Parsing d'entrée RSS fonctionne")
        
        # Test de validation
        assert connector.validate_content(content) is True
        print("✅ Validation de contenu fonctionne")
        
        print("🎉 Tests avec mock RSS réussis !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur dans les tests mock RSS: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_imports_and_structure():
    """Teste la structure des imports et modules."""
    print("\n🧪 Test de la structure des imports...")
    
    try:
        # Test des imports principaux
        from src.connectors.base_connector import BaseConnector, RawContent
        from src.connectors.medium_connector import MediumConnector
        print("✅ Imports des connecteurs OK")
        
        # Test de la hiérarchie des classes
        assert issubclass(MediumConnector, BaseConnector)
        print("✅ Hiérarchie des classes correcte")
        
        # Test de l'initialisation des classes
        raw_content = RawContent("Test", "http://test.com", "test")
        assert raw_content.title == "Test"
        assert raw_content.tags == []  # Auto-initialisé
        assert raw_content.raw_data == {}  # Auto-initialisé
        print("✅ Classe RawContent fonctionne")
        
        connector = MediumConnector()
        assert connector.source_name == "medium"
        assert hasattr(connector, 'logger')
        print("✅ Classe MediumConnector fonctionne")
        
        print("🎉 Structure et imports corrects !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur de structure: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Fonction principale de test."""
    print("🚀 Démarrage des tests du connecteur Medium")
    print("=" * 50)
    
    all_passed = True
    
    # Test 1: Structure et imports
    if not test_imports_and_structure():
        all_passed = False
    
    # Test 2: Fonctionnalités basiques
    if not await test_medium_connector_basic():
        all_passed = False
    
    # Test 3: Mock RSS
    if not await test_medium_connector_mock_rss():
        all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 TOUS LES TESTS RÉUSSIS ! Le connecteur Medium est prêt.")
        print("\n📋 Prochaines étapes:")
        print("1. Exécuter les tests unitaires complets avec pytest")
        print("2. Test d'intégration avec de vraies données (optionnel)")
        print("3. Intégrer dans l'agent collecteur")
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ. Vérifiez les erreurs ci-dessus.")
        return 1
    
    return 0


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)
