# examples/basic_usage.py
"""
Exemple d'utilisation basique du MICR Reader
"""

import os
import sys

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.micr_analyzer import MICRAnalyzer
from core.validator import MICRValidator
from utils.image_utils import ImageProcessor
from config import config

def print_micr_results(result, validations):
    """Affiche les résultats de l'analyse MICR de façon formatée"""
    print("=" * 60)
    print("RÉSULTATS DE L'ANALYSE MICR - CHÈQUE CANADIEN")
    print("=" * 60)
    
    if not result.success:
        print(f"❌ ÉCHEC DE L'ANALYSE: {result.error_message}")
        return
    
    print(f"✅ Statut: {'SUCCÈS' if result.success else 'ÉCHEC'}")
    print(f"📁 Fichier: {os.path.basename(result.image_path)}")
    print(f"⏱️  Temps: {result.processing_time:.2f}s")
    print(f"📝 Ligne MICR: {result.raw_line}")
    print(f"🎯 Confiance globale: {result.get_overall_confidence():.1%}")
    print(f"✓ Format valide: {'OUI' if validations.is_valid else 'NON'}")
    print(f"🔧 Complet: {'OUI' if result.is_complete_micr() else 'NON'}")
    print()
    
    print("COMPOSANTES DÉTAILLÉES:")
    print("-" * 40)
    
    components = [
        ("🏦 Numéro de transit", result.transit_number, validations.transit_valid),
        ("🏢 Numéro d'institution", result.institution_number, validations.institution_valid),
        ("👤 Numéro de compte", result.account_number, validations.account_valid),
        ("📄 Numéro de chèque", result.cheque_number, True),
        ("💰 Montant", result.amount, True),
        ("📋 Données auxiliaires", result.auxiliary_on_us, True)
    ]
    
    for label, component, is_valid in components:
        if component and component.value:
            status = "✓" if is_valid else "⚠️"
            print(f"{status} {label}: {component.value}")
            print(f"   📊 Confiance finale: {component.combined_confidence:.1%}")
            print(f"   🤖 Confiance LLM: {component.llm_confidence:.1%}")
            print(f"   📈 Confiance logprobs: {component.logprob_confidence:.1%}")
            print(f"   ✅ Validation: {'PASSÉE' if component.validation_passed else 'ÉCHOUÉE'}")
            
            # Afficher le nom de la banque si c'est l'institution
            if component.component_type.value == "institution_number":
                validator = MICRValidator()
                bank_name = validator.get_institution_name(component.value)
                print(f"   🏛️  Banque: {bank_name}")
            print()
        else:
            print(f"⚪ {label}: Non détecté")
            print()
    
    # Afficher les erreurs et avertissements
    if validations.errors:
        print("❌ ERREURS:")
        for error in validations.errors:
            print(f"   • {error}")
        print()
    
    if validations.warnings:
        print("⚠️ AVERTISSEMENTS:")
        for warning in validations.warnings:
            print(f"   • {warning}")
        print()

def demonstrate_confidence_analysis(analyzer, component):
    """Démontre l'analyse détaillée de confiance"""
    if not component:
        return
    
    print(f"🔍 ANALYSE DÉTAILLÉE DE CONFIANCE - {component.component_type.value.upper()}")
    print("-" * 50)
    
    breakdown = analyzer.get_confidence_breakdown(component)
    
    print(f"Valeur détectée: {component.value}")
    print()
    print("Contributions à la confiance finale:")
    print(f"  🤖 LLM ({breakdown['weights']['llm_weight']:.0%}): {breakdown['llm_contribution']:.3f}")
    print(f"  📈 Logprobs ({breakdown['weights']['logprob_weight']:.0%}): {breakdown['logprob_contribution']:.3f}")
    print(f"  ✅ Validation ({breakdown['weights']['validation_weight']:.0%}): {breakdown['validation_contribution']:.3f}")
    print(f"  📊 TOTAL: {breakdown['combined_total']:.3f} ({breakdown['combined_total']:.1%})")
    print()

