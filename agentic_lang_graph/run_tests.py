#!/usr/bin/env python3
"""
Script pour exécuter les tests avec différentes configurations.

Usage:
    python run_tests.py                 # Tous les tests
    python run_tests.py --unit          # Tests unitaires seulement
    python run_tests.py --integration   # Tests d'intégration seulement
    python run_tests.py --connector     # Tests des connecteurs seulement
    python run_tests.py --coverage      # Avec couverture de code
    python run_tests.py --fast          # Tests rapides seulement (sans slow)
    python run_tests.py --external      # Inclure les tests externes
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_pytest(args_list):
    """Exécute pytest avec les arguments donnés."""
    cmd = [sys.executable, "-m", "pytest"] + args_list
    print(f"Commande: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Lanceur de tests pour le projet Agent de Veille")
    
    # Types de tests
    parser.add_argument("--unit", action="store_true", help="Tests unitaires seulement")
    parser.add_argument("--integration", action="store_true", help="Tests d'intégration seulement")
    parser.add_argument("--connector", action="store_true", help="Tests des connecteurs seulement")
    
    # Options de performance
    parser.add_argument("--fast", action="store_true", help="Tests rapides seulement (exclut les tests lents)")
    parser.add_argument("--external", action="store_true", help="Inclure les tests externes")
    
    # Couverture et rapports
    parser.add_argument("--coverage", action="store_true", help="Activer la couverture de code")
    parser.add_argument("--html", action="store_true", help="Générer un rapport HTML")
    
    # Options de debugging
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbose")
    parser.add_argument("--debug", action="store_true", help="Mode debug avec logs détaillés")
    parser.add_argument("--pdb", action="store_true", help="Entrer en mode debug sur les échecs")
    
    # Sélection de tests spécifiques
    parser.add_argument("--file", help="Exécuter un fichier de test spécifique")
    parser.add_argument("--test", help="Exécuter un test spécifique")
    
    args = parser.parse_args()
    
    # Construction des arguments pytest
    pytest_args = []
    
    # Sélection par markers
    markers = []
    if args.unit:
        markers.append("unit")
    if args.integration:
        markers.append("integration")
    if args.connector:
        markers.append("connector")
    
    if markers:
        pytest_args.extend(["-m", " or ".join(markers)])
    
    # Exclusion des tests lents
    if args.fast:
        if markers:
            pytest_args[-1] += " and not slow"
        else:
            pytest_args.extend(["-m", "not slow"])
    
    # Tests externes
    if args.external:
        import os
        os.environ['RUN_EXTERNAL_TESTS'] = '1'
    
    # Couverture de code
    if args.coverage:
        pytest_args.extend([
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=xml"
        ])
        if args.html:
            pytest_args.append("--cov-report=html:htmlcov")
    
    # Options de debug
    if args.verbose:
        pytest_args.append("-v")
    if args.debug:
        pytest_args.extend(["--log-cli-level=DEBUG", "-s"])
    if args.pdb:
        pytest_args.append("--pdb")
    
    # Sélection de fichiers/tests spécifiques
    if args.file:
        pytest_args.append(args.file)
    if args.test:
        pytest_args.extend(["-k", args.test])
    
    # Si aucun argument spécifique, utiliser la configuration par défaut
    if not any([args.unit, args.integration, args.connector, args.file, args.test]):
        pytest_args.append("tests/")
    
    # Exécution des tests
    return_code = run_pytest(pytest_args)
    
    if return_code == 0:
        print("\n✅ Tous les tests sont passés avec succès!")
    else:
        print(f"\n❌ Certains tests ont échoué (code de retour: {return_code})")
    
    return return_code


if __name__ == "__main__":
    sys.exit(main())
