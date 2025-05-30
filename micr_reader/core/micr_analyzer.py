# core/micr_analyzer.py
"""
Analyseur principal MICR utilisant OpenAI GPT-4o
"""

import json
import time
from typing import Optional
from openai import OpenAI

from models.micr_models import MICRResult, MICRComponent, ComponentType
from core.confidence_calculator import ConfidenceCalculator
from core.validator import MICRValidator
from utils.image_utils import ImageProcessor
from config import config

class MICRAnalyzer:
    """
    Analyseur principal pour les codes MICR canadiens
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise l'analyseur MICR
        
        Args:
            api_key: Clé API OpenAI (utilise config si None)
        """
        self.api_key = api_key or config.openai.api_key
        self.client = OpenAI(api_key=self.api_key)
        self.confidence_calculator = ConfidenceCalculator()
        self.validator = MICRValidator()
        self.image_processor = ImageProcessor()
    
    def analyze_micr(self, image_path: str) -> MICRResult:
        """
        Analyse le code MICR d'un chèque canadien
        
        Args:
            image_path: Chemin vers l'image du chèque
            
        Returns:
            Résultat de l'analyse MICR
        """
        start_time = time.time()
        
        try:
            # Vérifier l'image
            if not self.image_processor.validate_image(image_path):
                return MICRResult(
                    raw_line="",
                    raw_confidence=0.0,
                    success=False,
                    error_message="Image invalide ou non supportée",
                    processing_time=time.time() - start_time,
                    image_path=image_path
                )
            
            # Encoder l'image
            base64_image = self.image_processor.encode_image(image_path)
            
            # Analyser avec GPT-4o
            response = self._call_openai_api(base64_image)
            
            # Parser la réponse
            result = self._parse_response(response, image_path, start_time)
            
            return result
            
        except Exception as e:
            return MICRResult(
                raw_line="",
                raw_confidence=0.0,
                success=False,
                error_message=f"Erreur lors de l'analyse: {str(e)}",
                processing_time=time.time() - start_time,
                image_path=image_path
            )
    
    def _call_openai_api(self, base64_image: str):
        """Appel à l'API OpenAI GPT-4o"""
        return self.client.chat.completions.create(
            model=config.openai.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self._create_micr_prompt()
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": config.image.image_detail
                            }
                        }
                    ]
                }
            ],
            max_tokens=config.openai.max_tokens,
            temperature=config.openai.temperature,
            logprobs=config.openai.logprobs,
            top_logprobs=config.openai.top_logprobs
        )
    
    def _create_micr_prompt(self) -> str:
        """
        Crée le prompt spécialisé pour l'analyse MICR des chèques canadiens
        """
        return """
Analysez cette image de chèque canadien et extrayez les informations du code MICR (Magnetic Ink Character Recognition) situé au bas du chèque.

Le code MICR canadien suit généralement ce format:
⑆TRANSIT⑆INSTITUTION⑈ACCOUNT NUMBER⑈CHEQUE NUMBER⑆

Où:
- TRANSIT: 5 chiffres (numéro de transit/succursale)
- INSTITUTION: 3 chiffres (numéro d'institution bancaire)
- ACCOUNT NUMBER: numéro de compte (longueur variable)
- CHEQUE NUMBER: numéro du chèque
- Les symboles ⑆ et ⑈ sont des caractères de contrôle MICR

Fournissez votre réponse UNIQUEMENT en format JSON avec cette structure exacte:
{
    "raw_line": "ligne MICR complète telle que lue",
    "raw_confidence": 0.95,
    "components": {
        "transit_number": {
            "value": "12345",
            "confidence": 0.98,
            "description": "Numéro de transit/succursale"
        },
        "institution_number": {
            "value": "123",
            "confidence": 0.97,
            "description": "Numéro d'institution bancaire"
        },
        "account_number": {
            "value": "1234567890",
            "confidence": 0.95,
            "description": "Numéro de compte"
        },
        "cheque_number": {
            "value": "001",
            "confidence": 0.99,
            "description": "Numéro du chèque"
        },
        "amount": {
            "value": "0000012345",
            "confidence": 0.85,
            "description": "Montant encodé (si présent)"
        },
        "auxiliary_on_us": {
            "value": "",
            "confidence": 0.0,
            "description": "Données auxiliaires (si présentes)"
        }
    },
    "success": true,
    "error_message": null
}

Évaluez la confiance de 0.0 à 1.0 basée sur la clarté et la lisibilité de chaque élément.
Si un élément n'est pas visible ou présent, utilisez une valeur vide et confidence 0.0.
Si l'analyse échoue complètement, retournez success: false avec un message d'erreur.
"""
    
    def _parse_response(self, response, image_path: str, start_time: float) -> MICRResult:
        """Parse la réponse de l'API OpenAI"""
        try:
            # Extraire la réponse et les logprobs
            response_text = response.choices[0].message.content.strip()
            logprobs_data = response.choices[0].logprobs
            
            # Nettoyer la réponse JSON
            response_text = self._clean_json_response(response_text)
            result_data = json.loads(response_text)
            
            # Créer les composants avec confiance améliorée
            components_data = result_data.get("components", {})
            
            # Pré-validation pour ajuster les confiances
            temp_result = self._create_temp_result(result_data, image_path, start_time)
            validations = self.validator.validate_canadian_micr(temp_result)
            
            # Créer les composants finaux avec validations
            final_components = self._create_final_components(
                components_data, logprobs_data, validations
            )
            
            # Construire le résultat final
            return MICRResult(
                raw_line=result_data.get("raw_line", ""),
                raw_confidence=result_data.get("raw_confidence", 0.0),
                success=result_data.get("success", False),
                error_message=result_data.get("error_message"),
                processing_time=time.time() - start_time,
                image_path=image_path,
                **final_components
            )
            
        except json.JSONDecodeError as e:
            return MICRResult(
                raw_line="",
                raw_confidence=0.0,
                success=False,
                error_message=f"Erreur de parsing JSON: {str(e)}",
                processing_time=time.time() - start_time,
                image_path=image_path
            )
        except Exception as e:
            return MICRResult(
                raw_line="",
                raw_confidence=0.0,
                success=False,
                error_message=f"Erreur lors du parsing: {str(e)}",
                processing_time=time.time() - start_time,
                image_path=image_path
            )
    
    def _clean_json_response(self, response_text: str) -> str:
        """Nettoie la réponse pour extraire le JSON valide"""
        # Enlever les balises de code markdown
        if response_text.startswith("```json"):
            response_text = response_text[7:-3]
        elif response_text.startswith("```"):
            response_text = response_text[3:-3]
        
        return response_text.strip()
    
    def _create_temp_result(self, result_data: dict, image_path: str, start_time: float) -> MICRResult:
        """Crée un résultat temporaire pour la validation"""
        components = result_data.get("components", {})
        
        def create_basic_component(comp_data, comp_type):
            if comp_data and comp_data.get("value"):
                return MICRComponent(
                    value=comp_data["value"],
                    description=comp_data.get("description", ""),
                    llm_confidence=comp_data.get("confidence", 0.0),
                    logprob_confidence=0.0,  # Calculé plus tard
                    combined_confidence=comp_data.get("confidence", 0.0),
                    component_type=comp_type
                )
            return None
        
        return MICRResult(
            raw_line=result_data.get("raw_line", ""),
            raw_confidence=result_data.get("raw_confidence", 0.0),
            success=result_data.get("success", False),
            error_message=result_data.get("error_message"),
            processing_time=time.time() - start_time,
            image_path=image_path,
            transit_number=create_basic_component(components.get("transit_number"), ComponentType.TRANSIT),
            institution_number=create_basic_component(components.get("institution_number"), ComponentType.INSTITUTION),
            account_number=create_basic_component(components.get("account_number"), ComponentType.ACCOUNT),
            cheque_number=create_basic_component(components.get("cheque_number"), ComponentType.CHEQUE),
            amount=create_basic_component(components.get("amount"), ComponentType.AMOUNT),
            auxiliary_on_us=create_basic_component(components.get("auxiliary_on_us"), ComponentType.AUXILIARY)
        )
    
    def _create_final_components(self, components_data: dict, logprobs_data, validations: dict) -> dict:
        """Crée les composants finaux avec confiance améliorée"""
        component_mapping = {
            "transit_number": (ComponentType.TRANSIT, validations.get("transit_valid", True)),
            "institution_number": (ComponentType.INSTITUTION, validations.get("institution_valid", True)),
            "account_number": (ComponentType.ACCOUNT, validations.get("account_valid", True)),
            "cheque_number": (ComponentType.CHEQUE, True),
            "amount": (ComponentType.AMOUNT, True),
            "auxiliary_on_us": (ComponentType.AUXILIARY, True)
        }
        
        result_components = {}
        
        for comp_name, (comp_type, validation_passed) in component_mapping.items():
            comp_data = components_data.get(comp_name)
            if comp_data and comp_data.get("value"):
                component = self._create_enhanced_component(
                    comp_data, comp_type, logprobs_data, validation_passed
                )
                result_components[comp_name] = component
            else:
                result_components[comp_name] = None
        
        return result_components
    
    def _create_enhanced_component(self, comp_data: dict, comp_type: ComponentType, 
                                 logprobs_data, validation_passed: bool) -> MICRComponent:
        """Crée un composant avec confiance améliorée"""
        llm_confidence = comp_data.get("confidence", 0.0)
        
        # Calculer la confiance logprobs
        logprob_confidence = 0.0
        if logprobs_data:
            try:
                logprobs_dict = logprobs_data.dict() if hasattr(logprobs_data, 'dict') else logprobs_data
                logprob_confidence = self.confidence_calculator.calculate_logprob_confidence(
                    logprobs_dict, comp_data["value"]
                )
            except Exception as e:
                print(f"Erreur calcul logprobs pour {comp_type.value}: {e}")
        
        # Combiner les confiances
        combined_confidence = self.confidence_calculator.combine_confidences(
            llm_confidence, logprob_confidence, validation_passed
        )
        
        return MICRComponent(
            value=comp_data["value"],
            description=comp_data.get("description", ""),
            llm_confidence=llm_confidence,
            logprob_confidence=logprob_confidence,
            combined_confidence=combined_confidence,
            component_type=comp_type,
            validation_passed=validation_passed
        )
    
    def analyze_batch(self, image_paths: list) -> dict:
        """
        Analyse plusieurs images en lot
        
        Args:
            image_paths: Liste des chemins d'images
            
        Returns:
            Dictionnaire {chemin: résultat}
        """
        results = {}
        
        for image_path in image_paths:
            print(f"Analyse de {image_path}...")
            results[image_path] = self.analyze_micr(image_path)
        
        return results
    
    def get_confidence_breakdown(self, component: MICRComponent) -> dict:
        """Analyse détaillée de la confiance d'un composant"""
        return self.confidence_calculator.analyze_confidence_breakdown(
            component.llm_confidence,
            component.logprob_confidence,
            component.validation_passed
        )
