# core/micr_analyzer.py
"""
Analyseur principal MICR utilisant OpenAI GPT-4o
"""

import math
import json
import time
from typing import Optional
from openai import OpenAI

from models.micr_models import MICRResult, MICRComponent, ComponentType
from core.confidence_calculator import ConfidenceCalculator
from core.validator import MICRValidator
from utils.image_utils import ImageProcessor
from config import config
from prompts import get_micr_prompt

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
                            "text": get_micr_prompt(config.micr.region)
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



    def _parse_response(self, response, image_path: str, start_time: float) -> MICRResult:
        """Parse la réponse de l'API OpenAI"""
        try:
            # Extraire la réponse et les logprobs
            response_text = response.choices[0].message.content.strip()
            logprobs_data = response.choices[0].logprobs
            
            # DEBUG: Afficher la réponse brute de GPT-4o
            print(f"\n📋 RÉPONSE BRUTE GPT-4o:")
            print(f"🔤 Texte brut: {response_text[:200]}...")  # Premiers 200 caractères
            
            # Nettoyer la réponse JSON
            response_text = self._clean_json_response(response_text)
            result_data = json.loads(response_text)
            
            # DEBUG: Afficher le JSON parsé
            print(f"\n📊 JSON PARSÉ:")
            print(f"🎯 raw_confidence GPT: {result_data.get('raw_confidence', 'ABSENT')}")
            
            # NOUVELLE FONCTIONNALITÉ: Recalculer raw_confidence avec logprobs
            recalculated_confidence = self._recalculate_confidence_from_logprobs(
                result_data.get('raw_confidence'), logprobs_data
            )
            
            if recalculated_confidence != result_data.get('raw_confidence'):
                print(f"🔄 Confiance recalculée: {recalculated_confidence:.3f} (était: {result_data.get('raw_confidence'):.3f})")
                result_data['raw_confidence'] = recalculated_confidence
            print(f"✅ success: {result_data.get('success', 'ABSENT')}")
            print(f"🏦 transit_number: {result_data.get('transit_number', 'ABSENT')}")
            print(f"🏢 institution_number: {result_data.get('institution_number', 'ABSENT')}")
            print(f"📄 JSON complet: {json.dumps(result_data, indent=2)}")
            
            # Créer les composants avec confiance améliorée - NOUVEAU FORMAT
            if not result_data.get("success", False):
                return MICRResult(
                    raw_line="",
                    raw_confidence=0.0,
                    success=False,
                    error_message=result_data.get("error_message", "Analyse échouée"),
                    processing_time=time.time() - start_time,
                    image_path=image_path
                )
            
            # Créer les composants basiques d'abord
            basic_components = {
                "transit_number": self._create_basic_component_new_format(
                    result_data.get("transit_number", ""), ComponentType.TRANSIT, logprobs_data, result_data
                ),
                "institution_number": self._create_basic_component_new_format(
                    result_data.get("institution_number", ""), ComponentType.INSTITUTION, logprobs_data, result_data
                ),
                "account_number": self._create_basic_component_new_format(
                    result_data.get("account_number", ""), ComponentType.ACCOUNT, logprobs_data, result_data
                ),
                "cheque_number": self._create_basic_component_new_format(
                    result_data.get("cheque_number", ""), ComponentType.CHEQUE, logprobs_data, result_data
                ),
                "amount": self._create_basic_component_new_format(
                    result_data.get("amount", ""), ComponentType.AMOUNT, logprobs_data, result_data
                ),
                "auxiliary_on_us": self._create_basic_component_new_format(
                    result_data.get("auxiliary_on_us", ""), ComponentType.AUXILIARY, logprobs_data, result_data
                )
            }
            
            # Créer un résultat temporaire pour validation
            temp_result = MICRResult(
                raw_line=result_data.get("raw_line", ""),
                raw_confidence=result_data.get("raw_confidence", 0.0),
                success=True,
                processing_time=time.time() - start_time,
                image_path=image_path,
                **basic_components
            )
            
            # Valider et ajuster les confiances
            validations = self.validator.validate_canadian_micr(temp_result)
            
            # Mettre à jour les validation_passed des composants
            if basic_components["transit_number"]:
                basic_components["transit_number"].validation_passed = validations.transit_valid
            if basic_components["institution_number"]:
                basic_components["institution_number"].validation_passed = validations.institution_valid
            if basic_components["account_number"]:
                basic_components["account_number"].validation_passed = validations.account_valid
            
            # Recalculer les confiances avec validation
            for comp_name, component in basic_components.items():
                if component:
                    component.combined_confidence = self.confidence_calculator.combine_confidences(
                        component.llm_confidence,
                        component.logprob_confidence,
                        component.validation_passed
                    )
            
            # Construire le résultat final
            return MICRResult(
                raw_line=result_data.get("raw_line", ""),
                raw_confidence=result_data.get("raw_confidence", 0.0),
                success=True,
                error_message=None,
                processing_time=time.time() - start_time,
                image_path=image_path,
                **basic_components
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
    
    def _recalculate_confidence_from_logprobs(self, original_confidence: float, logprobs_data) -> float:
        """
        Recalcule raw_confidence en utilisant les logprobs du token de confiance
        Utilise les mêmes techniques que calculate_logprob_confidence
        """
        if not logprobs_data or not original_confidence:
            return original_confidence or 0.5
        
        try:
            # Utiliser le calculateur existant pour chercher la valeur de confiance
            confidence_str = f"{original_confidence:.2f}"  # "0.95", "0.73", etc.
            
            print(f"🔍 Recherche confiance '{confidence_str}' avec techniques avancées...")
            
            # Réutiliser la logique éprouvée de calculate_logprob_confidence
            logprob_confidence = self.confidence_calculator.calculate_logprob_confidence(
                logprobs_data, confidence_str
            )
            
            if logprob_confidence > 0.0:
                print(f"✅ Confiance logprobs trouvée: {logprob_confidence:.3f}")
                
                # Moyenne pondérée entre confiance GPT et confiance logprob
                final_confidence = (original_confidence * 0.7) + (logprob_confidence * 0.3)
                print(f"📊 Combinaison: GPT({original_confidence:.3f}) * 0.7 + logprobs({logprob_confidence:.3f}) * 0.3 = {final_confidence:.3f}")
                return min(final_confidence, 1.0)
            else:
                print("⚠️ Confiance non détectée dans logprobs - utilisation GPT originale")
                return original_confidence
            
        except Exception as e:
            print(f"❌ Erreur recalcul confiance: {e}")
            return original_confidence or 0.5
    
    def _create_basic_component_new_format(self, value: str, comp_type: ComponentType, logprobs_data, result_data: dict) -> Optional[MICRComponent]:
        """Crée un composant MICR avec le nouveau format de réponse"""
        if not value or not value.strip():
            return None
        
        value = value.strip()
        
        # Utiliser raw_confidence du LLM au lieu d'une valeur fixe
        llm_confidence = result_data.get("raw_confidence", 0.5)  # Utilise la confiance globale du LLM
        print(f"🤖 Confiance LLM pour {comp_type.value}: {llm_confidence:.3f} (depuis raw_confidence)")
        
        # Calculer la confiance logprobs
        logprob_confidence = 0.0
        if logprobs_data:
            try:
                print(f"🔍 Debug logprobs pour {comp_type.value} = '{value}':")
                print(f"  Type logprobs_data: {type(logprobs_data)}")
                
                # Afficher les attributs disponibles pour debug
                if hasattr(logprobs_data, '__dict__'):
                    print(f"  Attributs logprobs_data: {list(logprobs_data.__dict__.keys())}")
                elif hasattr(logprobs_data, '__dir__'):
                    attrs = [attr for attr in dir(logprobs_data) if not attr.startswith('_')]
                    print(f"  Attributs publics: {attrs}")
                
                # Passer directement l'objet logprobs à calculate_logprob_confidence
                logprob_confidence = self.confidence_calculator.calculate_logprob_confidence(
                    logprobs_data, value
                )
                print(f"  Résultat confiance logprobs: {logprob_confidence:.3f}")
            except Exception as e:
                print(f"❌ Erreur calcul logprobs pour {comp_type.value}: {e}")
                print(f"  Type d'erreur: {type(e).__name__}")
                import traceback
                print(f"  Traceback: {traceback.format_exc()}")
                # En cas d'erreur, utiliser une heuristique basée sur la longueur et le contenu
                if value.isdigit() and len(value) > 0:
                    logprob_confidence = 0.7  # Confiance par défaut pour chiffres valides
                else:
                    logprob_confidence = 0.3
                print(f"  Utilisation fallback: {logprob_confidence:.3f}")
        else:
            print(f"⚠️  Pas de données logprobs pour {comp_type.value}")
        
        # Confiance combinée initiale (sera recalculée après validation)
        combined_confidence = self.confidence_calculator.combine_confidences(
            llm_confidence, logprob_confidence, True  # Assume validation OK initialement
        )
        
        return MICRComponent(
            value=value,
            description=self._get_component_description(comp_type),
            llm_confidence=llm_confidence,
            logprob_confidence=logprob_confidence,
            combined_confidence=combined_confidence,
            component_type=comp_type,
            validation_passed=True  # Sera mis à jour après validation
        )
    
    def _get_component_description(self, comp_type: ComponentType) -> str:
        """Retourne la description d'un type de composant"""
        descriptions = {
            ComponentType.TRANSIT: "Numéro de transit/succursale",
            ComponentType.INSTITUTION: "Numéro d'institution bancaire",
            ComponentType.ACCOUNT: "Numéro de compte",
            ComponentType.CHEQUE: "Numéro du chèque",
            ComponentType.AMOUNT: "Montant encodé",
            ComponentType.AUXILIARY: "Données auxiliaires"
        }
        return descriptions.get(comp_type, "Composant MICR")
    
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
    
    def _create_final_components(self, components_data: dict, logprobs_data, validations) -> dict:
        """Crée les composants finaux avec confiance améliorée"""
        component_mapping = {
            "transit_number": (ComponentType.TRANSIT, validations.transit_valid),
            "institution_number": (ComponentType.INSTITUTION, validations.institution_valid),
            "account_number": (ComponentType.ACCOUNT, validations.account_valid),
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
