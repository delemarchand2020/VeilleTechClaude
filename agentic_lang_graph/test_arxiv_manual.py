#!/usr/bin/env python3
"""
Test rapide du connecteur ArXiv.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from connectors.arxiv_connector import ArxivConnector

def test_arxiv_connector():
    """Test rapide du connecteur ArXiv."""
    print("🧪 Test rapide du connecteur ArXiv")
    
    # Test d'initialisation
    print("1. Test d'initialisation...")
    connector = ArxivConnector(["transformer"], ["cs.AI"])
    assert connector.source_name == "arxiv"
    assert "transformer" in connector.search_keywords
    print("   ✅ Initialisation OK")
    
    # Test de construction des requêtes
    print("2. Test de construction des requêtes...")
    queries = connector._build_search_queries()
    assert len(queries) > 0
    assert any("cat:cs.AI" in q for q in queries)
    print(f"   ✅ {len(queries)} requêtes construites")
    
    # Test d'extraction d'ID ArXiv
    print("3. Test d'extraction d'ID ArXiv...")
    test_url = "http://arxiv.org/abs/2401.12345v1"
    arxiv_id = connector._extract_arxiv_id(test_url)
    assert arxiv_id == "2401.12345v1"
    print("   ✅ Extraction d'ID OK")
    
    # Test de disponibilité (optionnel, peut échouer sans Internet)
    print("4. Test de disponibilité...")
    try:
        available = connector.is_available()
        print(f"   ✅ ArXiv disponible: {available}")
    except Exception as e:
        print(f"   ⚠️  Test de disponibilité échoué (normal sans Internet): {e}")
    
    print("\n🎉 Tous les tests rapides du connecteur ArXiv sont passés!")

if __name__ == "__main__":
    test_arxiv_connector()
