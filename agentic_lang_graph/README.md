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
│   │   ├── medium_connector.py    # Connecteur Medium ✅
│   │   ├── arxiv_connector.py     # Connecteur ArXiv ✅
│   │   └── base_connector.py      # Classe de base
│   └── utils/           # Configuration et utilitaires
├── data/                # Base de données SQLite
├── output/reports/      # Rapports générés
├── tests/               # Tests
│   ├── test_medium_connector.py ✅
│   └── test_arxiv_connector.py  ✅
├── main.py             # Point d'entrée
└── requirements.txt    # Dépendances
```

## 🔄 Roadmap

- [x] **Phase 1** : Architecture de base et modèles de données
- [x] **Phase 2** : Agent Collecteur Tech (sources multiples) - **50% TERMINÉ**
  - [x] Connecteur Medium ✅
  - [x] Connecteur ArXiv ✅
  - [ ] Connecteur GitHub
  - [ ] Connecteur Towards Data Science
- [ ] **Phase 3** : Agent Analyse Tech (filtrage expert)
- [ ] **Phase 4** : Agent Synthétiseur (rapports Markdown)

## 📊 Sources de données

### ✅ Connecteurs disponibles
- **Medium** : Articles techniques via flux RSS
  - Publications spécialisées (Towards Data Science, etc.)
  - Recherche par tags AI/ML/GenAI
  - Métadonnées complètes (auteur, date, résumé)

- **ArXiv** : Papers académiques via API officielle
  - Catégories techniques (cs.AI, cs.CL, cs.LG, etc.)
  - Recherche dans titres et abstracts
  - Accès aux PDFs et métadonnées complètes
  - Filtrage temporel des publications récentes

### 🚧 Connecteurs en développement
- **GitHub** : Repositories, releases, trending
- **Towards Data Science** : Articles spécialisés ML/AI

## 🧪 Tests

### Exécution des tests

```bash
# Tous les tests
python run_tests.py
# ou
dev.bat test

# Tests des connecteurs seulement
python run_tests.py --connector

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

### Tests manuels des connecteurs

```bash
# Test du connecteur Medium
python test_medium_manual.py

# Test du connecteur ArXiv
python test_arxiv_manual.py
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

### 🆕 Dernières nouveautés

- ✅ **Connecteur ArXiv** : Accès aux papers académiques récents
- ✅ **Tests complets** : Couverture des deux connecteurs Medium et ArXiv
- ✅ **Documentation** : README et plan mis à jour
- 📈 **Progression** : Phase 2 à 50% (2/4 connecteurs terminés)
