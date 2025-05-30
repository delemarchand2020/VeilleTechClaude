# interface/gradio_interface.py
"""
Interface Gradio pour les démonstrations business du MICR Reader
"""

import gradio as gr
import pandas as pd
import json
import os
import time
from typing import Tuple, Dict, Any
from PIL import Image
import base64
from io import BytesIO

# Imports du projet
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.micr_analyzer import MICRAnalyzer
from core.validator import MICRValidator
from utils.image_utils import ImageProcessor
from models.micr_models import MICRResult
from config import config

class MICRGradioInterface:
    """Interface Gradio pour les démonstrations MICR Reader"""
    
    def __init__(self, api_key: str = None, share: bool = False, server_name: str = "127.0.0.1", server_port: int = 7860):
        """
        Initialise l'interface Gradio
        
        Args:
            api_key: Clé API OpenAI
            share: Partager publiquement (Gradio share)
            server_name: Adresse du serveur
            server_port: Port du serveur
        """
        self.api_key = api_key or config.openai.api_key
        self.share = share
        self.server_name = server_name
        self.server_port = server_port
        
        # Initialiser les composants
        self.analyzer = MICRAnalyzer(self.api_key)
        self.validator = MICRValidator()
        self.image_processor = ImageProcessor()
        
        # Créer l'interface
        self.interface = self._create_interface()
    
    def _create_interface(self) -> gr.Blocks:
        """Crée l'interface Gradio"""
        
        # CSS personnalisé pour un look professionnel
        custom_css = """
        .gradio-container {
            max-width: 1200px !important;
            margin: auto;
        }
        .header {
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        .metric-card {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 1rem;
            margin: 0.5rem;
            text-align: center;
        }
        .success {
            border-left: 4px solid #28a745;
        }
        .warning {
            border-left: 4px solid #ffc107;
        }
        .error {
            border-left: 4px solid #dc3545;
        }
        .confidence-high {
            color: #28a745;
            font-weight: bold;
        }
        .confidence-medium {
            color: #ffc107;
            font-weight: bold;
        }
        .confidence-low {
            color: #dc3545;
            font-weight: bold;
        }
        """
        
        with gr.Blocks(css=custom_css, title="MICR Reader - Démo Business", theme=gr.themes.Soft()) as interface:
            
            # En-tête
            gr.HTML("""
                <div class="header">
                    <h1>🏦 MICR Reader - Démonstration Business</h1>
                    <p>Analyse automatique des codes MICR sur chèques canadiens avec IA avancée</p>
                    <p><strong>Powered by OpenAI GPT-4o • Système de confiance tri-modal</strong></p>
                </div>
            """)
            
            with gr.Row():
                with gr.Column(scale=1):
                    # Zone de téléchargement d'image
                    gr.Markdown("## 📤 Télécharger un chèque")
                    image_input = gr.Image(
                        label="Image du chèque canadien",
                        type="filepath",
                        height=400
                    )
                    
                    # Boutons d'action
                    with gr.Row():
                        analyze_btn = gr.Button("🔍 Analyser le MICR", variant="primary", size="lg")
                        clear_btn = gr.Button("🗑️ Effacer", variant="secondary")
                    
                    # Informations sur l'image
                    gr.Markdown("## 📋 Informations de l'image")
                    image_info = gr.JSON(label="Métadonnées de l'image", visible=False)
                
                with gr.Column(scale=2):
                    # Résultats de l'analyse
                    gr.Markdown("## 📊 Résultats de l'analyse")
                    
                    # Statut global
                    status_html = gr.HTML()
                    
                    # Ligne MICR brute
                    with gr.Row():
                        raw_micr = gr.Textbox(
                            label="📝 Ligne MICR détectée",
                            interactive=False,
                            placeholder="La ligne MICR apparaîtra ici..."
                        )
                    
                    # Composants MICR
                    gr.Markdown("### 🔍 Composants MICR détectés")
                    
                    with gr.Row():
                        transit_output = gr.Textbox(label="🏦 Numéro de transit", interactive=False)
                        institution_output = gr.Textbox(label="🏢 Institution", interactive=False)
                    
                    with gr.Row():
                        account_output = gr.Textbox(label="👤 Numéro de compte", interactive=False)
                        cheque_output = gr.Textbox(label="📄 Numéro de chèque", interactive=False)
                    
                    # Informations bancaires
                    bank_info = gr.Textbox(label="🏛️ Banque identifiée", interactive=False)
                    
                    # Métriques de confiance
                    gr.Markdown("### 🎯 Analyse de confiance")
                    confidence_html = gr.HTML()
                    
                    # Tableaux détaillés
                    with gr.Tabs():
                        with gr.TabItem("📈 Confiances détaillées"):
                            confidence_table = gr.DataFrame(
                                headers=["Composant", "Valeur", "Confiance finale", "Confiance LLM", "Confiance Logprobs", "Validation"],
                                datatype=["str", "str", "str", "str", "str", "str"],
                                label="Analyse détaillée des confiances"
                            )
                        
                        with gr.TabItem("✅ Validation"):
                            validation_table = gr.DataFrame(
                                headers=["Critère", "Statut", "Détails"],
                                datatype=["str", "str", "str"],
                                label="Résultats de validation"
                            )
                        
                        with gr.TabItem("🔧 Données techniques"):
                            technical_info = gr.JSON(label="Données techniques complètes")
            
            # Zone d'exemples
            gr.Markdown("## 💡 Exemples de correspondance logprobs")
            examples_html = gr.HTML(self._create_examples_html())
            
            # Footer avec informations
            gr.HTML("""
                <div style="text-align: center; margin-top: 2rem; padding: 1rem; background: #f8f9fa; border-radius: 8px;">
                    <p><strong>MICR Reader v1.0</strong> - Système de confiance tri-modal innovant</p>
                    <p>🤖 30% Confiance LLM • 📈 60% Confiance Logprobs • ✅ 10% Validation Format</p>
                </div>
            """)
            
            # Event handlers
            analyze_btn.click(
                fn=self._analyze_image,
                inputs=[image_input],
                outputs=[
                    status_html, raw_micr, transit_output, institution_output,
                    account_output, cheque_output, bank_info, confidence_html,
                    confidence_table, validation_table, technical_info, image_info
                ]
            )
            
            clear_btn.click(
                fn=lambda: self._clear_all(),
                outputs=[
                    image_input, status_html, raw_micr, transit_output, institution_output,
                    account_output, cheque_output, bank_info, confidence_html,
                    confidence_table, validation_table, technical_info, image_info
                ]
            )
            
            image_input.change(
                fn=self._get_image_info,
                inputs=[image_input],
                outputs=[image_info]
            )
        
        return interface
    
    def _analyze_image(self, image_path: str) -> Tuple:
        """
        Analyse une image de chèque
        
        Args:
            image_path: Chemin vers l'image
            
        Returns:
            Tuple avec tous les résultats pour l'interface
        """
        if not image_path:
            return self._empty_results("❌ Aucune image sélectionnée")
        
        try:
            # Analyser l'image
            result = self.analyzer.analyze_micr(image_path)
            validations = self.validator.validate_canadian_micr(result)
            
            # Générer tous les éléments de sortie
            status_html = self._create_status_html(result, validations)
            raw_micr = result.raw_line if result.success else ""
            
            # Extraire les composants
            transit = result.transit_number.value if result.transit_number else ""
            institution = result.institution_number.value if result.institution_number else ""
            account = result.account_number.value if result.account_number else ""
            cheque = result.cheque_number.value if result.cheque_number else ""
            
            # Informations bancaires
            bank_info = ""
            if result.institution_number and result.institution_number.value:
                bank_name = self.validator.get_institution_name(result.institution_number.value)
                bank_info = f"{bank_name} ({result.institution_number.value})"
            
            # HTML de confiance
            confidence_html = self._create_confidence_html(result)
            
            # Tableaux
            confidence_table = self._create_confidence_table(result)
            validation_table = self._create_validation_table(validations)
            
            # Données techniques
            technical_info = {
                "resultat_complet": result.to_dict(),
                "validation": validations.to_dict(),
                "temps_traitement": f"{result.processing_time:.2f}s" if result.processing_time else "N/A",
                "confiance_globale": f"{result.get_overall_confidence():.1%}" if result.success else "0%"
            }
            
            # Info image
            image_info = self.image_processor.get_image_info(image_path)
            
            return (
                status_html, raw_micr, transit, institution, account, cheque,
                bank_info, confidence_html, confidence_table, validation_table,
                technical_info, image_info
            )
            
        except Exception as e:
            return self._empty_results(f"❌ Erreur lors de l'analyse: {str(e)}")
    
    def _create_status_html(self, result: MICRResult, validations) -> str:
        """Crée le HTML du statut global"""
        if not result.success:
            return f"""
            <div class="metric-card error">
                <h3>❌ Analyse échouée</h3>
                <p>{result.error_message}</p>
            </div>
            """
        
        confidence = result.get_overall_confidence()
        confidence_class = "confidence-high" if confidence >= 0.8 else "confidence-medium" if confidence >= 0.6 else "confidence-low"
        status_class = "success" if validations.is_valid else "warning"
        
        return f"""
        <div class="metric-card {status_class}">
            <h3>✅ Analyse réussie</h3>
            <p><strong>Confiance globale:</strong> <span class="{confidence_class}">{confidence:.1%}</span></p>
            <p><strong>Format valide:</strong> {'✅ Oui' if validations.is_valid else '⚠️ Problèmes détectés'}</p>
            <p><strong>Temps de traitement:</strong> {result.processing_time:.2f}s</p>
        </div>
        """
    
    def _create_confidence_html(self, result: MICRResult) -> str:
        """Crée le HTML d'analyse de confiance"""
        if not result.success:
            return "<p>Aucune donnée de confiance disponible</p>"
        
        components = [
            ("Transit", result.transit_number),
            ("Institution", result.institution_number),
            ("Compte", result.account_number),
            ("Chèque", result.cheque_number)
        ]
        
        html = "<div style='display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;'>"
        
        for name, component in components:
            if component:
                conf_class = "confidence-high" if component.combined_confidence >= 0.8 else "confidence-medium" if component.combined_confidence >= 0.6 else "confidence-low"
                html += f"""
                <div class="metric-card">
                    <h4>{name}</h4>
                    <p><strong>Finale:</strong> <span class="{conf_class}">{component.combined_confidence:.1%}</span></p>
                    <p>LLM: {component.llm_confidence:.1%} | Logprobs: {component.logprob_confidence:.1%}</p>
                </div>
                """
        
        html += "</div>"
        return html
    
    def _create_confidence_table(self, result: MICRResult) -> pd.DataFrame:
        """Crée le tableau des confiances"""
        if not result.success:
            return pd.DataFrame()
        
        data = []
        components = [
            ("🏦 Transit", result.transit_number),
            ("🏢 Institution", result.institution_number),
            ("👤 Compte", result.account_number),
            ("📄 Chèque", result.cheque_number),
            ("💰 Montant", result.amount)
        ]
        
        for name, component in components:
            if component:
                data.append([
                    name,
                    component.value,
                    f"{component.combined_confidence:.1%}",
                    f"{component.llm_confidence:.1%}",
                    f"{component.logprob_confidence:.1%}",
                    "✅ Valide" if component.validation_passed else "❌ Invalid"
                ])
        
        return pd.DataFrame(data, columns=["Composant", "Valeur", "Confiance finale", "Confiance LLM", "Confiance Logprobs", "Validation"])
    
    def _create_validation_table(self, validations) -> pd.DataFrame:
        """Crée le tableau de validation"""
        data = [
            ["🏦 Transit", "✅ Valide" if validations.transit_valid else "❌ Invalide", "Format 5 chiffres"],
            ["🏢 Institution", "✅ Valide" if validations.institution_valid else "❌ Invalide", "Format 3 chiffres + base de données"],
            ["👤 Compte", "✅ Valide" if validations.account_valid else "❌ Invalide", "3-20 chiffres"],
            ["📋 Format global", "✅ Valide" if validations.format_valid else "❌ Invalide", "Standards MICR canadiens"]
        ]
        
        return pd.DataFrame(data, columns=["Critère", "Statut", "Détails"])
    
    def _create_examples_html(self) -> str:
        """Crée le HTML des exemples de logprobs"""
        return """
        <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
            <h4>📚 Exemples de correspondance logprobs</h4>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-top: 1rem;">
                <div class="metric-card">
                    <h5>🎯 Correspondance exacte</h5>
                    <p><code>Tokens: ['{"transit": "', '12345', '"]</code></p>
                    <p><code>Target: "12345"</code></p>
                    <p><strong>Confiance:</strong> <span class="confidence-high">exp(-0.2) ≈ 81.9%</span></p>
                </div>
                <div class="metric-card">
                    <h5>🔗 Reconstruction</h5>
                    <p><code>Tokens: ['"account": "', '987', '654', '321']</code></p>
                    <p><code>Target: "987654321"</code></p>
                    <p><strong>Confiance:</strong> <span class="confidence-medium">Moy. géométrique ≈ 72.9%</span></p>
                </div>
                <div class="metric-card">
                    <h5>🔍 Approximative</h5>
                    <p><code>Tokens: ['I see', '1', '2', '3', '4', '5']</code></p>
                    <p><code>Target: "12345"</code></p>
                    <p><strong>Confiance:</strong> <span class="confidence-low">Moy. pondérée ≈ 61.3%</span></p>
                </div>
            </div>
        </div>
        """
    
    def _get_image_info(self, image_path: str) -> Dict:
        """Obtient les informations de l'image"""
        if not image_path:
            return {}
        
        try:
            info = self.image_processor.get_image_info(image_path)
            return info
        except Exception as e:
            return {"error": str(e)}
    
    def _clear_all(self):
        """Efface tous les champs"""
        return (
            None,  # image
            "",    # status_html
            "",    # raw_micr
            "",    # transit
            "",    # institution
            "",    # account
            "",    # cheque
            "",    # bank_info
            "",    # confidence_html
            pd.DataFrame(),  # confidence_table
            pd.DataFrame(),  # validation_table
            {},    # technical_info
            {}     # image_info
        )
    
    def _empty_results(self, error_message: str):
        """Retourne des résultats vides avec un message d'erreur"""
        error_html = f"""
        <div class="metric-card error">
            <h3>{error_message}</h3>
        </div>
        """
        
        return (
            error_html,      # status_html
            "",              # raw_micr
            "",              # transit
            "",              # institution
            "",              # account
            "",              # cheque
            "",              # bank_info
            "",              # confidence_html
            pd.DataFrame(),  # confidence_table
            pd.DataFrame(),  # validation_table
            {},              # technical_info
            {}               # image_info
        )
    
    def launch(self, **kwargs):
        """Lance l'interface Gradio"""
        
        # Vérifier la configuration
        try:
            config.validate()
        except ValueError as e:
            print(f"❌ Erreur de configuration: {e}")
            print("💡 Assurez-vous d'avoir configuré votre clé API OpenAI")
            return
        
        print("🚀 Lancement de l'interface MICR Reader...")
        print(f"🌐 Serveur: http://{self.server_name}:{self.server_port}")
        
        # Paramètres par défaut
        launch_params = {
            'share': self.share,
            'server_name': self.server_name,
            'server_port': self.server_port,
            'show_api': False,
            'quiet': False
        }
        
        # Merger avec les paramètres utilisateur
        launch_params.update(kwargs)
        
        return self.interface.launch(**launch_params)

def create_demo_interface(api_key: str = None, **kwargs) -> MICRGradioInterface:
    """
    Fonction utilitaire pour créer rapidement une interface de démo
    
    Args:
        api_key: Clé API OpenAI
        **kwargs: Paramètres pour le lancement
        
    Returns:
        Instance de MICRGradioInterface
    """
    interface = MICRGradioInterface(api_key=api_key)
    return interface

if __name__ == "__main__":
    # Lancement direct pour test
    interface = create_demo_interface()
    interface.launch()