def create_demo_result():
    """Crée un résultat de démonstration avec des données fictives"""
    from models.micr_models import MICRResult, MICRComponent, ComponentType
    
    print("🎭 DÉMONSTRATION AVEC DONNÉES FICTIVES")
    print("=" * 60)
    
    # Créer des composants fictifs avec différents niveaux de confiance
    transit_comp = MICRComponent(
        value="12345",
        description="Numéro de transit/succursale",
        llm_confidence=0.95,
        logprob_confidence=0.89,
        combined_confidence=0.91,
        component_type=ComponentType.TRANSIT,
        validation_passed=True
    )
    
    institution_comp = MICRComponent(
        value="003",
        description="Numéro d'institution bancaire",
        llm_confidence=0.88,
        logprob_confidence=0.92,
        combined_confidence=0.90,
        component_type=ComponentType.INSTITUTION,
        validation_passed=True
    )
    
    account_comp = MICRComponent(
        value="1234567890",
        description="Numéro de compte",
        llm_confidence=0.82,
        logprob_confidence=0.75,
        combined_confidence=0.78,
        component_type=ComponentType.ACCOUNT,
        validation_passed=True
    )
    
    cheque_comp = MICRComponent(
        value="001",
        description="Numéro du chèque",
        llm_confidence=0.97,
        logprob_confidence=0.94,
        combined_confidence=0.95,
        component_type=ComponentType.CHEQUE,
        validation_passed=True
    )
    
    # Créer le résultat fictif
    demo_result = MICRResult(
        raw_line="⑆12345⑆003⑈1234567890⑈001⑆",
        raw_confidence=0.89,
        success=True,
        error_message=None,
        transit_number=transit_comp,
        institution_number=institution_comp,
        account_number=account_comp,
        cheque_number=cheque_comp,
        amount=None,
        auxiliary_on_us=None,
        processing_time=2.3,
        image_path="exemple_fictif.jpg"
    )
    
    # Créer une validation fictive
    from models.micr_models import ValidationResult
    demo_validation = ValidationResult(
        is_valid=True,
        transit_valid=True,
        institution_valid=True,
        account_valid=True,
        format_valid=True,
        errors=[],
        warnings=["Institution reconnue: Banque Royale du Canada (003)"]
    )
    
    # Afficher les résultats
    print_micr_results(demo_result, demo_validation)
    
    # Démonstration de l'analyse de confiance
    print("🔍 EXEMPLE D'ANALYSE DE CONFIANCE DÉTAILLÉE")
    print("-" * 50)
    
    breakdown_example = {
        'llm_contribution': 0.95 * 0.3,
        'logprob_contribution': 0.89 * 0.6,
        'validation_contribution': 1.0 * 0.1,
        'combined_total': 0.91,
        'weights': {
            'llm_weight': 0.3,
            'logprob_weight': 0.6,
            'validation_weight': 0.1
        }
    }
    
    print(f"Valeur détectée: {transit_comp.value}")
    print()
    print("Contributions à la confiance finale:")
    print(f"  🤖 LLM ({breakdown_example['weights']['llm_weight']:.0%}): {breakdown_example['llm_contribution']:.3f}")
    print(f"  📈 Logprobs ({breakdown_example['weights']['logprob_weight']:.0%}): {breakdown_example['logprob_contribution']:.3f}")
    print(f"  ✅ Validation ({breakdown_example['weights']['validation_weight']:.0%}): {breakdown_example['validation_contribution']:.3f}")
    print(f"  📊 TOTAL: {breakdown_example['combined_total']:.3f} ({breakdown_example['combined_total']:.1%})")
    print()
    
    print("💡 Cette démonstration montre comment les différents types de confiance")
    print("   se combinent pour produire un score final fiable.")

