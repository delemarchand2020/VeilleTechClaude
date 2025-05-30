# tests/test_confidence.py
"""
Tests pour le système de confiance
"""

import unittest
import math
from core.confidence_calculator import ConfidenceCalculator

class TestConfidenceCalculator(unittest.TestCase):
    """Tests pour le calculateur de confiance"""
    
    def setUp(self):
        self.calculator = ConfidenceCalculator()
    
    def test_exact_match_confidence(self):
        """Test de correspondance exacte des logprobs"""
        logprobs_data = {
            'tokens': ['{"transit": "', '12345', '", "institution":'],
            'token_logprobs': [-0.1, -0.2, -0.05]
        }
        target_text = "12345"
        
        confidence = self.calculator.calculate_logprob_confidence(logprobs_data, target_text)
        expected = math.exp(-0.2)  # ≈ 0.819
        
        self.assertAlmostEqual(confidence, expected, places=3)
    
    def test_reconstruction_confidence(self):
        """Test de reconstruction de tokens"""
        logprobs_data = {
            'tokens': ['"account": "', '987', '654', '321', '"'],
            'token_logprobs': [-0.05, -0.3, -0.25, -0.4, -0.1]
        }
        target_text = "987654321"
        
        confidence = self.calculator.calculate_logprob_confidence(logprobs_data, target_text)
        
        # Devrait être la moyenne géométrique des probabilités des tokens pertinents
        expected_probs = [math.exp(-0.3), math.exp(-0.25), math.exp(-0.4)]
        expected = math.pow(math.prod(expected_probs), 1.0 / len(expected_probs))
        
        self.assertAlmostEqual(confidence, expected, places=3)
    
    def test_combine_confidences(self):
        """Test de combinaison des confiances"""
        llm_conf = 0.9
        logprob_conf = 0.85
        validation_passed = True
        
        combined = self.calculator.combine_confidences(llm_conf, logprob_conf, validation_passed)
        
        # Calcul attendu avec les poids par défaut (0.3, 0.6, 0.1)
        expected = 0.9 * 0.3 + 0.85 * 0.6 + 1.0 * 0.1
        
        self.assertAlmostEqual(combined, expected, places=3)
    
    def test_combine_confidences_validation_failed(self):
        """Test avec validation échouée"""
        llm_conf = 0.9
        logprob_conf = 0.85
        validation_passed = False
        
        combined = self.calculator.combine_confidences(llm_conf, logprob_conf, validation_passed)
        
        # Avec validation échouée, score de validation = 0.5
        expected = 0.9 * 0.3 + 0.85 * 0.6 + 0.5 * 0.1
        
        self.assertAlmostEqual(combined, expected, places=3)
    
    def test_empty_logprobs_data(self):
        """Test avec données logprobs vides"""
        confidence = self.calculator.calculate_logprob_confidence({}, "12345")
        self.assertEqual(confidence, 0.0)
        
        confidence = self.calculator.calculate_logprob_confidence(None, "12345")
        self.assertEqual(confidence, 0.0)
    
    def test_empty_target_text(self):
        """Test avec texte cible vide"""
        logprobs_data = {
            'tokens': ['test'],
            'token_logprobs': [-0.1]
        }
        
        confidence = self.calculator.calculate_logprob_confidence(logprobs_data, "")
        self.assertEqual(confidence, 0.0)
        
        confidence = self.calculator.calculate_logprob_confidence(logprobs_data, None)
        self.assertEqual(confidence, 0.0)
    
    def test_custom_weights(self):
        """Test avec poids personnalisés"""
        custom_weights = {'llm': 0.5, 'logprob': 0.4, 'validation': 0.1}
        calculator = ConfidenceCalculator(custom_weights)
        
        combined = calculator.combine_confidences(0.8, 0.7, True)
        expected = 0.8 * 0.5 + 0.7 * 0.4 + 1.0 * 0.1
        
        self.assertAlmostEqual(combined, expected, places=3)
    
    def test_confidence_breakdown(self):
        """Test de l'analyse détaillée de confiance"""
        breakdown = self.calculator.analyze_confidence_breakdown(0.9, 0.8, True)
        
        self.assertIn('llm_contribution', breakdown)
        self.assertIn('logprob_contribution', breakdown)
        self.assertIn('validation_contribution', breakdown)
        self.assertIn('combined_total', breakdown)
        self.assertIn('weights', breakdown)
        
        # Vérifier les calculs
        expected_llm = 0.9 * self.calculator.llm_weight
        expected_logprob = 0.8 * self.calculator.logprob_weight
        expected_validation = 1.0 * self.calculator.validation_weight
        
        self.assertAlmostEqual(breakdown['llm_contribution'], expected_llm, places=3)
        self.assertAlmostEqual(breakdown['logprob_contribution'], expected_logprob, places=3)
        self.assertAlmostEqual(breakdown['validation_contribution'], expected_validation, places=3)

if __name__ == '__main__':
    unittest.main()
