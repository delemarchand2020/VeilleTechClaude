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
    
    def calculate_logprob_confidence(self, logprobs_data, target_text: str) -> float:
        """
        Calcule la confiance basée sur les logprobs pour un texte donné - FORMAT OPENAI v1.0+
        
        Args:
            logprobs_data: Données logprobs d'OpenAI (ChoiceLogprobs object ou dict)
            target_text: Texte pour lequel calculer la confiance
            
        Returns:
            Score de confiance basé sur les logprobs (0.0 à 1.0)
        """
        if not logprobs_data or not target_text:
            return 0.0
            
        try:
            # Nouveau format OpenAI v1.0+ - extraire depuis ChoiceLogprobs
            tokens = []
            token_logprobs = []
            
            # Debug: afficher la structure pour comprendre
            print(f"  🔍 Structure logprobs_data: {type(logprobs_data)}")
            
            # Gérer différents formats d'entrée
            content_data = None
            
            # Si c'est un objet ChoiceLogprobs direct
            if hasattr(logprobs_data, 'content'):
                content_data = logprobs_data.content
                print(f"  📝 Content direct trouvé, type: {type(content_data)}")
            
            # Si c'est un dictionnaire (après .dict())
            elif isinstance(logprobs_data, dict) and 'content' in logprobs_data:
                content_data = logprobs_data['content']
                print(f"  📝 Content depuis dict trouvé, type: {type(content_data)}")
            
            else:
                print(f"  ❌ Pas de content dans logprobs_data")
                print(f"  🔍 Attributs disponibles: {dir(logprobs_data) if hasattr(logprobs_data, '__dict__') else 'N/A'}")
                return 0.0
            
            # Extraire les tokens et logprobs
            if content_data and len(content_data) > 0:
                print(f"  📝 Content trouvé, nombre d'éléments: {len(content_data)}")
                
                for i, content_item in enumerate(content_data):
                    # Gérer objet token ou dictionnaire
                    token_val = None
                    logprob_val = None
                    
                    if hasattr(content_item, 'token') and hasattr(content_item, 'logprob'):
                        token_val = content_item.token
                        logprob_val = content_item.logprob
                    elif isinstance(content_item, dict):
                        token_val = content_item.get('token')
                        logprob_val = content_item.get('logprob')
                    
                    if token_val is not None and logprob_val is not None:
                        tokens.append(token_val)
                        token_logprobs.append(logprob_val)
                        if i < 10:  # Debug: afficher les 10 premiers tokens
                            print(f"    Token {i}: '{token_val}' (logprob: {logprob_val:.3f})")
                
                print(f"  ✅ Extracted {len(tokens)} tokens")
            else:
                print(f"  ❌ Content vide ou None")
                return 0.0
            
            if not tokens or not token_logprobs:
                print(f"  ❌ Tokens ou logprobs vides")
                return 0.0
            
            # Première tentative: correspondance exacte
            exact_confidence = self._exact_match_confidence(tokens, token_logprobs, target_text)
            if exact_confidence > 0:
                print(f"  ✅ Correspondance exacte trouvée: {exact_confidence:.3f}")
                return exact_confidence
            
            # Deuxième tentative: reconstruction de tokens
            reconstruction_confidence = self._reconstruction_confidence(tokens, token_logprobs, target_text)
            if reconstruction_confidence > 0:
                print(f"  ✅ Correspondance par reconstruction: {reconstruction_confidence:.3f}")
                return reconstruction_confidence
            
            # Troisième tentative: correspondance approximative
            approx_confidence = self._approximate_logprob_confidence(tokens, token_logprobs, target_text)
            print(f"  📊 Correspondance approximative: {approx_confidence:.3f}")
            return approx_confidence
            
        except Exception as e:
            print(f"  ❌ Erreur dans calculate_logprob_confidence: {e}")
            import traceback
            print(f"  📋 Traceback: {traceback.format_exc()}")
            return 0.0
    
    def _exact_match_confidence(self, tokens: List[str], token_logprobs: List[float], target_text: str) -> float:
        """
        Cherche une correspondance exacte du target_text dans les tokens
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
        """
        if not target_text:
            return 0.0
        
        # Nettoyer le texte cible
        clean_target = ''.join(c for c in target_text if c.isalnum())
        
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
        json_number_pattern = f'"{clean_target}"'  # "12345"
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
        return 0.15  # 15% de confiance par défaut plutôt que 0%
    
    def combine_confidences(self, llm_conf: float, logprob_conf: float, validation_passed: bool = True) -> float:
        """
        Combine les différents types de confiance en un score final
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
