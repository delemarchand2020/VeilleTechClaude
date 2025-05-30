# config.py
"""
Configuration globale pour le MICR Reader
"""

import os
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class OpenAIConfig:
    """Configuration pour l'API OpenAI"""
    api_key: str
    model: str = "gpt-4o"
    max_tokens: int = 1000
    temperature: float = 0.1
    logprobs: bool = True
    top_logprobs: int = 5

@dataclass
class ConfidenceConfig:
    """Configuration pour le calcul de confiance"""
    llm_weight: float = 0.3
    logprob_weight: float = 0.6
    validation_weight: float = 0.1
    min_confidence_threshold: float = 0.5

@dataclass
class MICRConfig:
    """Configuration pour la validation MICR canadien"""
    transit_length: int = 5
    institution_length: int = 3
    min_account_length: int = 3
    max_account_length: int = 20

@dataclass
class ImageConfig:
    """Configuration pour le traitement d'images"""
    max_file_size_mb: int = 10
    supported_formats: list = None
    image_detail: str = "high"  # "low", "high", "auto"
    
    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']

class Config:
    """Configuration principale de l'application"""
    
    def __init__(self):
        # Charger depuis les variables d'environnement ou valeurs par défaut
        self.openai = OpenAIConfig(
            api_key=os.getenv('OPENAI_API_KEY', 'votre-clé-api-openai'),
            model=os.getenv('OPENAI_MODEL', 'gpt-4o'),
            max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '1000')),
            temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.1'))
        )
        
        self.confidence = ConfidenceConfig(
            llm_weight=float(os.getenv('CONFIDENCE_LLM_WEIGHT', '0.3')),
            logprob_weight=float(os.getenv('CONFIDENCE_LOGPROB_WEIGHT', '0.6')),
            validation_weight=float(os.getenv('CONFIDENCE_VALIDATION_WEIGHT', '0.1')),
            min_confidence_threshold=float(os.getenv('MIN_CONFIDENCE_THRESHOLD', '0.5'))
        )
        
        self.micr = MICRConfig()
        self.image = ImageConfig()
    
    def validate(self) -> bool:
        """Valide la configuration"""
        if not self.openai.api_key or self.openai.api_key == 'votre-clé-api-openai':
            raise ValueError("Clé API OpenAI manquante. Définissez OPENAI_API_KEY ou modifiez config.py")
        
        # Vérifier que les poids de confiance totalisent 1.0
        total_weight = (self.confidence.llm_weight + 
                       self.confidence.logprob_weight + 
                       self.confidence.validation_weight)
        
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Les poids de confiance doivent totaliser 1.0, actuellement: {total_weight}")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit la configuration en dictionnaire"""
        return {
            'openai': {
                'model': self.openai.model,
                'max_tokens': self.openai.max_tokens,
                'temperature': self.openai.temperature,
                'logprobs': self.openai.logprobs,
                'top_logprobs': self.openai.top_logprobs
            },
            'confidence': {
                'llm_weight': self.confidence.llm_weight,
                'logprob_weight': self.confidence.logprob_weight,
                'validation_weight': self.confidence.validation_weight,
                'min_confidence_threshold': self.confidence.min_confidence_threshold
            },
            'micr': {
                'transit_length': self.micr.transit_length,
                'institution_length': self.micr.institution_length,
                'min_account_length': self.micr.min_account_length,
                'max_account_length': self.micr.max_account_length
            },
            'image': {
                'max_file_size_mb': self.image.max_file_size_mb,
                'supported_formats': self.image.supported_formats,
                'image_detail': self.image.image_detail
            }
        }

# Instance globale de configuration
config = Config()

# Validation au chargement du module
try:
    config.validate()
    print("✅ Configuration chargée avec succès")
except ValueError as e:
    print(f"❌ Erreur de configuration: {e}")
    print("💡 Conseil: Copiez config.py.example vers config.py et configurez votre clé API")
