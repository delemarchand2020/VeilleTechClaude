# models/micr_models.py
"""
Classes de données pour le MICR Reader
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class ComponentType(Enum):
    """Types de composants MICR"""
    TRANSIT = "transit_number"
    INSTITUTION = "institution_number"
    ACCOUNT = "account_number"
    CHEQUE = "cheque_number"
    AMOUNT = "amount"
    AUXILIARY = "auxiliary_on_us"

@dataclass
class MICRComponent:
    """
    Représente une composante du code MICR avec ses différents types de confiance
    
    Attributes:
        value: La valeur extraite (ex: "12345")
        description: Description du composant (ex: "Numéro de transit")
        llm_confidence: Confiance subjective du LLM (0.0 à 1.0)
        logprob_confidence: Confiance basée sur les logprobs (0.0 à 1.0)
        combined_confidence: Confiance finale combinée (0.0 à 1.0)
        component_type: Type de composant MICR
        raw_tokens: Tokens bruts utilisés pour extraire cette valeur
        validation_passed: Si ce composant a passé la validation de format
    """
    value: str
    description: str
    llm_confidence: float
    logprob_confidence: float
    combined_confidence: float
    component_type: ComponentType
    raw_tokens: Optional[list] = None
    validation_passed: bool = True
    
    @property
    def confidence(self) -> float:
        """Alias pour combined_confidence pour compatibilité"""
        return self.combined_confidence
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Détermine si ce composant a une confiance élevée"""
        return self.combined_confidence >= threshold
    
    def is_valid(self) -> bool:
        """Détermine si ce composant est valide (valeur non vide et validation passée)"""
        return bool(self.value) and self.validation_passed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour sérialisation"""
        return {
            'value': self.value,
            'description': self.description,
            'llm_confidence': self.llm_confidence,
            'logprob_confidence': self.logprob_confidence,
            'combined_confidence': self.combined_confidence,
            'component_type': self.component_type.value,
            'validation_passed': self.validation_passed,
            'is_high_confidence': self.is_high_confidence(),
            'is_valid': self.is_valid()
        }

@dataclass
class MICRResult:
    """
    Résultat complet de l'analyse MICR
    
    Attributes:
        raw_line: Ligne MICR complète telle que détectée
        raw_confidence: Confiance globale de la détection
        success: Si l'analyse a réussi
        error_message: Message d'erreur en cas d'échec
        transit_number: Composant numéro de transit
        institution_number: Composant numéro d'institution
        account_number: Composant numéro de compte
        cheque_number: Composant numéro de chèque
        amount: Composant montant (si présent)
        auxiliary_on_us: Composant données auxiliaires (si présent)
        processing_time: Temps de traitement en secondes
        image_path: Chemin vers l'image analysée
    """
    raw_line: str
    raw_confidence: float
    success: bool
    error_message: Optional[str] = None
    transit_number: Optional[MICRComponent] = None
    institution_number: Optional[MICRComponent] = None
    account_number: Optional[MICRComponent] = None
    cheque_number: Optional[MICRComponent] = None
    amount: Optional[MICRComponent] = None
    auxiliary_on_us: Optional[MICRComponent] = None
    processing_time: Optional[float] = None
    image_path: Optional[str] = None
    
    def get_component(self, component_type: ComponentType) -> Optional[MICRComponent]:
        """Récupère un composant par son type"""
        component_map = {
            ComponentType.TRANSIT: self.transit_number,
            ComponentType.INSTITUTION: self.institution_number,
            ComponentType.ACCOUNT: self.account_number,
            ComponentType.CHEQUE: self.cheque_number,
            ComponentType.AMOUNT: self.amount,
            ComponentType.AUXILIARY: self.auxiliary_on_us
        }
        return component_map.get(component_type)
    
    def get_all_components(self) -> Dict[ComponentType, Optional[MICRComponent]]:
        """Récupère tous les composants dans un dictionnaire"""
        return {
            ComponentType.TRANSIT: self.transit_number,
            ComponentType.INSTITUTION: self.institution_number,
            ComponentType.ACCOUNT: self.account_number,
            ComponentType.CHEQUE: self.cheque_number,
            ComponentType.AMOUNT: self.amount,
            ComponentType.AUXILIARY: self.auxiliary_on_us
        }
    
    def get_valid_components(self) -> Dict[ComponentType, MICRComponent]:
        """Récupère seulement les composants valides"""
        valid_components = {}
        for comp_type, component in self.get_all_components().items():
            if component and component.is_valid():
                valid_components[comp_type] = component
        return valid_components
    
    def get_low_confidence_components(self, threshold: float = 0.7) -> Dict[ComponentType, MICRComponent]:
        """Récupère les composants avec une confiance faible"""
        low_conf_components = {}
        for comp_type, component in self.get_all_components().items():
            if component and component.combined_confidence < threshold:
                low_conf_components[comp_type] = component
        return low_conf_components
    
    def get_overall_confidence(self) -> float:
        """Calcule la confiance globale basée sur les composants essentiels"""
        essential_components = [
            self.transit_number,
            self.institution_number,
            self.account_number
        ]
        
        valid_confidences = [
            comp.combined_confidence for comp in essential_components 
            if comp and comp.is_valid()
        ]
        
        if not valid_confidences:
            return 0.0
        
        # Moyenne pondérée (les composants manquants réduisent la confiance)
        avg_confidence = sum(valid_confidences) / len(valid_confidences)
        completeness_factor = len(valid_confidences) / len(essential_components)
        
        return avg_confidence * completeness_factor
    
    def is_complete_micr(self) -> bool:
        """Détermine si tous les composants essentiels sont présents et valides"""
        essential_components = [
            self.transit_number,
            self.institution_number, 
            self.account_number
        ]
        
        return all(comp and comp.is_valid() for comp in essential_components)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour sérialisation JSON"""
        result = {
            'raw_line': self.raw_line,
            'raw_confidence': self.raw_confidence,
            'success': self.success,
            'error_message': self.error_message,
            'processing_time': self.processing_time,
            'image_path': self.image_path,
            'overall_confidence': self.get_overall_confidence(),
            'is_complete': self.is_complete_micr(),
            'components': {}
        }
        
        # Ajouter tous les composants
        for comp_type, component in self.get_all_components().items():
            if component:
                result['components'][comp_type.value] = component.to_dict()
            else:
                result['components'][comp_type.value] = None
        
        return result
    
    def to_csv_row(self) -> Dict[str, str]:
        """Convertit en ligne CSV pour export"""
        return {
            'image_path': self.image_path or '',
            'success': str(self.success),
            'raw_line': self.raw_line,
            'transit_number': self.transit_number.value if self.transit_number else '',
            'transit_confidence': f"{self.transit_number.combined_confidence:.3f}" if self.transit_number else '',
            'institution_number': self.institution_number.value if self.institution_number else '',
            'institution_confidence': f"{self.institution_number.combined_confidence:.3f}" if self.institution_number else '',
            'account_number': self.account_number.value if self.account_number else '',
            'account_confidence': f"{self.account_number.combined_confidence:.3f}" if self.account_number else '',
            'cheque_number': self.cheque_number.value if self.cheque_number else '',
            'cheque_confidence': f"{self.cheque_number.combined_confidence:.3f}" if self.cheque_number else '',
            'overall_confidence': f"{self.get_overall_confidence():.3f}",
            'is_complete': str(self.is_complete_micr()),
            'processing_time': f"{self.processing_time:.2f}" if self.processing_time else '',
            'error_message': self.error_message or ''
        }

@dataclass
class ValidationResult:
    """
    Résultat de validation d'un code MICR
    
    Attributes:
        is_valid: Si le code MICR global est valide
        transit_valid: Si le numéro de transit est valide
        institution_valid: Si le numéro d'institution est valide
        account_valid: Si le numéro de compte est valide
        format_valid: Si le format général est respecté
        errors: Liste des erreurs détectées
        warnings: Liste des avertissements
    """
    is_valid: bool
    transit_valid: bool
    institution_valid: bool  
    account_valid: bool
    format_valid: bool
    errors: list
    warnings: list
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            'is_valid': self.is_valid,
            'transit_valid': self.transit_valid,
            'institution_valid': self.institution_valid,
            'account_valid': self.account_valid,
            'format_valid': self.format_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }
