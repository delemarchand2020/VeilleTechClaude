# test_gradio_quick.py
"""
Test rapide pour diagnostiquer le problème Gradio share
"""

import gradio as gr
import requests
import sys

def test_connectivity():
    """Test rapide de connectivité"""
    try:
        response = requests.get("https://status.gradio.app", timeout=5)
        return response.status_code == 200
    except:
        return False

def simple_demo():
    """Interface de test minimaliste"""
    def echo(text):
        return f"Echo: {text}"
    
    with gr.Blocks(title="Test MICR") as demo:
        gr.HTML("<h2>🧪 Test de connectivité MICR Reader</h2>")
        
        text_input = gr.Textbox(label="Test d'entrée")
        text_output = gr.Textbox(label="Sortie")
        
        gr.Button("Test").click(echo, text_input, text_output)
        
        # Afficher le statut de connectivité
        if test_connectivity():
            gr.HTML("<p style='color: green;'>✅ Services Gradio accessibles</p>")
        else:
            gr.HTML("<p style='color: red;'>❌ Services Gradio non accessibles</p>")
    
    return demo

def main():
    print("🧪 TEST RAPIDE GRADIO SHARE")
    print("=" * 30)
    
    # Test de connectivité
    if test_connectivity():
        print("✅ Services Gradio accessibles")
        print("🚀 Tentative de partage public...")
        
        demo = simple_demo()
        try:
            demo.launch(share=True, quiet=False)
        except Exception as e:
            print(f"❌ Échec du partage: {e}")
            print("🔄 Basculement en mode local...")
            demo.launch(share=False, server_name="0.0.0.0")
    else:
        print("❌ Services Gradio non accessibles")
        print("🏠 Lancement en mode local uniquement...")
        
        demo = simple_demo()
        demo.launch(share=False, server_name="0.0.0.0")

if __name__ == "__main__":
    main()
