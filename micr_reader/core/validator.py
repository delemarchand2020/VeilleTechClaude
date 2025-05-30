# core/validator.py
"""
Validateur pour les codes MICR canadiens
"""

import re
from typing import Dict, List
from models.micr_models import MICRResult, ValidationResult
from config import config

class MICRValidator:
    """
    Validateur pour les codes MICR selon les standards canadiens
    """
    
    # Banques canadiennes connues (numéros d'institution)
    CANADIAN_INSTITUTIONS = {
        '001': 'Banque de Montréal',
        '002': 'Banque Scotia',
        '003': 'Banque Royale du Canada',
        '004': 'Banque Toronto-Dominion',
        '006': 'Banque Nationale du Canada',
        '010': 'Banque Canadienne Impériale de Commerce',
        '016': 'Banque HSBC Canada',
        '030': 'Banque Canadienne de l\'Ouest',
        '039': 'Banque Laurentienne',
        '117': 'Banque Northern Trust du Canada',
        '127': 'Banque Manuvie du Canada',
        '177': 'Desjardins',
        '219': 'Tangerine',
        '260': 'CIBC Trust Corporation',
        '269': 'Simplii Financial',
        '308': 'Banque de Chine (Canada)',
        '309': 'Citibank Canada',
        '326': 'Banque Présidential',
        '338': 'Banque Équitable du Canada',
        '509': 'Concentra Bank',
        '540': 'Mogo Money Inc.',
        '614': 'Tandia Financial Credit Union',
        '815': 'Banque Bridgewater',
        '828': 'Banque CentreVue',
        '837': 'Paymi',
        '865': 'Koova Credit Union Limited',
        '889': 'Banque Alterna',
        '899': 'Wealth One Bank of Canada'
    }
    
    def __init__(self):
        self.transit_length = config.micr.transit_length
        self.institution_length = config.micr.institution_length
        self.min_account_length = config.micr.min_account_length
        self.max_account_length = config.micr.max_account_length
        self.min_cheque_length = config.micr.min_cheque_length
        self.max_cheque_length = config.micr.max_cheque_length
    
    def validate_canadian_micr(self, result: MICRResult) -> ValidationResult:
        """
        Valide un résultat MICR selon les standards canadiens
        
        Args:
            result: Résultat de l'analyse MICR
            
        Returns:
            Résultat de validation détaillé
        """
        errors = []
        warnings = []
        
        if not result.success:
            errors.append("L'analyse MICR a échoué")
            return ValidationResult(
                is_valid=False,
                transit_valid=False,
                institution_valid=False,
                account_valid=False,
                format_valid=False,
                errors=errors,
                warnings=warnings
            )
        
        # Validation du numéro de transit
        transit_valid = self._validate_transit(result.transit_number, errors, warnings)
        
        # Validation du numéro d'institution
        institution_valid = self._validate_institution(result.institution_number, errors, warnings)
        
        # Validation du numéro de compte
        account_valid = self._validate_account(result.account_number, errors, warnings)
        
        # Validation du numéro de chèque
        cheque_valid = self._validate_cheque_number_strict(result.cheque_number, errors, warnings)
        
        # Validation du format général
        format_valid = self._validate_overall_format(result, errors, warnings)
        
        # Validations supplémentaires
        self._validate_consistency(result, warnings)
        
        # Validation globale
        is_valid = transit_valid and institution_valid and account_valid and cheque_valid and format_valid
        
        return ValidationResult(
            is_valid=is_valid,
            transit_valid=transit_valid,
            institution_valid=institution_valid,
            account_valid=account_valid,
            format_valid=format_valid,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_transit(self, transit_component, errors: List[str], warnings: List[str]) -> bool:
        """Valide le numéro de transit (5 chiffres)"""
        if not transit_component or not transit_component.value:
            errors.append("Numéro de transit manquant")
            return False
        
        transit = transit_component.value.strip()
        
        # Vérifier la longueur
        if len(transit) != self.transit_length:
            errors.append(f"Numéro de transit doit avoir {self.transit_length} chiffres, trouvé: {len(transit)}")
            return False
        
        # Vérifier que ce sont tous des chiffres
        if not transit.isdigit():
            errors.append(f"Numéro de transit doit contenir seulement des chiffres: {transit}")
            return False
        
        # Vérifications de plausibilité
        if transit.startswith('000'):
            warnings.append("Numéro de transit commence par 000, peu probable")
        
        if transit == '00000':
            errors.append("Numéro de transit invalide: 00000")
            return False
        
        # Avertissement pour confiance faible
        if transit_component.combined_confidence < 0.7:
            warnings.append(f"Confiance faible pour le transit: {transit_component.combined_confidence:.1%}")
        
        return True
    
    def _validate_cheque_number_strict(self, cheque_component, errors: List[str], warnings: List[str]) -> bool:
        """Valide le numéro de chèque selon la spécification (1-10 chiffres)"""
        if not cheque_component or not cheque_component.value:
            errors.append("Numéro de chèque manquant")
            return False
        
        cheque_num = cheque_component.value.strip()
        
        # Vérifier que ce sont tous des chiffres
        if not cheque_num.isdigit():
            errors.append(f"Numéro de chèque doit contenir seulement des chiffres: {cheque_num}")
            return False
        
        # Vérifier la longueur selon spécification
        if len(cheque_num) < self.min_cheque_length:
            errors.append(f"Numéro de chèque trop court: {len(cheque_num)} caractères (minimum {self.min_cheque_length})")
            return False
        
        if len(cheque_num) > self.max_cheque_length:
            errors.append(f"Numéro de chèque trop long: {len(cheque_num)} caractères (maximum {self.max_cheque_length})")
            return False
        
        # Vérifications de plausibilité
        if cheque_num == '0' * len(cheque_num):
            errors.append("Numéro de chèque invalide: que des zéros")
            return False
        
        # Avertissement pour confiance faible
        if cheque_component.combined_confidence < 0.7:
            warnings.append(f"Confiance faible pour le chèque: {cheque_component.combined_confidence:.1%}")
        
        return True
    
    def _validate_institution(self, institution_component, errors: List[str], warnings: List[str]) -> bool:
        """Valide le numéro d'institution (3 chiffres)"""
        if not institution_component or not institution_component.value:
            errors.append("Numéro d'institution manquant")
            return False
        
        institution = institution_component.value.strip()
        
        # Vérifier la longueur
        if len(institution) != self.institution_length:
            errors.append(f"Numéro d'institution doit avoir {self.institution_length} chiffres, trouvé: {len(institution)}")
            return False
        
        # Vérifier que ce sont tous des chiffres
        if not institution.isdigit():
            errors.append(f"Numéro d'institution doit contenir seulement des chiffres: {institution}")
            return False
        
        # Vérifier si c'est une institution canadienne connue
        if institution in self.CANADIAN_INSTITUTIONS:
            # Succès - institution reconnue
            bank_name = self.CANADIAN_INSTITUTIONS[institution]
            warnings.append(f"Institution reconnue: {bank_name} ({institution})")
        else:
            warnings.append(f"Institution inconnue: {institution} (peut être une caisse locale)")
        
        # Vérifications de plausibilité
        if institution == '000':
            errors.append("Numéro d'institution invalide: 000")
            return False
        
        # Avertissement pour confiance faible
        if institution_component.combined_confidence < 0.7:
            warnings.append(f"Confiance faible pour l'institution: {institution_component.combined_confidence:.1%}")
        
        return True
    
    def _validate_account(self, account_component, errors: List[str], warnings: List[str]) -> bool:
        """Valide le numéro de compte"""
        if not account_component or not account_component.value:
            errors.append("Numéro de compte manquant")
            return False
        
        account = account_component.value.strip()
        
        # Vérifier la longueur
        if len(account) < self.min_account_length:
            errors.append(f"Numéro de compte trop court: {len(account)} caractères (minimum {self.min_account_length})")
            return False
        
        if len(account) > self.max_account_length:
            errors.append(f"Numéro de compte trop long: {len(account)} caractères (maximum {self.max_account_length})")
            return False
        
        # Vérifier que ce sont tous des chiffres
        if not account.isdigit():
            errors.append(f"Numéro de compte doit contenir seulement des chiffres: {account}")
            return False
        
        # Vérifications de plausibilité
        if account == '0' * len(account):
            errors.append("Numéro de compte invalide: que des zéros")
            return False
        
        # Avertissement pour confiance faible
        if account_component.combined_confidence < 0.7:
            warnings.append(f"Confiance faible pour le compte: {account_component.combined_confidence:.1%}")
        
        return True
    
    def _validate_overall_format(self, result: MICRResult, errors: List[str], warnings: List[str]) -> bool:
        """Valide le format général du code MICR"""
        if not result.raw_line:
            warnings.append("Ligne MICR brute non disponible")
            return True  # Pas d'erreur si on ne peut pas valider
        
        # Vérifier la présence de caractères MICR typiques
        micr_chars = ['⑆', '⑈', 'c', 'd', 'a', 'b']  # Caractères de contrôle MICR
        has_micr_chars = any(char in result.raw_line for char in micr_chars)
        
        if not has_micr_chars:
            warnings.append("Aucun caractère de contrôle MICR détecté dans la ligne brute")
        
        # Vérifier la longueur raisonnable
        if len(result.raw_line) < 10:
            warnings.append("Ligne MICR très courte, possiblement incomplète")
        elif len(result.raw_line) > 100:
            warnings.append("Ligne MICR très longue, possiblement avec du bruit")
        
        return True
    
    def _validate_cheque_number(self, cheque_component, warnings: List[str]):
        """Valide le numéro de chèque (version légère pour warnings seulement)"""
        # Cette fonction est maintenant redondante avec _validate_cheque_number_strict
        # Gardée pour compatibilité mais ne fait que des warnings
        pass
    
    def _validate_consistency(self, result: MICRResult, warnings: List[str]):
        """Valide la cohérence entre les composants"""
        # Vérifier les confiances relatives
        components = [
            ('transit', result.transit_number),
            ('institution', result.institution_number),
            ('account', result.account_number)
        ]
        
        confidences = []
        for name, comp in components:
            if comp and comp.combined_confidence:
                confidences.append((name, comp.combined_confidence))
        
        if len(confidences) >= 2:
            # Détecter des écarts importants de confiance
            conf_values = [conf for _, conf in confidences]
            max_conf = max(conf_values)
            min_conf = min(conf_values)
            
            if max_conf - min_conf > 0.4:  # Écart de plus de 40%
                warnings.append(f"Écart important de confiance entre composants: {min_conf:.1%} à {max_conf:.1%}")
        
        # Vérifier la cohérence de la ligne brute
        if result.raw_line:
            detected_values = []
            for name, comp in components:
                if comp and comp.value:
                    detected_values.append(comp.value)
            
            # Vérifier que les valeurs détectées apparaissent dans la ligne brute
            for value in detected_values:
                if value not in result.raw_line:
                    warnings.append(f"Valeur '{value}' non trouvée dans la ligne MICR brute")
    
    def get_institution_name(self, institution_number: str) -> str:
        """
        Retourne le nom de l'institution bancaire
        
        Args:
            institution_number: Numéro d'institution (3 chiffres)
            
        Returns:
            Nom de la banque ou "Institution inconnue"
        """
        return self.CANADIAN_INSTITUTIONS.get(institution_number, "Institution inconnue")
    
    def is_known_institution(self, institution_number: str) -> bool:
        """Vérifie si l'institution est connue"""
        return institution_number in self.CANADIAN_INSTITUTIONS
    
    def get_all_institutions(self) -> Dict[str, str]:
        """Retourne toutes les institutions connues"""
        return self.CANADIAN_INSTITUTIONS.copy()
