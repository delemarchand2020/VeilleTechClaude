# Tests Manuels

Ce dossier contient un test manuel simple et fiable pour l'Agent Collecteur Tech.

## Script Disponible

### `test_simple.py` ⭐ **RECOMMANDÉ**
Test manuel simple et rapide de l'Agent Collecteur Tech :
```bash
python manual_tests/test_simple.py
```

Ce script effectue :
- Initialisation de l'agent
- Diagnostic de santé des connecteurs
- Test de collecte avec limite réduite (2 articles)
- Affichage des résultats

## Tests Recommandés (Racine du Projet)

### `validation_finale.py` ⭐ **MEILLEUR CHOIX**
Validation complète avec diagnostic détaillé :
```bash
python validation_finale.py
```

### Tests automatisés
Tests complets de l'infrastructure :
```bash
python run_tests.py --agent      # Tests des agents
python run_tests.py --coverage   # Avec couverture
```

## Utilisation

**Pour valider rapidement l'Agent Collecteur Tech :**
```bash
python validation_finale.py
```

**Pour un test manuel simple :**
```bash
python manual_tests/test_simple.py
```

## Note

Les fichiers de test intermédiaires et de debug ont été supprimés pour une structure plus propre. Seuls les tests essentiels et fonctionnels sont conservés.
