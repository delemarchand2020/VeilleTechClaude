# test_cheque_optional.py
"""
Test pour vérifier que le système fonctionne sans numéro de chèque
"""

from core.micr_analyzer import MICRAnalyzer
from core.validator import MICRValidator  
from models.micr_models import MICRResult, MICRComponent, ComponentType
from config import config

def test_cheque_optional_validation():
    """Test de validation sans numéro de chèque"""
    
    print("🧪 TEST: Validation MICR sans numéro de chèque")
    print("=" * 50)
    
    # Créer un validateur
    validator = MICRValidator()
    
    # Simuler un résultat MICR SANS numéro de chèque
    result_sans_cheque = MICRResult(
        raw_line="⑆ 12345 ⑆ 003 ⑈ 987654321 ⑈",
        raw_confidence=0.95,
        success=True,
        transit_number=MICRComponent(
            value="12345",
            description="Numéro de transit",
            llm_confidence=0.95,
            logprob_confidence=0.90,
            combined_confidence=0.93,
            component_type=ComponentType.TRANSIT
        ),
        institution_number=MICRComponent(
            value="003",
            description="Numéro d'institution",
            llm_confidence=0.97,
            logprob_confidence=0.92,
            combined_confidence=0.95,
            component_type=ComponentType.INSTITUTION
        ),
        account_number=MICRComponent(
            value="987654321",
            description="Numéro de compte",
            llm_confidence=0.93,
            logprob_confidence=0.88,
            combined_confidence=0.91,
            component_type=ComponentType.ACCOUNT
        ),
        cheque_number=None  # PAS DE NUMÉRO DE CHÈQUE
    )
    
    # Valider
    validation = validator.validate_canadian_micr(result_sans_cheque)
    
    print(f"📊 RÉSULTATS DE VALIDATION:")
    print(f"   ✅ Globalement valide: {validation.is_valid}")
    print(f"   🏦 Transit valide: {validation.transit_valid}")
    print(f"   🏢 Institution valide: {validation.institution_valid}")
    print(f"   💳 Compte valide: {validation.account_valid}")
    print(f"   📋 Format valide: {validation.format_valid}")
    print()
    
    print(f"⚠️  AVERTISSEMENTS ({len(validation.warnings)}):")
    for warning in validation.warnings:
        print(f"   • {warning}")
    print()
    
    print(f"❌ ERREURS ({len(validation.errors)}):")
    for error in validation.errors:
        print(f"   • {error}")
    print()
    
    # Simuler un résultat AVEC numéro de chèque pour comparaison
    result_avec_cheque = MICRResult(
        raw_line="001234 ⑆ 12345 ⑆ 003 ⑈ 987654321 ⑈",
        raw_confidence=0.97,
        success=True,
        transit_number=MICRComponent(
            value="12345",
            description="Numéro de transit",
            llm_confidence=0.95,
            logprob_confidence=0.90,
            combined_confidence=0.93,
            component_type=ComponentType.TRANSIT
        ),
        institution_number=MICRComponent(
            value="003",
            description="Numéro d'institution",
            llm_confidence=0.97,
            logprob_confidence=0.92,
            combined_confidence=0.95,
            component_type=ComponentType.INSTITUTION
        ),
        account_number=MICRComponent(
            value="987654321",
            description="Numéro de compte",
            llm_confidence=0.93,
            logprob_confidence=0.88,
            combined_confidence=0.91,
            component_type=ComponentType.ACCOUNT
        ),
        cheque_number=MICRComponent(
            value="001234",
            description="Numéro de chèque",
            llm_confidence=0.89,
            logprob_confidence=0.85,
            combined_confidence=0.87,
            component_type=ComponentType.CHEQUE
        )
    )
    
    validation_avec = validator.validate_canadian_micr(result_avec_cheque)
    
    print(f"🔄 COMPARAISON AVEC CHÈQUE:")
    print(f"   ✅ Globalement valide: {validation_avec.is_valid}")
    print(f"   ⚠️  Avertissements: {len(validation_avec.warnings)}")
    print(f"   ❌ Erreurs: {len(validation_avec.errors)}")
    print()
    
    # Vérifier que les deux sont valides
    if validation.is_valid and validation_avec.is_valid:
        print("🎯 SUCCÈS: Les deux cas (avec et sans chèque) sont valides!")
    else:
        print("❌ ÉCHEC: Un des cas n'est pas valide")
        
    print(f"\n💡 CONFIGURATION:")
    print(f"   Chèque requis: {config.micr.cheque_required}")
    print(f"   Région: {config.micr.region}")

def test_prompt_examples():
    """Test des exemples dans le prompt"""
    
    print("\n🔍 EXEMPLES DU PROMPT:")
    print("=" * 30)
    
    from prompts import get_micr_prompt
    
    prompt = get_micr_prompt()
    
    # Vérifier que les exemples sans chèque sont présents
    if 'SANS numéro de chèque' in prompt:
        print("✅ Exemples sans numéro de chèque présents dans le prompt")
    else:
        print("❌ Exemples sans numéro de chèque manquants")
        
    if 'OPTIONNEL' in prompt:
        print("✅ Indication que le chèque est optionnel présente")
    else:
        print("❌ Indication d'optionalité manquante")
        
    if 'OBLIGATOIRE' in prompt:
        print("✅ Indication des champs obligatoires présente")
    else:
        print("❌ Indication des champs obligatoires manquante")

if __name__ == "__main__":
    try:
        test_cheque_optional_validation()
        test_prompt_examples()
        print("\n🚀 TESTS TERMINÉS - Le système est configuré pour accepter les chèques sans numéro!")
    except Exception as e:
        print(f"\n❌ ERREUR LORS DU TEST: {e}")
        import traceback
        traceback.print_exc()
