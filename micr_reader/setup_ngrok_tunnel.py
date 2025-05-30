# setup_ngrok_tunnel.py
"""
Script pour configurer automatiquement un tunnel ngrok pour MICR Reader
"""

import os
import sys
import subprocess
import json
import time
import requests
from pathlib import Path

def check_ngrok_installed():
    """Vérifie si ngrok est installé"""
    try:
        result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ ngrok trouvé: {result.stdout.strip()}")
            return True
        else:
            return False
    except FileNotFoundError:
        return False

def install_ngrok_windows():
    """Instructions pour installer ngrok sur Windows"""
    print("📥 ngrok n'est pas installé. Instructions d'installation:")
    print("\n🔧 Option 1: Installation manuelle")
    print("   1. Aller sur: https://ngrok.com/download")
    print("   2. Télécharger ngrok pour Windows")
    print("   3. Extraire ngrok.exe dans un dossier")
    print("   4. Ajouter le dossier au PATH Windows")
    print("\n🔧 Option 2: Avec Chocolatey")
    print("   choco install ngrok")
    print("\n🔧 Option 3: Avec Scoop")
    print("   scoop install ngrok")
    print("\n💡 Après installation, créez un compte gratuit sur ngrok.com")
    print("   et configurez votre token d'authentification:")
    print("   ngrok config add-authtoken VOTRE_TOKEN")

def setup_ngrok_config():
    """Configure ngrok avec un fichier de configuration"""
    
    config_dir = Path.home() / ".ngrok2"
    config_file = config_dir / "ngrok.yml"
    
    # Créer le répertoire si nécessaire
    config_dir.mkdir(exist_ok=True)
    
    # Configuration ngrok pour MICR Reader
    ngrok_config = """
version: "2"
authtoken: YOUR_AUTH_TOKEN
tunnels:
  micr-reader:
    proto: http
    addr: 7860
    bind_tls: true
    inspect: true
    metadata: "MICR Reader Demo Interface"
"""
    
    print(f"📝 Configuration ngrok dans: {config_file}")
    
    if config_file.exists():
        print("⚠️ Fichier de configuration ngrok existant trouvé")
        response = input("Voulez-vous le remplacer? (y/N): ")
        if response.lower() != 'y':
            return False
    
    with open(config_file, 'w') as f:
        f.write(ngrok_config)
    
    print("✅ Configuration ngrok créée")
    print("💡 N'oubliez pas de remplacer YOUR_AUTH_TOKEN par votre token")
    print("   Obtenez votre token sur: https://dashboard.ngrok.com/get-started/your-authtoken")
    
    return True

def start_ngrok_tunnel(port=7860):
    """Démarre un tunnel ngrok"""
    
    print(f"🚀 Démarrage du tunnel ngrok sur le port {port}...")
    
    try:
        # Lancer ngrok en arrière-plan
        process = subprocess.Popen([
            'ngrok', 'http', str(port),
            '--log', 'stdout'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Attendre un peu pour que ngrok démarre
        time.sleep(3)
        
        # Récupérer l'URL publique
        try:
            response = requests.get('http://localhost:4040/api/tunnels')
            if response.status_code == 200:
                tunnels = response.json()['tunnels']
                if tunnels:
                    public_url = tunnels[0]['public_url']
                    print(f"✅ Tunnel ngrok actif!")
                    print(f"🌍 URL publique: {public_url}")
                    print(f"🏠 URL locale: http://localhost:{port}")
                    print(f"📊 Dashboard ngrok: http://localhost:4040")
                    return process, public_url
        except:
            pass
        
        print("⚠️ Tunnel démarré mais URL publique non récupérée")
        print("🔍 Vérifiez le dashboard ngrok: http://localhost:4040")
        return process, None
        
    except Exception as e:
        print(f"❌ Erreur lors du démarrage de ngrok: {e}")
        return None, None

def create_launch_script():
    """Crée un script de lancement combiné"""
    
    launch_script = '''@echo off
echo 🏦 MICR Reader avec tunnel ngrok
echo ================================

echo 🚀 Démarrage du tunnel ngrok...
start "ngrok" ngrok http 7860

echo ⏳ Attente du tunnel (5 secondes)...
timeout /t 5

echo 🎯 Lancement de MICR Reader...
python launch_demo_improved.py --host 0.0.0.0 --port 7860 --force-local

echo ✅ Terminé!
pause
'''
    
    script_path = "launch_with_ngrok.bat"
    
    with open(script_path, 'w') as f:
        f.write(launch_script)
    
    print(f"✅ Script de lancement créé: {script_path}")
    print("💡 Lancez ce script pour démarrer automatiquement ngrok + MICR Reader")

def main():
    """Fonction principale de configuration ngrok"""
    
    print("🌍 CONFIGURATION TUNNEL NGROK POUR MICR READER")
    print("=" * 50)
    
    # Vérifier ngrok
    if not check_ngrok_installed():
        install_ngrok_windows()
        return
    
    print("\n🔧 Options de configuration:")
    print("1. Configurer ngrok avec fichier de config")
    print("2. Démarrer tunnel simple maintenant")
    print("3. Créer script de lancement automatique")
    print("4. Quitter")
    
    while True:
        choice = input("\nChoisissez une option (1-4): ").strip()
        
        if choice == '1':
            setup_ngrok_config()
            break
            
        elif choice == '2':
            port = input("Port MICR Reader (défaut 7860): ").strip() or "7860"
            try:
                port = int(port)
                process, url = start_ngrok_tunnel(port)
                if process:
                    print(f"\n✅ Tunnel actif! Démarrez maintenant MICR Reader:")
                    print(f"   python launch_demo_improved.py --host 0.0.0.0 --port {port} --force-local")
                    print("\n⏸️  Appuyez sur Ctrl+C pour arrêter le tunnel")
                    try:
                        process.wait()
                    except KeyboardInterrupt:
                        print("\n⏹️  Tunnel fermé")
                        process.terminate()
            except ValueError:
                print("❌ Port invalide")
            break
            
        elif choice == '3':
            create_launch_script()
            break
            
        elif choice == '4':
            break
            
        else:
            print("❌ Option invalide")
    
    print("\n💡 Ressources utiles:")
    print("   • Documentation ngrok: https://ngrok.com/docs")
    print("   • Tableau de bord: https://dashboard.ngrok.com")
    print("   • Plans gratuits: jusqu'à 1 tunnel simultané")

if __name__ == "__main__":
    main()
