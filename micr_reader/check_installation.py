# check_installation.py
"""
Script de vérification de l'installation du MICR Reader
"""

import sys
import os

def check_python_version():
    """Vérifie la version de Python"""
    print("🐍 Vérification de Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Version trop ancienne (minimum 3.8)")
        return False

def check_dependencies():
    """Vérifie les dépendances"""
    print("\n📦 Vérification des dépendances...")
    dependencies = ['openai', 'PIL', 'json', 'time', 'base64']
    missing = []
    
    for dep in dependencies:
        try:
            if dep == 'PIL':
                from PIL import Image
                print(f"✅ Pillow (PIL) - OK")
            elif dep == 'openai':
                import openai
                print(f"✅ OpenAI - OK")
            else:
                __import__(dep)
                print(f"✅ {dep} - OK")
        except ImportError:
            print(f"❌ {dep} - MANQUANT")
            missing.append(dep)
    
    return len(missing) == 0

def check_project_structure():
    """Vérifie la structure du projet"""
    print("\n📁 Vérification de la structure du projet...")
    
    required_files = [
        'config.py',
        'README.md',
        'requirements.txt',
        'models/__init__.py',
        'models/micr_models.py',
        'core/__init__.py',
        'core/confidence_calculator.py',
        'core/micr_analyzer.py',
        'core/validator.py',
        'utils/__init__.py',
        'utils/image_utils.py',
        'examples/__init__.py',
        'examples/basic_usage.py',
        'examples/batch_processing.py',
        'examples/demo_interface.py',
        'interface/__init__.py',
        'interface/gradio_interface.py',
        'launch_demo.py',
        'tests/__init__.py',
        'tests/test_confidence.py',
        'tests/test_validator.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MANQUANT")
            missing_files.append(file_path)
    
    return len(missing_files) == 0

def check_imports():
    """Vérifie que les modules peuvent être importés"""
    print("\n🔧 Vérification des imports...")
    
    try:
        from config import config
        print("✅ config - OK")
    except Exception as e:
        print(f"❌ config - ERREUR: {e}")
        return False
    
    try:
        from models.micr_models import MICRResult, MICRComponent, ComponentType
        print("✅ models.micr_models - OK")
    except Exception as e:
        print(f"❌ models.micr_models - ERREUR: {e}")
        return False
    
    try:
        from core.confidence_calculator import ConfidenceCalculator
        print("✅ core.confidence_calculator - OK")
    except Exception as e:
        print(f"❌ core.confidence_calculator - ERREUR: {e}")
        return False
    
    try:
        from core.validator import MICRValidator
        print("✅ core.validator - OK")
    except Exception as e:
        print(f"❌ core.validator - ERREUR: {e}")
        return False
    
    try:
        from utils.image_utils import ImageProcessor
        print("✅ utils.image_utils - OK")
    except Exception as e:
        print(f"❌ utils.image_utils - ERREUR: {e}")
        return False
    
    return True

def check_config():
    """Vérifie la configuration"""
    print("\n⚙️  Vérification de la configuration...")
    
    try:
        from config import config
        
        # Vérifier si la clé API est configurée
        if config.openai.api_key == 'votre-clé-api-openai':
            print("⚠️  Clé API OpenAI non configurée (utilise la valeur par défaut)")
            print("   Modifiez config.py ou définissez OPENAI_API_KEY")
        else:
            print("✅ Clé API OpenAI configurée")
        
        # Vérifier les poids de confiance
        total_weight = (config.confidence.llm_weight + 
                       config.confidence.logprob_weight + 
                       config.confidence.validation_weight)
        
        if abs(total_weight - 1.0) < 0.01:
            print("✅ Poids de confiance valides")
        else:
            print(f"❌ Poids de confiance invalides (total: {total_weight})")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur de configuration: {e}")
        return False

def run_basic_test():
    """Execute un test basique"""
    print("\n🧪 Test basique...")
    
    try:
        from models.micr_models import MICRResult, MICRComponent, ComponentType
        from core.validator import MICRValidator
        
        # Créer un composant de test
        test_component = MICRComponent(
            value="12345",
            description="Test transit",
            llm_confidence=0.9,
            logprob_confidence=0.8,
            combined_confidence=0.85,
            component_type=ComponentType.TRANSIT
        )
        
        # Créer un résultat de test
        test_result = MICRResult(
            raw_line="⑆12345⑆003⑈1234567890⑈001⑆",
            raw_confidence=0.9,
            success=True,
            transit_number=test_component
        )
        
        # Tester le validateur
        validator = MICRValidator()
        validation = validator.validate_canadian_micr(test_result)
        
        print("✅ Test basique réussi")
        print(f"   - Composant créé: {test_component.value}")
        print(f"   - Validation: {validation.transit_valid}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test basique échoué: {e}")
        return False

def main():
    """Fonction principale de vérification"""
    print("🔍 VÉRIFICATION DE L'INSTALLATION MICR READER")
    print("=" * 60)
    
    checks = [
        ("Version Python", check_python_version),
        ("Dépendances", check_dependencies),
        ("Structure du projet", check_project_structure),
        ("Imports des modules", check_imports),
        ("Configuration", check_config),
        ("Test basique", run_basic_test)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Erreur lors de {name}: {e}")
            results.append((name, False))
    
    # Résumé final
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DE LA VÉRIFICATION")
    print("=" * 60)
    
    passed = 0
    for name, result in results:
        status = "✅ PASSÉ" if result else "❌ ÉCHEC"
        print(f"{status} - {name}")
        if result:
            passed += 1
    
    print(f"\nRésultat: {passed}/{len(results)} vérifications réussies")
    
    if passed == len(results):
        print("\n🎉 INSTALLATION COMPLÈTE ET FONCTIONNELLE !")
        print("Vous pouvez maintenant utiliser le MICR Reader.")
        print("\nProchaines étapes:")
        print("1. Configurez votre clé API OpenAI")
        print("2. Testez avec: python examples/basic_usage.py")
    else:
        print(f"\n⚠️  Installation incomplète ({len(results)-passed} problèmes)")
        print("Veuillez corriger les erreurs ci-dessus.")

if __name__ == "__main__":
    main()
