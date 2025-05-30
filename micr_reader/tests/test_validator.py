# tests/test_validator.py
"""
Tests pour le validateur MICR
"""

import unittest
from models.micr_models import MICRResult, MICRComponent, ComponentType
from core.validator import MICRValidator

class TestMICRValidator(unittest.TestCase):
    """Tests pour le validateur MICR"""
    
    def setUp(self):
        self.validator = MICRValidator()
    
    def create_mock_component(self, value: str, comp_type: ComponentType, confidence: float = 0.9):
        """Crée un composant MICR fictif pour les tests"""
        return MICRComponent(
            value=value,
            description=f"Test {comp_type.value}",
            llm_confidence=confidence,
            logprob_confidence=confidence,
            combined_confidence=confidence,
            component_type=comp_type,
            validation_passed=True
        )
    
    def test_valid_transit_number(self):
        """Test de validation d'un numéro de transit valide"""
        errors = []
        warnings = []
        transit_comp = self.create_mock_component("12345", ComponentType.TRANSIT)
        
        result = self.validator._validate_transit(transit_comp, errors, warnings)
        
        self.assertTrue(result)
        self.assertEqual(len(errors), 0)
    
    def test_invalid_transit_length(self):
        """Test avec numéro de transit de mauvaise longueur"""
        errors = []
        warnings = []
        transit_comp = self.create_mock_component("1234", ComponentType.TRANSIT)  # Trop court
        
        result = self.validator._validate_transit(transit_comp, errors, warnings)
        
        self.assertFalse(result)
        self.assertTrue(any("doit avoir 5 chiffres" in error for error in errors))
    
    def test_invalid_transit_non_numeric(self):
        """Test avec numéro de transit non-numérique"""
        errors = []
        warnings = []
        transit_comp = self.create_mock_component("1234A", ComponentType.TRANSIT)
        
        result = self.validator._validate_transit(transit_comp, errors, warnings)
        
        self.assertFalse(result)
        self.assertTrue(any("seulement des chiffres" in error for error in errors))
    
    def test_valid_institution_known(self):
        """Test avec institution canadienne connue"""
        errors = []
        warnings = []
        institution_comp = self.create_mock_component("003", ComponentType.INSTITUTION)  # RBC
        
        result = self.validator._validate_institution(institution_comp, errors, warnings)
        
        self.assertTrue(result)
        self.assertEqual(len(errors), 0)
        self.assertTrue(any("Banque Royale du Canada" in warning for warning in warnings))
    
    def test_valid_institution_unknown(self):
        """Test avec institution inconnue mais format valide"""
        errors = []
        warnings = []
        institution_comp = self.create_mock_component("999", ComponentType.INSTITUTION)
        
        result = self.validator._validate_institution(institution_comp, errors, warnings)
        
        self.assertTrue(result)
        self.assertEqual(len(errors), 0)
        self.assertTrue(any("Institution inconnue" in warning for warning in warnings))
    
    def test_invalid_institution_length(self):
        """Test avec numéro d'institution de mauvaise longueur"""
        errors = []
        warnings = []
        institution_comp = self.create_mock_component("12", ComponentType.INSTITUTION)
        
        result = self.validator._validate_institution(institution_comp, errors, warnings)
        
        self.assertFalse(result)
        self.assertTrue(any("doit avoir 3 chiffres" in error for error in errors))
    
    def test_valid_account_number(self):
        """Test avec numéro de compte valide"""
        errors = []
        warnings = []
        account_comp = self.create_mock_component("1234567890", ComponentType.ACCOUNT)
        
        result = self.validator._validate_account(account_comp, errors, warnings)
        
        self.assertTrue(result)
        self.assertEqual(len(errors), 0)
    
    def test_invalid_account_too_short(self):
        """Test avec numéro de compte trop court"""
        errors = []
        warnings = []
        account_comp = self.create_mock_component("12", ComponentType.ACCOUNT)
        
        result = self.validator._validate_account(account_comp, errors, warnings)
        
        self.assertFalse(result)
        self.assertTrue(any("trop court" in error for error in errors))
    
    def test_invalid_account_all_zeros(self):
        """Test avec numéro de compte que des zéros"""
        errors = []
        warnings = []
        account_comp = self.create_mock_component("0000000", ComponentType.ACCOUNT)
        
        result = self.validator._validate_account(account_comp, errors, warnings)
        
        self.assertFalse(result)
        self.assertTrue(any("que des zéros" in error for error in errors))
    
    def test_complete_micr_validation_success(self):
        """Test de validation complète réussie"""
        # Créer un résultat MICR complet et valide
        result = MICRResult(
            raw_line="⑆12345⑆003⑈1234567890⑈001⑆",
            raw_confidence=0.9,
            success=True,
            transit_number=self.create_mock_component("12345", ComponentType.TRANSIT),
            institution_number=self.create_mock_component("003", ComponentType.INSTITUTION),
            account_number=self.create_mock_component("1234567890", ComponentType.ACCOUNT),
            cheque_number=self.create_mock_component("001", ComponentType.CHEQUE)
        )
        
        validation = self.validator.validate_canadian_micr(result)
        
        self.assertTrue(validation.is_valid)
        self.assertTrue(validation.transit_valid)
        self.assertTrue(validation.institution_valid)
        self.assertTrue(validation.account_valid)
        self.assertTrue(validation.format_valid)
        self.assertEqual(len(validation.errors), 0)
    
    def test_complete_micr_validation_failure(self):
        """Test de validation complète échouée"""
        # Créer un résultat MICR avec erreurs
        result = MICRResult(
            raw_line="invalid",
            raw_confidence=0.5,
            success=True,
            transit_number=self.create_mock_component("1234", ComponentType.TRANSIT),  # Trop court
            institution_number=self.create_mock_component("12", ComponentType.INSTITUTION),  # Trop court
            account_number=self.create_mock_component("12", ComponentType.ACCOUNT),  # Trop court
        )
        
        validation = self.validator.validate_canadian_micr(result)
        
        self.assertFalse(validation.is_valid)
        self.assertFalse(validation.transit_valid)
        self.assertFalse(validation.institution_valid)
        self.assertFalse(validation.account_valid)
        self.assertTrue(len(validation.errors) > 0)
    
    def test_failed_micr_analysis(self):
        """Test avec analyse MICR échouée"""
        result = MICRResult(
            raw_line="",
            raw_confidence=0.0,
            success=False,
            error_message="Analyse échouée"
        )
        
        validation = self.validator.validate_canadian_micr(result)
        
        self.assertFalse(validation.is_valid)
        self.assertFalse(validation.transit_valid)
        self.assertFalse(validation.institution_valid)
        self.assertFalse(validation.account_valid)
        self.assertFalse(validation.format_valid)
        self.assertTrue(any("analyse MICR a échoué" in error for error in validation.errors))
    
    def test_get_institution_name(self):
        """Test de récupération du nom d'institution"""
        # Institution connue
        name = self.validator.get_institution_name("003")
        self.assertEqual(name, "Banque Royale du Canada")
        
        # Institution inconnue
        name = self.validator.get_institution_name("999")
        self.assertEqual(name, "Institution inconnue")
    
    def test_is_known_institution(self):
        """Test de vérification d'institution connue"""
        # Institution connue
        self.assertTrue(self.validator.is_known_institution("003"))
        self.assertTrue(self.validator.is_known_institution("001"))
        self.assertTrue(self.validator.is_known_institution("177"))  # Desjardins
        
        # Institution inconnue
        self.assertFalse(self.validator.is_known_institution("999"))
        self.assertFalse(self.validator.is_known_institution("000"))
    
    def test_get_all_institutions(self):
        """Test de récupération de toutes les institutions"""
        institutions = self.validator.get_all_institutions()
        
        self.assertIsInstance(institutions, dict)
        self.assertIn("003", institutions)
        self.assertIn("001", institutions)
        self.assertIn("177", institutions)
        self.assertEqual(institutions["003"], "Banque Royale du Canada")
        self.assertEqual(institutions["001"], "Banque de Montréal")
    
    def test_low_confidence_warning(self):
        """Test d'avertissement pour confiance faible"""
        errors = []
        warnings = []
        # Créer un composant avec confiance faible
        low_conf_comp = self.create_mock_component("12345", ComponentType.TRANSIT, confidence=0.6)
        
        result = self.validator._validate_transit(low_conf_comp, errors, warnings)
        
        self.assertTrue(result)  # Toujours valide malgré la confiance faible
        self.assertTrue(any("Confiance faible" in warning for warning in warnings))
    
    def test_validation_result_to_dict(self):
        """Test de conversion ValidationResult en dictionnaire"""
        result = MICRResult(
            raw_line="⑆12345⑆003⑈1234567890⑈001⑆",
            raw_confidence=0.9,
            success=True,
            transit_number=self.create_mock_component("12345", ComponentType.TRANSIT),
            institution_number=self.create_mock_component("003", ComponentType.INSTITUTION),
            account_number=self.create_mock_component("1234567890", ComponentType.ACCOUNT)
        )
        
        validation = self.validator.validate_canadian_micr(result)
        validation_dict = validation.to_dict()
        
        self.assertIsInstance(validation_dict, dict)
        self.assertIn('is_valid', validation_dict)
        self.assertIn('transit_valid', validation_dict)
        self.assertIn('institution_valid', validation_dict)
        self.assertIn('account_valid', validation_dict)
        self.assertIn('format_valid', validation_dict)
        self.assertIn('errors', validation_dict)
        self.assertIn('warnings', validation_dict)
        self.assertIn('error_count', validation_dict)
        self.assertIn('warning_count', validation_dict)

if __name__ == '__main__':
    unittest.main()
