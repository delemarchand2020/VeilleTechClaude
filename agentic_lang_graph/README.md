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

## 🧪 Technologies

- **Framework** : LangGraph
- **LLM** : OpenAI GPT-4o/GPT-4o-mini
- **Base de données** : SQLite
- **Sources** : Medium, ArXiv, GitHub, Towards Data Science

## 📝 Notes de développement

Ce projet sert aussi de démonstrateur pour l'automatisation de processus manuels avec GenAI.
