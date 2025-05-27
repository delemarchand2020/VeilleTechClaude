"""Configuration du projet Agent de Veille"""
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

class Config:
    """Configuration générale"""
    
    # OpenAI API
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Base de données
    DATABASE_PATH = "data/articles.db"
    
    # Répertoires
    OUTPUT_DIR = "output/reports"
    DATA_DIR = "data"
    
    # Paramètres de veille
    MAX_ARTICLES_PER_SOURCE = 10
    ANALYSIS_MODEL = "gpt-4o-mini"  # Modèle pour l'analyse
    SYNTHESIS_MODEL = "gpt-4o"      # Modèle pour la synthèse
    
    # Sources activées
    SOURCES = {
        "medium": True,
        "arxiv": True,
        "github": True,
        "towards_data_science": True
    }
    
    # Mots-clés de recherche
    KEYWORDS = [
        "GenAI", "Generative AI", "LLM", "Large Language Model",
        "Agent", "Agentic", "Multi-agent", "RAG",
        "Retrieval Augmented Generation", "Fine-tuning",
        "Prompt Engineering", "Automation", "Process Optimization"
    ]
    
    # Filtres niveau expert
    EXPERT_FILTERS = {
        "avoid_beginner": ["introduction to", "getting started", "beginners guide"],
        "avoid_too_complex": ["mathematical proof", "theoretical analysis only"],
        "prefer_practical": ["implementation", "tutorial", "case study", "example"]
    }

# Validation de la configuration
def validate_config():
    """Vérifie que la configuration est valide"""
    if not Config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY manquante. Créez un fichier .env avec votre clé API.")
    
    # Créer les répertoires si ils n'existent pas
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
    
    return True