def show_examples_of_logprob_matching():
    """Montre des exemples de correspondance logprobs"""
    print("\n📚 EXEMPLES DE CORRESPONDANCE LOGPROBS")
    print("=" * 60)
    
    examples = [
        {
            "title": "Correspondance exacte",
            "tokens": ['{"transit": "', '12345', '", "institution":'],
            "logprobs": [-0.1, -0.2, -0.05],
            "target": "12345",
            "explanation": "Token '12345' trouvé exactement à l'index 1",
            "confidence": "exp(-0.2) ≈ 0.819"
        },
        {
            "title": "Reconstruction de tokens",
            "tokens": ['"account": "', '987', '654', '321', '"'],
            "logprobs": [-0.05, -0.3, -0.25, -0.4, -0.1],
            "target": "987654321",
            "explanation": "Reconstruction: '987' + '654' + '321' = '987654321'",
            "confidence": "moyenne_géométrique(0.741, 0.779, 0.670) ≈ 0.729"
        },
        {
            "title": "Correspondance approximative",
            "tokens": ['I see transit', ' ', '1', '2', '3', '4', '5', ' here'],
            "logprobs": [-0.2, -0.1, -0.5, -0.4, -0.3, -0.6, -0.7, -0.2],
            "target": "12345",
            "explanation": "Stratégie approximative: tokens '1','2','3','4','5'",
            "confidence": "moyenne_pondérée ≈ 0.613"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"Exemple {i}: {example['title']}")
        print(f"  Tokens: {example['tokens']}")
        print(f"  Logprobs: {example['logprobs']}")
        print(f"  Target: '{example['target']}'")
        print(f"  📝 {example['explanation']}")
        print(f"  🎯 Confiance: {example['confidence']}")
        print()

def main():
    """Fonction principale d'exemple"""
    
    # Configuration
    print("🔧 Configuration du MICR Reader")
    print("-" * 30)
    
    # Vérifier la configuration
    try:
        config.validate()
        print("✅ Configuration valide")
    except ValueError as e:
        print(f"❌ Erreur de configuration: {e}")
        print("💡 Assurez-vous d'avoir configuré votre clé API OpenAI")
        return
    
    # Chemin vers votre image de test
    # Modifiez ce chemin pour pointer vers votre chèque
    IMAGE_PATH = "./examples/specheck1.png"  # Remplacez par votre image
    
    # Vérifier que l'image existe
    if not os.path.exists(IMAGE_PATH):
        print(f"❌ Image non trouvée: {IMAGE_PATH}")
        print("💡 Placez une image de chèque et modifiez IMAGE_PATH dans le script")
        
        # Créer un exemple fictif pour démonstration
        print("\n📝 Création d'un exemple fictif pour démonstration...")
        create_demo_result()
        return
    
    print(f"📁 Analyse de: {IMAGE_PATH}")
    print()
    
    # Initialiser les composants
    print("🚀 Initialisation...")
    image_processor = ImageProcessor()
    analyzer = MICRAnalyzer()
    validator = MICRValidator()
    
    # Vérifier l'image
    print("🔍 Validation de l'image...")
    if not image_processor.validate_image(IMAGE_PATH):
        print("❌ Image invalide")
        return
    
    # Afficher les informations de l'image
    image_info = image_processor.get_image_info(IMAGE_PATH)
    print(f"📋 Info image: {image_info['width']}x{image_info['height']} pixels, {image_info['file_size_mb']:.1f}MB")
    
    # Estimer le temps de traitement
    estimated_time = image_processor.estimate_processing_time(IMAGE_PATH)
    print(f"⏱️  Temps estimé: ~{estimated_time:.1f}s")
    print()
    
    # Analyser le chèque
    print("🔍 Analyse du code MICR en cours...")
    result = analyzer.analyze_micr(IMAGE_PATH)
    
    # Valider le résultat
    validations = validator.validate_canadian_micr(result)
    
    # Afficher les résultats
    print_micr_results(result, validations)
    
    # Démonstration de l'analyse de confiance détaillée
    if result.success and result.transit_number:
        demonstrate_confidence_analysis(analyzer, result.transit_number)
    
    # Conseils basés sur les résultats
    print("💡 CONSEILS:")
    print("-" * 15)
    
    if result.success:
        low_conf = result.get_low_confidence_components()
        if low_conf:
            print("• Composants avec confiance faible détectés:")
            for comp_type, comp in low_conf.items():
                print(f"  - {comp_type.value}: {comp.combined_confidence:.1%}")
            print("• Considérez une nouvelle analyse avec une image de meilleure qualité")
        else:
            print("• Excellente qualité de détection!")
        
        if not result.is_complete_micr():
            print("• Code MICR incomplet - vérifiez que tous les éléments sont visibles")
    else:
        print("• Essayez avec une image de meilleure résolution")
        print("• Assurez-vous que le code MICR est clairement visible")
        print("• Vérifiez l'éclairage et l'absence de reflets")

if __name__ == "__main__":
    try:
        main()
        show_examples_of_logprob_matching()
        
        print("\n🎉 ANALYSE TERMINÉE")
        print("=" * 30)
        print("Pour utiliser le MICR Reader:")
        print("1. Configurez votre clé API OpenAI dans config.py")
        print("2. Placez vos images de chèques dans un dossier")
        print("3. Modifiez IMAGE_PATH dans ce script")
        print("4. Lancez: python examples/basic_usage.py")
        print()
        print("Pour le traitement en lot: python examples/batch_processing.py")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Analyse interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
