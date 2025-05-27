"""Point d'entrée principal de l'Agent de Veille Intelligente"""
from loguru import logger

from agentic_lang_graph.src.utils.config import validate_config
from agentic_lang_graph.src.models.database import DatabaseManager

def main():
    """Fonction principale"""
    logger.info("🚀 Démarrage de l'Agent de Veille Intelligente - MVP")
    
    try:
        # Validation de la configuration
        validate_config()
        logger.info("✅ Configuration validée")
        
        # Initialisation de la base de données
        db = DatabaseManager()
        logger.info("✅ Base de données initialisée")
        
        # TODO: Implémentation des agents
        logger.info("🔄 Lancement du workflow de veille...")
        
        # Placeholder pour le moment
        logger.info("📝 MVP en cours de développement...")
        logger.info("📋 Prochaines étapes:")
        logger.info("   - Phase 2: Agent Collecteur Tech")
        logger.info("   - Phase 3: Agent Analyse Tech")
        logger.info("   - Phase 4: Agent Synthétiseur")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution: {e}")
        raise

if __name__ == "__main__":
    main()
