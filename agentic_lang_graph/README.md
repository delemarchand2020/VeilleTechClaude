# Agent de Veille Intelligente - MVP

Solution agentique basée sur LangGraph pour automatiser la veille technologique sur GenAI/Agentic/LLM.

## 🎯 Objectif

Créer un agent intelligent qui :
- Collecte automatiquement les contenus techniques récents
- Filtre selon un niveau expert
- Produit un digest quotidien des 3 articles les plus pertinents
- Permet d'approfondir avec des résumés détaillés

## 🏗️ Architecture

```
Agent Collecteur Tech → Agent Analyse Tech → Agent Synthétiseur
```

### Agents MVP
- **Agent Collecteur Tech** : Collecte depuis Medium, ArXiv, GitHub, Towards Data Science
- **Agent Analyse Tech** : Filtre et classe selon profil expert
- **Agent Synthétiseur** : Produit les rapports Markdown

## 🛠️ Installation

1. **Cloner le projet** (déjà fait)

2. **Installer les dépendances**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configuration**
   ```bash
   cp .env.example .env
   # Éditer .env avec vos clés API
   ```

4. **Variables d'environnement requises**
   - `OPENAI_API_KEY` : Clé API OpenAI (obligatoire)
   - `GITHUB_TOKEN` : Token GitHub (optionnel)

## 🚀 Utilisation

```bash
python main.py
```

## 📁 Structure du projet

```
├── src/
│   ├── agents/          # Agents LangGraph
│   ├── models/          # Modèles de données et DB
│   ├── connectors/      # Connecteurs vers sources
│   └── utils/           # Configuration et utilitaires
├── data/                # Base de données SQLite
├── output/reports/      # Rapports générés
├── main.py             # Point d'entrée
└── requirements.txt    # Dépendances
```

## 🔄 Roadmap

- [x] **Phase 1** : Architecture de base et modèles de données
- [ ] **Phase 2** : Agent Collecteur Tech (sources multiples)
- [ ] **Phase 3** : Agent Analyse Tech (filtrage expert)
- [ ] **Phase 4** : Agent Synthétiseur (rapports Markdown)

## 🧪 Tests

### Exécution des tests

```bash
# Tous les tests
python run_tests.py
# ou
dev.bat test

# Tests unitaires seulement
python run_tests.py --unit
# ou
dev.bat test-unit

# Tests avec couverture de code
python run_tests.py --coverage --html
# ou
dev.bat test-coverage

# Tests rapides (sans les lents)
python run_tests.py --fast
```

### Structure des tests
- `tests/test_*.py` : Tests unitaires et d'intégration
- `conftest.py` : Configuration partagée et fixtures
- `pytest.ini` : Configuration de pytest

### Markers disponibles
- `@pytest.mark.unit` : Tests unitaires rapides
- `@pytest.mark.integration` : Tests d'intégration
- `@pytest.mark.connector` : Tests spécifiques aux connecteurs
- `@pytest.mark.slow` : Tests lents (peuvent être skippés)
- `@pytest.mark.external` : Tests nécessitant Internet

## 🛠️ Technologies

- **Framework** : LangGraph
- **LLM** : OpenAI GPT-4o/GPT-4o-mini
- **Base de données** : SQLite
- **Sources** : Medium, ArXiv, GitHub, Towards Data Science
- **Tests** : pytest, pytest-asyncio, pytest-cov

## 📝 Notes de développement

Ce projet sert aussi de démonstrateur pour l'automatisation de processus manuels avec GenAI.
