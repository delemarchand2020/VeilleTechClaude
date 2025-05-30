# gradio_share_diagnostic.py
"""
Script de diagnostic et solutions pour le partage Gradio
"""

import os
import sys
import requests
import gradio as gr
import time
from typing import Optional

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_internet_connectivity():
    """Test la connectivité internet et les services Gradio"""
    print("🌐 Test de connectivité internet...")
    
    test_urls = [
        ("Google", "https://www.google.com"),
        ("Gradio Status", "https://status.gradio.app"),
        ("Gradio API", "https://api.gradio.app"),
        ("HuggingFace", "https://huggingface.co")
    ]
    
    results = []
    for name, url in test_urls:
        try:
            response = requests.get(url, timeout=10)
            status = "✅ OK" if response.status_code == 200 else f"⚠️ {response.status_code}"
            results.append(f"  {name}: {status}")
        except requests.RequestException as e:
            results.append(f"  {name}: ❌ Erreur - {str(e)[:50]}...")
    
    print("\n".join(results))
    return results

def test_gradio_versions():
    """Vérifie les versions et compatibilité"""
    print("\n🔧 Informations versions...")
    
    try:
        import gradio as gr
        print(f"  Gradio version: {gr.__version__}")
        
        # Vérifier si c'est une version récente (>= 4.0)
        version_parts = gr.__version__.split('.')
        major_version = int(version_parts[0])
        
        if major_version >= 4:
            print("  ✅ Version Gradio récente")
        else:
            print("  ⚠️ Version Gradio ancienne - mise à jour recommandée")
            print("     Commande: pip install --upgrade gradio")
        
        # Tester les fonctionnalités de base
        print("  Test création interface basique...")
        with gr.Blocks() as demo:
            gr.Markdown("Test")
        print("  ✅ Interface créée avec succès")
        
    except Exception as e:
        print(f"  ❌ Erreur Gradio: {e}")

def create_simple_test_interface():
    """Crée une interface de test simple"""
    
    def hello(name):
        return f"Hello {name}!"
    
    with gr.Blocks(title="Test MICR Reader") as demo:
        gr.HTML("<h1>🧪 Test Interface MICR Reader</h1>")
        
        with gr.Row():
            name_input = gr.Textbox(label="Votre nom")
            output = gr.Textbox(label="Réponse")
        
        gr.Button("Dire bonjour").click(hello, name_input, output)
        
        gr.HTML("""
        <p><strong>Test de connectivité:</strong></p>
        <p>Si vous voyez cette interface, Gradio fonctionne localement.</p>
        <p>Pour le partage public, essayez les solutions alternatives.</p>
        """)
    
    return demo

def launch_with_alternatives(demo, port: int = 7860):
    """Lance l'interface avec différentes alternatives de partage"""
    
    print("\n🚀 TENTATIVES DE LANCEMENT")
    print("=" * 40)
    
    # Méthode 1: Essayer share=True d'abord
    print("1️⃣ Tentative avec share=True...")
    try:
        demo.launch(
            share=True,
            server_port=port,
            quiet=True,
            prevent_thread_lock=True
        )
        print("   ✅ Partage public réussi!")
        return True
    except Exception as e:
        print(f"   ❌ Échec du partage public: {str(e)[:100]}...")
    
    # Méthode 2: Local avec accès réseau
    print("\n2️⃣ Lancement en local accessible réseau...")
    try:
        demo.close()  # Fermer la tentative précédente
        time.sleep(1)
        
        demo.launch(
            share=False,
            server_name="0.0.0.0",  # Accessible depuis le réseau
            server_port=port,
            quiet=True,
            prevent_thread_lock=True
        )
        print(f"   ✅ Interface locale accessible!")
        print(f"   🌐 URL locale: http://localhost:{port}")
        print(f"   🌐 URL réseau: http://0.0.0.0:{port}")
        return True
    except Exception as e:
        print(f"   ❌ Échec: {str(e)[:100]}...")
    
    # Méthode 3: Local uniquement
    print("\n3️⃣ Lancement local uniquement...")
    try:
        demo.close()
        time.sleep(1)
        
        demo.launch(
            share=False,
            server_name="127.0.0.1",
            server_port=port,
            quiet=True,
            prevent_thread_lock=True
        )
        print(f"   ✅ Interface locale démarrée!")
        print(f"   🌐 URL: http://127.0.0.1:{port}")
        return True
    except Exception as e:
        print(f"   ❌ Échec: {str(e)[:100]}...")
    
    return False

def show_alternative_solutions():
    """Affiche les solutions alternatives"""
    print("\n💡 SOLUTIONS ALTERNATIVES POUR LE PARTAGE")
    print("=" * 50)
    
    print("🔧 Option 1: ngrok (Recommandé)")
    print("   1. Installer ngrok: https://ngrok.com/download")
    print("   2. Créer un compte gratuit sur ngrok.com")
    print("   3. Lancer votre interface sans share=True")
    print("   4. Dans un autre terminal: ngrok http 7860")
    print("   5. Utiliser l'URL publique fournie par ngrok")
    print()
    
    print("🔧 Option 2: Serveur VPS/Cloud")
    print("   1. Déployer sur un VPS (AWS, DigitalOcean, etc.)")
    print("   2. Configurer un nom de domaine")
    print("   3. Utiliser un reverse proxy (nginx)")
    print()
    
    print("🔧 Option 3: Hugging Face Spaces")
    print("   1. Créer un Space sur huggingface.co/spaces")
    print("   2. Uploader votre code")
    print("   3. Interface automatiquement publique")
    print()
    
    print("🔧 Option 4: Réseau local")
    print("   1. Lancer avec --host 0.0.0.0")
    print("   2. Partager l'IP locale + port avec vos collègues")
    print("   3. Fonctionne sur le même réseau WiFi/LAN")

def main():
    """Fonction principale de diagnostic"""
    
    print("🔬 DIAGNOSTIC GRADIO SHARE")
    print("=" * 40)
    
    # Tests de connectivité
    connectivity_results = test_internet_connectivity()
    
    # Tests de versions
    test_gradio_versions()
    
    # Analyser les résultats
    internet_ok = any("✅" in result for result in connectivity_results if "Google" in result)
    gradio_status_ok = any("✅" in result for result in connectivity_results if "Gradio Status" in result)
    
    print(f"\n📊 ANALYSE:")
    print(f"   Internet: {'✅ OK' if internet_ok else '❌ Problème'}")
    print(f"   Gradio Status: {'✅ OK' if gradio_status_ok else '❌ Problème'}")
    
    if not internet_ok:
        print("\n❌ Problème de connectivité internet détecté")
        print("   Vérifiez votre connexion internet et les paramètres proxy/firewall")
        return
    
    if not gradio_status_ok:
        print("\n⚠️ Service Gradio peut avoir des problèmes")
        print("   Vérifiez https://status.gradio.app pour les mises à jour")
    
    # Créer et tester une interface simple
    print("\n🧪 Test avec interface simple...")
    demo = create_simple_test_interface()
    
    # Tenter le lancement
    success = launch_with_alternatives(demo)
    
    if not success:
        print("\n❌ Toutes les tentatives de lancement ont échoué")
        show_alternative_solutions()
    else:
        print("\n✅ Interface lancée avec succès!")
        show_alternative_solutions()
        
        print("\n⏸️  Interface en cours d'exécution...")
        print("   Appuyez sur Ctrl+C pour arrêter")
        
        try:
            demo.block_thread()
        except KeyboardInterrupt:
            print("\n⏹️  Interface fermée")

if __name__ == "__main__":
    main()
