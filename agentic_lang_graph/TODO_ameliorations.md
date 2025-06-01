# TODO - Améliorations du Système de Veille Intelligente

**Date de création** : 1er juin 2025  
**État** : Système fonctionnel - Optimisations identifiées

---

## 📋 Points d'amélioration identifiés

### 1. 🗂️ **Organisation des modèles de données**

**❓ Question** : Dans models, je ne vois que le modèle de synthèse, est-ce normal ?

**📝 Situation actuelle** : Les modèles d'analyse (`ContentAnalysis`, `AnalyzedContent`) sont définis dans `src/agents/simple_analyzer_prototype.py` au lieu d'être dans `src/models/`.

**💡 Amélioration proposée** :
- [ ] Créer `src/models/analysis_models.py` 
- [ ] Extraire tous les modèles d'analyse depuis `simple_analyzer_prototype.py`
- [ ] Centraliser tous les modèles dans le dossier `models/`
- [ ] Mettre à jour les imports dans les agents

**🎯 Bénéfices** : Organisation plus claire, modèles réutilisables, séparation des responsabilités

---

### 2. 💾 **Utilisation de la base de données**

**❓ Question** : Est-ce que la BD est utilisée pour de vrai ?

**📝 Situation actuelle** : Le `DatabaseManager` est initialisé mais pas utilisé. Les données transitent en mémoire entre les agents sans persistance.

**💡 Amélioration proposée** :
- [ ] Sauvegarder les articles collectés dans la BD
- [ ] Persister les résultats d'analyse 
- [ ] Stocker l'historique des digests générés
- [ ] Ajouter des requêtes pour éviter la re-collecte
- [ ] Implémenter un cache intelligent des analyses

**🎯 Bénéfices** : Historique complet, éviter la re-collecte, analytics, débogage facilité

---

### 3. 📝 **Externalisation des prompts**

**❓ Question** : Les prompts sont dans des fichiers .py ?

**📝 Situation actuelle** : Prompts définis comme chaînes Python dans le code (`tech_analyzer_agent.py`, `synthesis_models.py`, `simple_analyzer_prototype.py`).

**💡 Amélioration proposée** :
- [ ] Créer un dossier `prompts/`
- [ ] Externaliser en fichiers `.md` ou `.txt` :
  - `prompts/analyzer_system.md`
  - `prompts/analyzer_content.md` 
  - `prompts/synthesizer_executive.md`
  - `prompts/synthesizer_insights.md`
  - `prompts/synthesizer_recommendations.md`
- [ ] Ajouter support variables avec templating (Jinja2)
- [ ] Versioning des prompts

**🎯 Bénéfices** : Prompts modifiables sans redéploiement, versioning, collaboration non-dev

---

### 4. ⚙️ **Centralisation de la configuration**

**❓ Question** : Les paramètres pour ma veille (combien d'articles, les sujets...) sont où ?

**📝 Situation actuelle** : Configuration dispersée dans `main.py`, `tech_collector_agent.py`, `synthesis_models.py`, `simple_analyzer_prototype.py`.

**💡 Amélioration proposée** :
- [ ] Créer `config/veille_config.yaml` :
```yaml
collection:
  total_limit: 15
  source_limits:
    medium: 8
    arxiv: 8
  keywords:
    - AI
    - GenAI
    - LLM
  max_age_days: 30

analysis:
  expert_level: intermediate
  interests:
    - LangGraph
    - Multi-agent
  avoid_topics:
    - basic tutorials

synthesis:
  max_articles_in_digest: 3
  target_audience: senior_engineer
```
- [ ] Loader de configuration centralisé
- [ ] Validation des paramètres

**🎯 Bénéfices** : Configuration unique, facile à modifier, validation, environnements multiples

---

### 5. 📊 **Paramètres de sortie configurables**

**❓ Question** : Et les paramètres de l'output (top X, contenu, ...) sont où ?

**📝 Situation actuelle** : Paramètres d'output dans `DEFAULT_SYNTHESIS_CONFIG` en dur dans le code.

**💡 Amélioration proposée** :
- [ ] Intégrer dans `config/veille_config.yaml` :
```yaml
output:
  digest:
    max_articles: 3
    max_insights: 5
    max_recommendations: 4
    word_limits:
      executive_summary: 150
      article_summary: 100
    format:
      tone: professional
      technical_depth: high
      include_technical_trends: true
```
- [ ] Interface CLI pour override : `python main.py --max-articles 5`
- [ ] Profils de configuration multiples (démo, production, expert)

**🎯 Bénéfices** : Flexibilité, adaptation audience, tests A/B

---

## 🚀 Améliorations complémentaires

### 6. 📈 **Monitoring et métriques**
- [ ] Dashboard des performances (temps, taux succès)
- [ ] Métriques qualité (scores moyens, taux recommandation)
- [ ] Alertes en cas d'échec
- [ ] Logs structurés (JSON)

### 7. 🔄 **Optimisations performance**
- [ ] Cache des analyses LLM
- [ ] Parallélisation collecte sources
- [ ] Optimisation prompts (tokens)
- [ ] Rate limiting intelligent

### 8. 🎨 **Interface utilisateur**
- [ ] Web UI pour configuration
- [ ] Prévisualisation digests
- [ ] Historique et recherche
- [ ] Export formats multiples (PDF, HTML)

### 9. 🔌 **Extensibilité**
- [ ] Plugin system pour nouvelles sources
- [ ] API REST pour intégration
- [ ] Webhooks pour notifications
- [ ] Support multi-langues

### 10. 🛡️ **Robustesse production**
- [ ] Health checks automatisés
- [ ] Retry policies configurables
- [ ] Circuit breakers
- [ ] Backup/restore configuration

---

## 📝 Plan de mise en œuvre suggéré

### Phase 1 (Quick wins) - 1-2h
- [ ] Externaliser configuration principale
- [ ] Créer structure `config/` et `prompts/`

### Phase 2 (Organisation) - 2-3h  
- [ ] Refactoring modèles vers `models/`
- [ ] Externaliser tous les prompts

### Phase 3 (Fonctionnalités) - 4-6h
- [ ] Intégration BD complète
- [ ] Monitoring basique
- [ ] Interface CLI enrichie

### Phase 4 (Production) - 1-2j
- [ ] Web UI
- [ ] Optimisations performance
- [ ] Documentation utilisateur

---

**🎯 Priorité recommandée** : Phase 1 → Phase 2 → Phase 3 → Phase 4

*Ces améliorations transformeront le système actuel (fonctionnel) en solution production-ready robuste et maintenable.*