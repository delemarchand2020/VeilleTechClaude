# launch_firewall_safe.py
"""
Script de lancement sécurisé pour environnements avec firewall
"""

import os
import sys
import argparse
import socket
from interface.gradio_interface import MICRGradioInterface

def get_local_ip():
    """Récupère l'IP locale"""
    try:
        # Créer une socket pour découvrir l'IP locale
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

def check_port_available(host, port):
    """Vérifie si un port est disponible"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex((host, port))
        s.close()
        return result != 0  # True si port disponible
    except:
        return False

def find_available_port(host, start_port=7860):
    """Trouve un port disponible"""
    for port in range(start_port, start_port + 20):
        if check_port_available(host, port):
            return port
    return start_port

def main():
    """Lancement sécurisé firewall"""
    
    parser = argparse.ArgumentParser(description="MICR Reader - Mode firewall safe")
    parser.add_argument('--api-key', type=str, help="Clé API OpenAI")
    parser.add_argument('--port', type=int, default=7860, help="Port préféré")
    parser.add_argument('--localhost-only', action='store_true', help="Localhost uniquement (127.0.0.1)")
    parser.add_argument('--debug', action='store_true', help="Mode debug")
    
    args = parser.parse_args()
    
    print("🛡️  MICR Reader - Mode Firewall Safe")
    print("=" * 50)
    
    # Vérifier la clé API
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'votre-clé-api-openai':
        print("❌ Clé API OpenAI manquante !")
        print("💡 Utilisez: python launch_firewall_safe.py --api-key sk-votre-clé")
        return
    
    # Déterminer l'host
    if args.localhost_only:
        host = "127.0.0.1"
        print("🏠 Mode localhost uniquement")
    else:
        host = "0.0.0.0"
        local_ip = get_local_ip()
        print(f"🌐 Mode réseau local (IP: {local_ip})")
    
    # Trouver un port disponible
    port = find_available_port(host, args.port)
    if port != args.port:
        print(f"⚠️  Port {args.port} occupé, utilisation du port {port}")
    else:
        print(f"✅ Port {port} disponible")
    
    print(f"\n🚀 Configuration finale:")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   URL: http://{'localhost' if host == '127.0.0.1' else local_ip if 'local_ip' in locals() else host}:{port}")
    
    if not args.localhost_only:
        print(f"\n📱 Pour partage réseau local:")
        print(f"   URL à partager: http://{get_local_ip()}:{port}")
        print(f"   (Fonctionne sur le même WiFi/réseau)")
    
    print(f"\n🛡️  Avantages mode firewall safe:")
    print(f"   • Aucune connexion internet sortante")
    print(f"   • Pas de tentative de tunnel public")
    print(f"   • Compatible environnements sécurisés")
    print(f"   • Détection automatique de port")
    
    try:
        # Créer et lancer l'interface
        interface = MICRGradioInterface(
            api_key=api_key,
            share=False,  # Jamais de partage public
            server_name=host,
            server_port=port
        )
        
        print(f"\n💡 Conseils pour la démonstration:")
        print(f"   • Interface 100% locale - aucun risque sécurité")
        print(f"   • Préparez des images de test à l'avance")
        print(f"   • Utilisez des chèques canadiens de bonne qualité")
        print(f"   • Montrez le système de confiance tri-modal")
        
        print(f"\n🎬 Interface prête - Mode sécurisé activé!")
        print(f"{'='*50}\n")
        
        # Lancement
        interface.launch(
            share=False,
            server_name=host,
            server_port=port,
            debug=args.debug,
            show_error=True,
            quiet=False,
            prevent_thread_lock=False
        )
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Interface fermée par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
