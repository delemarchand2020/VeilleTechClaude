# core/confidence_calculator.py
"""
Calculateur de confiance basé sur les logprobs et autres métriques
"""

import math
from typing import Dict, List, Optional, Tuple
from config import config

class ConfidenceCalculator:
    """
    Calcule la confiance en combinant logprobs, validation et évaluation LLM
    """
    
    def __init__(self, custom_weights: Optional[Dict[str, float]] = None):
        """
        Initialise le calculateur avec des poids personnalisés
        
        Args:
            custom_weights: Poids personnalisés pour llm, logprob, validation
        """
        if custom_weights:
            self.llm_weight = custom_weights.get('llm', config.confidence.llm_weight)
            self.logprob_weight = custom_weights.get('logprob', config.confidence.logprob_weight)
            self.validation_weight = custom_weights.get('validation', config.confidence.validation_weight)
        else:
            self.llm_weight = config.confidence.llm_weight
            self.logprob_weight = config.confidence.logprob_weight
            self.validation_weight = config.confidence.validation_weight
    
    def calculate_logprob_confidence(self, logprobs_data: Dict, target_text: str) -> float:
        """
        Calcule la confiance basée sur les logprobs pour un texte donné
        
        Args:
            logprobs_data: Données logprobs d'OpenAI
            target_text: Texte pour lequel calculer la confiance
            
        Returns:
            Score de confiance basé sur les logprobs (0.0 à 1.0)
            
        Examples:
            # Correspondance exacte
            logprobs = {
                'tokens': ['{"transit": "', '12345', '", "institution":'],
                'token_logprobs': [-0.1, -0.2, -0.05]
            }
            confidence = calculator.calculate_logprob_confidence(logprobs, "12345")
            # Résultat: exp(-0.2) ≈ 0.819
            
            # Correspondance par reconstruction
            logprobs = {
                'tokens': ['"account": "', '987', '654', '321', '"'],
                'token_logprobs': [-0.05, -0.3, -0.25, -0.4, -0.1]
            }
            confidence = calculator.calculate_logprob_confidence(logprobs, "987654321")
            # Résultat: moyenne_géométrique(0.741, 0.779, 0.670) ≈ 0.729
        """
        if not logprobs_data or not target_text:
            return 0.0
            
        try:
            # Extraire les tokens et leurs logprobs
            tokens = logprobs_data.get('tokens', [])
            token_logprobs = logprobs_data.get('token_logprobs', [])
            
            if not tokens or not token_logprobs:
                return 0.0
            
            # Première tentative: correspondance exacte
            exact_confidence = self._exact_match_confidence(tokens, token_logprobs, target_text)
            if exact_confidence > 0:
                return exact_confidence
            
            # Deuxième tentative: reconstruction de tokens
            reconstruction_confidence = self._reconstruction_confidence(tokens, token_logprobs, target_text)
            if reconstruction_confidence > 0:
                return reconstruction_confidence
            
            # Troisième tentative: correspondance approximative
            return self._approximate_logprob_confidence(tokens, token_logprobs, target_text)
            
        except Exception as e:
            print(f"Erreur calcul logprobs: {e}")
            return 0.0
    
    def _exact_match_confidence(self, tokens: List[str], token_logprobs: List[float], target_text: str) -> float:
        """
        Cherche une correspondance exacte du target_text dans les tokens
        
        Example:
            tokens = ['{"transit": "', '12345', '", ']
            target_text = "12345"
            # Trouve directement "12345" à l'index 1
        """
        for i, token in enumerate(tokens):
            if i < len(token_logprobs) and token_logprobs[i] is not None:
                # Nettoyer le token des espaces et caractères spéciaux pour la comparaison
                clean_token = ''.join(c for c in token if c.isalnum())
                clean_target = ''.join(c for c in target_text if c.isalnum())
                
                if clean_token == clean_target:
                    return min(math.exp(token_logprobs[i]), 1.0)
        
        return 0.0
    
    def _reconstruction_confidence(self, tokens: List[str], token_logprobs: List[float], target_text: str) -> float:
        """
        Tente de reconstruire le target_text à partir de tokens contigus
        
        Example:
            tokens = ['"account": "', '987', '654', '321', '"']
            target_text = "987654321"
            # Reconstruit "987" + "654" + "321" = "987654321"
        """
        # Reconstituer le texte à partir des tokens pour trouver la position
        full_text = ''.join(tokens)
        target_start = full_text.find(target_text)
        
        if target_start == -1:
            return 0.0
        
        # Identifier les tokens qui correspondent au texte cible
        target_logprobs = []
        char_count = 0
        
        for i, token in enumerate(tokens):
            token_start = char_count
            token_end = char_count + len(token)
            
            # Si ce token chevauche avec notre target_text
            if (token_start < target_start + len(target_text) and 
                token_end > target_start and 
                i < len(token_logprobs) and 
                token_logprobs[i] is not None):
                target_logprobs.append(token_logprobs[i])
            
            char_count += len(token)
            
            if char_count >= target_start + len(target_text):
                break
        
        if not target_logprobs:
            return 0.0
        
        # Calculer la moyenne géométrique pour éviter qu'un token très incertain domine
        probabilities = [math.exp(logprob) for logprob in target_logprobs]
        geometric_mean = math.pow(math.prod(probabilities), 1.0 / len(probabilities))
        
        return min(geometric_mean, 1.0)
    
    def _approximate_logprob_confidence(self, tokens: List[str], token_logprobs: List[float], target_text: str) -> float:
        """
        Calcule une confiance approximative avec recherche fuzzy améliorée
        
        Examples:
            # Stratégie 1: Correspondance de sous-chaînes
            tokens = ['I see transit', ' ', '123', '45', ' here']
            target_text = "12345"
            # "123" contient 1,2,3 de "12345" ✓
            # "45" contient 4,5 de "12345" ✓
            
            # Stratégie 2: Correspondance des chiffres
            tokens = ['numbers found:', ' ', '1', '2', '3', '4', '5']
            target_text = "12345"
            # Chaque chiffre individuel matche ✓
        """
        if not target_text:
            return 0.0
        
        # Nettoyer le texte cible
        clean_target = ''.join(c for c in target_text if c.isalnum())
        relevant_logprobs = []
        
        # NOUVELLE Stratégie 0: Recherche de séquences complètes dans les tokens
        for i, token in enumerate(tokens):
            if i >= len(token_logprobs) or token_logprobs[i] is None:
                continue
            
            # Chercher le target_text complet dans le token (avec variations)
            clean_token = ''.join(c for c in token if c.isalnum())
            if clean_token == clean_target:
                # Correspondance exacte trouvée!
                return min(math.exp(token_logprobs[i]), 1.0)
        
        # Stratégie 1: Correspondances de sous-chaînes
        substring_matches = []
        for i, token in enumerate(tokens):
            if i >= len(token_logprobs) or token_logprobs[i] is None:
                continue
                
            clean_token = ''.join(c for c in token if c.isalnum())
            
            # Si le token contient une partie significative du texte cible
            if clean_token and clean_target:
                if clean_token in clean_target or clean_target in clean_token:
                    substring_matches.append((token_logprobs[i], len(clean_token)))
                elif len(clean_token) >= 2 and any(clean_token in clean_target[j:j+len(clean_token)] for j in range(len(clean_target)-len(clean_token)+1)):
                    substring_matches.append((token_logprobs[i], len(clean_token)))
        
        if substring_matches:
            # Pondérer par la longueur des correspondances
            total_weight = sum(weight for _, weight in substring_matches)
            if total_weight > 0:
                weighted_logprob = sum(logprob * weight for logprob, weight in substring_matches) / total_weight
                confidence = min(math.exp(weighted_logprob), 1.0)
                if confidence > 0.1:  # Seuil minimum pour considérer comme valide
                    return confidence
        
        # Stratégie 2: Correspondance de chiffres individuels pour les nombres
        if clean_target.isdigit() and len(clean_target) >= 3:
            target_digits = list(clean_target)
            digit_matches = []
            
            for i, token in enumerate(tokens):
                if i >= len(token_logprobs) or token_logprobs[i] is None:
                    continue
                    
                token_digits = ''.join(c for c in token if c.isdigit())
                
                # Vérifier si ce token contient des chiffres de notre séquence
                if token_digits:
                    for digit in token_digits:
                        if digit in target_digits:
                            digit_matches.append(token_logprobs[i])
                            break  # Un seul match par token pour éviter la duplication
            
            if len(digit_matches) >= len(target_digits) * 0.6:  # Au moins 60% des chiffres trouvés
                probabilities = [math.exp(logprob) for logprob in digit_matches[:len(target_digits)]]
                confidence = sum(probabilities) / len(probabilities)
                if confidence > 0.1:
                    return min(confidence, 1.0)
        
        # Stratégie 3: Recherche de patterns numériques dans les JSON
        json_number_pattern = f'\"{clean_target}\"'  # "12345"
        for i, token in enumerate(tokens):
            if i >= len(token_logprobs) or token_logprobs[i] is None:
                continue
            
            if clean_target in token or json_number_pattern in token:
                return min(math.exp(token_logprobs[i]), 1.0)
        
        # Stratégie 4: Fallback général - tokens numériques
        numeric_logprobs = []
        for i, token in enumerate(tokens):
            if (i < len(token_logprobs) and token_logprobs[i] is not None and 
                any(char.isdigit() for char in token) and 
                len(''.join(c for c in token if c.isdigit())) >= 2):  # Au moins 2 chiffres
                numeric_logprobs.append(token_logprobs[i])
        
        if numeric_logprobs:
            # Prendre les meilleurs tokens numériques
            numeric_logprobs.sort(reverse=True)  # Trier par logprob (meilleur = plus proche de 0)
            best_logprobs = numeric_logprobs[:min(3, len(numeric_logprobs))]  # Top 3
            probabilities = [math.exp(logprob) for logprob in best_logprobs]
            return sum(probabilities) / len(probabilities)
        
        # Si aucune correspondance trouvée, retourner une confiance très faible
        return 0.1  # 10% de confiance par défaut plutôt que 0%
    
    def combine_confidences(self, llm_conf: float, logprob_conf: float, validation_passed: bool = True) -> float:
        """
        Combine les différents types de confiance en un score final
        
        Args:
            llm_conf: Confiance subjective du LLM (0.0 à 1.0)
            logprob_conf: Confiance basée sur les logprobs (0.0 à 1.0)
            validation_passed: Si la validation du format a réussi
            
        Returns:
            Confiance combinée (0.0 à 1.0)
            
        Examples:
            # Cas optimal
            combined = calculator.combine_confidences(0.9, 0.85, True)
            # Résultat: 0.9*0.3 + 0.85*0.6 + 1.0*0.1 = 0.88
            
            # Cas avec validation échouée
            combined = calculator.combine_confidences(0.9, 0.85, False)
            # Résultat: 0.9*0.3 + 0.85*0.6 + 0.5*0.1 = 0.83
        """
        # Score de validation (binaire converti en score)
        validation_score = 1.0 if validation_passed else 0.5
        
        # Moyenne pondérée
        combined = (llm_conf * self.llm_weight + 
                   logprob_conf * self.logprob_weight + 
                   validation_score * self.validation_weight)
        
        return min(combined, 1.0)
    
    def analyze_confidence_breakdown(self, llm_conf: float, logprob_conf: float, validation_passed: bool) -> Dict[str, float]:
        """
        Analyse détaillée de la répartition des confiances
        
        Returns:
            Dictionnaire avec la contribution de chaque composant
        """
        validation_score = 1.0 if validation_passed else 0.5
        
        return {
            'llm_contribution': llm_conf * self.llm_weight,
            'logprob_contribution': logprob_conf * self.logprob_weight,
            'validation_contribution': validation_score * self.validation_weight,
            'combined_total': self.combine_confidences(llm_conf, logprob_conf, validation_passed),
            'weights': {
                'llm_weight': self.llm_weight,
                'logprob_weight': self.logprob_weight,
                'validation_weight': self.validation_weight
            }
        }
