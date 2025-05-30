# launch_demo.py
"""
Script de lancement de l'interface de démonstration MICR Reader
"""

import os
import sys
import argparse
from interface.gradio_interface import MICRGradioInterface

def main():
    """Fonction principale de lancement"""
    
    parser = argparse.ArgumentParser(description="Lance l'interface de démonstration MICR Reader")
    parser.add_argument('--api-key', type=str, help="Clé API OpenAI")
    parser.add_argument('--share', action='store_true', help="Partager publiquement (Gradio share)")
    parser.add_argument('--host', type=str, default="127.0.0.1", help="Adresse du serveur (défaut: 127.0.0.1)")
    parser.add_argument('--port', type=int, default=7860, help="Port du serveur (défaut: 7860)")
    parser.add_argument('--debug', action='store_true', help="Mode debug")
    
    args = parser.parse_args()
    
    print("🏦 MICR Reader - Interface de Démonstration Business")
    print("=" * 60)
    
    # Vérifier la clé API
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'votre-clé-api-openai':
        print("❌ Clé API OpenAI manquante !")
        print("💡 Solutions:")
        print("   1. Utilisez: python launch_demo.py --api-key sk-votre-clé")
        print("   2. Définissez: set OPENAI_API_KEY=sk-votre-clé")
        print("   3. Modifiez config.py avec votre clé")
        return
    
    print(f"✅ Clé API configurée: {api_key[:10]}...")
    
    try:
        # Créer et lancer l'interface
        interface = MICRGradioInterface(
            api_key=api_key,
            share=args.share,
            server_name=args.host,
            server_port=args.port
        )
        
        print(f"\n🚀 Lancement de l'interface...")
        print(f"🌐 URL locale: http://{args.host}:{args.port}")
        
        if args.share:
            print("🌍 Lien de partage public sera généré...")
        
        print("\n💡 Conseils pour la démonstration:")
        print("   • Utilisez des images de chèques canadiens de bonne qualité")
        print("   • Résolution recommandée: 300 DPI minimum")
        print("   • Formats supportés: JPG, PNG, BMP, TIFF")
        print("   • Taille maximum: 10MB")
        
        print("\n⚡ Fonctionnalités à démontrer:")
        print("   🎯 Système de confiance tri-modal innovant")
        print("   📈 Analyse des logprobs en temps réel")
        print("   🏛️ Reconnaissance automatique des banques")
        print("   ✅ Validation des standards MICR canadiens")
        
        print(f"\n{'='*60}")
        print("🎬 Interface prête pour vos démonstrations business !")
        print("🔥 Impressionnez vos clients avec l'IA de nouvelle génération")
        print(f"{'='*60}\n")
        
        # Lancer l'interface
        interface.launch(
            debug=args.debug,
            show_error=True
        )
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Interface fermée par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur lors du lancement: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
