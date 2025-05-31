#!/usr/bin/env python3
"""
Test manuel simple de l'Agent Collecteur Tech - Version safe.
"""
import sys
import asyncio
from pathlib import Path

# Ajout du path pour l'import (remonte au niveau parent)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.agents.tech_collector_agent import TechCollectorAgent, CollectionConfig
    print("[OK] Import reussi depuis manual_tests/")
except ImportError as e:
    print(f"[ERREUR] Import echoue: {e}")
    print(f"Chemin projet: {project_root}")
    print(f"Contenu: {list(project_root.iterdir())}")
    sys.exit(1)

async def test_manual_simple():
    """Test manuel simple."""
    try:
        print("=== Test Manuel Simple ===")
        
        # Test initialisation
        print("Initialisation de l'agent...")
        agent = TechCollectorAgent()
        print(f"[OK] Agent cree avec {len(agent.connectors)} connecteurs")
        
        # Test diagnostic
        print("Diagnostic de sante...")
        health = await agent.health_check()
        print(f"[OK] Statut: {health['agent_status']}")
        
        # Test collecte limitee
        print("Test de collecte (limite 2)...")
        config = CollectionConfig(
            total_limit=2, 
            source_limits={'medium': 1, 'arxiv': 1}
        )
        
        result = await agent.collect_all_sources(config)
        
        print(f"[OK] Collecte terminee:")
        print(f"  - Total collecte: {result.total_collected}")
        print(f"  - Total final: {result.total_filtered}")
        print(f"  - Temps: {result.collection_time:.2f}s")
        
        if result.contents:
            print(f"  - Premier article: {result.contents[0].title[:50]}...")
        
        print("[SUCCES] Test manuel reussi !")
        return True
        
    except Exception as e:
        print(f"[ERREUR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Test Manuel Simple - Agent Collecteur Tech")
    print("=" * 60)
    
    success = asyncio.run(test_manual_simple())
    
    if success:
        print("\n[SUCCES] L'Agent Collecteur Tech fonctionne parfaitement !")
        print("Vous pouvez maintenant passer a l'Agent Analyse Tech.")
    else:
        print("\n[ECHEC] Probleme avec l'agent.")
        sys.exit(1)
