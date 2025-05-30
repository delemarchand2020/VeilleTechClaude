# launch_demo_improved.py
"""
Script de lancement amélioré avec solutions pour le partage Gradio
"""

import os
import sys
import argparse
import time
import requests
from interface.gradio_interface import MICRGradioInterface

def test_gradio_connectivity():
    """Teste la connectivité aux services Gradio"""
    print("🔍 Test de connectivité Gradio...")
    
    try:
        response = requests.get("https://status.gradio.app", timeout=10)
        if response.status_code == 200:
            print("✅ Services Gradio accessibles")
            return True
        else:
            print(f"⚠️ Status Gradio: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Impossible d'accéder aux services Gradio: {str(e)[:50]}...")
        return False

def launch_with_fallback(interface, args):
    """Lance l'interface avec fallback automatique en cas de problème de partage"""
    
    if args.share:
        print("🌍 Tentative de partage public...")
        
        # Vérifier la connectivité d'abord
        if not test_gradio_connectivity():
            print("⚠️ Services Gradio non accessibles - passage en mode local")
            args.share = False
        else:
            try:
                # Tentative avec share=True
                print("🚀 Lancement avec partage public...")
                return interface.launch(
                    share=True,
                    server_name=args.host,
                    server_port=args.port,
                    debug=args.debug,
                    show_error=True,
                    quiet=False
                )
            except Exception as e:
                print(f"❌ Échec du partage public: {str(e)}")
                print("🔄 Basculement en mode local...")
                args.share = False
                time.sleep(2)
    
    # Mode local ou fallback
    if not args.share:
        print(f"🏠 Lancement en mode local...")
        print(f"🌐 URL locale: http://{args.host}:{args.port}")
        
        # Si host est 127.0.0.1, proposer 0.0.0.0 pour accès réseau
        if args.host == "127.0.0.1":
            print("💡 Pour accès réseau local, utilisez: --host 0.0.0.0")
        
        return interface.launch(
            share=False,
            server_name=args.host,
            server_port=args.port,
            debug=args.debug,
            show_error=True,
            quiet=False
        )

def show_sharing_alternatives(host, port):
    """Affiche les alternatives de partage"""
    print("\n" + "="*60)
    print("💡 ALTERNATIVES POUR LE PARTAGE PUBLIC")
    print("="*60)
    
    print("🔧 Option 1: ngrok (RECOMMANDÉ)")
    print("   1. Installer ngrok: https://ngrok.com/download")
    print("   2. Créer un compte gratuit")
    print("   3. Dans un terminal: ngrok http", port)
    print("   4. Utiliser l'URL https://xxx.ngrok.io fournie")
    print()
    
    print("🔧 Option 2: Accès réseau local")
    print(f"   Redémarrer avec: --host 0.0.0.0 --port {port}")
    print("   Puis partager: http://[votre-ip-locale]:" + str(port))
    print()
    
    print("🔧 Option 3: Tunnel SSH")
    print("   Si vous avez un serveur: ssh -R 80:localhost:" + str(port) + " serveur")
    print()
    
    print("🔧 Option 4: Solutions cloud")
    print("   • Hugging Face Spaces (gratuit)")
    print("   • Railway.app")
    print("   • Render.com")
    print("   • Heroku")

def main():
    """Fonction principale de lancement améliorée"""
    
    parser = argparse.ArgumentParser(description="Lance l'interface de démonstration MICR Reader")
    parser.add_argument('--api-key', type=str, help="Clé API OpenAI")
    parser.add_argument('--share', action='store_true', help="Partager publiquement (Gradio share)")
    parser.add_argument('--host', type=str, default="127.0.0.1", help="Adresse du serveur (défaut: 127.0.0.1)")
    parser.add_argument('--port', type=int, default=7860, help="Port du serveur (défaut: 7860)")
    parser.add_argument('--debug', action='store_true', help="Mode debug")
    parser.add_argument('--force-local', action='store_true', help="Forcer le mode local (pas de tentative de partage)")
    
    args = parser.parse_args()
    
    print("🏦 MICR Reader - Interface de Démonstration Business")
    print("=" * 60)
    
    # Vérifier la clé API
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'votre-clé-api-openai':
        print("❌ Clé API OpenAI manquante !")
        print("💡 Solutions:")
        print("   1. Utilisez: python launch_demo_improved.py --api-key sk-votre-clé")
        print("   2. Définissez: set OPENAI_API_KEY=sk-votre-clé")
        print("   3. Modifiez config.py avec votre clé")
        return
    
    print(f"✅ Clé API configurée: {api_key[:10]}...")
    
    # Afficher les informations de version
    try:
        import gradio as gr
        print(f"📦 Gradio version: {gr.__version__}")
    except:
        print("⚠️ Impossible de déterminer la version Gradio")
    
    # Forcer local si demandé
    if args.force_local:
        args.share = False
        print("🏠 Mode local forcé")
    
    try:
        # Créer l'interface
        interface = MICRGradioInterface(
            api_key=api_key,
            share=args.share,
            server_name=args.host,
            server_port=args.port
        )
        
        print(f"\n🚀 Initialisation de l'interface...")
        
        if args.share and not args.force_local:
            print("🌍 Mode partage public demandé")
        else:
            print("🏠 Mode local")
        
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
        
        # Lancement avec gestion d'erreurs
        success = launch_with_fallback(interface, args)
        
        if success and not args.share:
            show_sharing_alternatives(args.host, args.port)
        
        # Interface lancée, attendre fermeture
        print("\n⏸️  Interface en cours d'exécution...")
        print("   Appuyez sur Ctrl+C pour arrêter")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Interface fermée par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur lors du lancement: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        
        print("\n🔧 Solutions possibles:")
        print("   1. Vérifier votre connexion internet")
        print("   2. Mettre à jour Gradio: pip install --upgrade gradio")
        print("   3. Essayer en mode local: --force-local")
        print("   4. Changer de port: --port 7861")

if __name__ == "__main__":
    main()
