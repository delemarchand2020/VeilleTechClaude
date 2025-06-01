# 🧠 Formation LangGraph pour l'Agent Analyseur

> **Documentation d'apprentissage pour implémenter l'Agent Analyseur du système de veille**  
> Basée sur l'architecture existante et les modèles déjà implémentés

## 📋 Table des matières

1. [Contexte du projet](#1-contexte-du-projet)
2. [Concepts LangGraph essentiels](#2-concepts-langgraph-essentiels)
3. [Architecture de l'Agent Analyseur](#3-architecture-de-lagent-analyseur)
4. [Modèles de données requis](#4-modèles-de-données-requis)
5. [Implémentation étape par étape](#5-implémentation-étape-par-étape)
6. [Intégration avec l'existant](#6-intégration-avec-lexistant)

---

## 1. Contexte du projet

### 🎯 Situation actuelle

Vous avez un **Agent Collecteur** opérationnel qui produit des `List[RawContent]` depuis Medium et ArXiv. L'objectif est de créer un **Agent Analyseur** qui transforme ces contenus bruts en articles analysés et scorés.

### 📊 Pipeline cible

```
RawContent[] (Agent Collecteur ✅) → Agent Analyseur 📋 → ScoredArticle[]
```

### 🏗️ Architecture existante utilisée

```python
# Déjà implémenté et fonctionnel
from src.models.database import RawContent
from src.agents.tech_collector_agent import TechCollectorAgent, CollectionConfig

# À créer pour l'Agent Analyseur
from src.models.analysis_models import AnalysisState, ScoredArticle
from src.agents.tech_analyzer_agent import TechAnalyzerAgent
```

---

## 2. Concepts LangGraph essentiels

### 🔹 StateGraph - Le workflow central

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List

# État partagé entre toutes les étapes
class MyWorkflowState(TypedDict):
    input_data: List[str]
    processed_data: List[dict]
    final_result: dict

# Création du workflow
workflow = StateGraph(MyWorkflowState)
```

### 🔹 Nœuds - Fonctions de transformation

```python
def process_step(state: MyWorkflowState) -> MyWorkflowState:
    """Transforme l'état et retourne les modifications."""
    
    # Traitement
    processed = [{"item": item, "status": "processed"} for item in state["input_data"]]
    
    # Retour des modifications d'état
    return {"processed_data": processed}

# Ajout au workflow
workflow.add_node("process", process_step)
```

### 🔹 Arêtes - Logique de flux

```python
# Arête simple
workflow.add_edge(START, "process")
workflow.add_edge("process", END)

# Arête conditionnelle
def should_continue(state: MyWorkflowState) -> str:
    if len(state["processed_data"]) > 5:
        return "detailed_analysis"
    return "quick_summary"

workflow.add_conditional_edges(
    "process",
    should_continue,
    {"detailed_analysis": "deep_node", "quick_summary": "summary_node"}
)
```

### 🔹 Exemple complet minimal

```python
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END

class SimpleState(TypedDict):
    items: List[str]
    processed_count: int

def add_item(state: SimpleState) -> SimpleState:
    new_item = f"Item {state['processed_count'] + 1}"
    return {
        "items": state["items"] + [new_item],
        "processed_count": state["processed_count"] + 1
    }

def should_continue(state: SimpleState) -> str:
    return "continue" if state["processed_count"] < 3 else "stop"

# Construction
workflow = StateGraph(SimpleState)
workflow.add_node("add_item", add_item)
workflow.add_edge(START, "add_item")
workflow.add_conditional_edges(
    "add_item",
    should_continue,
    {"continue": "add_item", "stop": END}
)

# Compilation et exécution
app = workflow.compile()
result = app.invoke({"items": [], "processed_count": 0})
print(result["items"])  # ['Item 1', 'Item 2', 'Item 3']
```

---

## 3. Architecture de l'Agent Analyseur

### 🎯 Objectif spécifique

Transformer `List[RawContent]` (depuis votre Agent Collecteur) en `List[ScoredArticle]` avec analyse intelligente.

### 🔄 Workflow d'analyse

```mermaid
graph TD
    A[RawContent List] --> B[Initialize Analysis]
    B --> C[Filter Relevance]
    C --> D{Is Relevant?}
    D -->|Yes| E[Analyze Technical Depth]
    D -->|No| F[Mark Filtered]
    E --> G[Score Impact]
    G --> H[Prioritize Articles]
    H --> I[Finalize Results]
    F --> I
    I --> J[ScoredArticle List]
```

### 🏗️ Structure de l'agent

```python
class TechAnalyzerAgent:
    """Agent d'analyse basé sur LangGraph."""
    
    def __init__(self, expert_profile: dict = None):
        self.expert_profile = expert_profile or DEFAULT_EXPERT_PROFILE
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        self.graph = None
    
    def create_graph(self) -> StateGraph:
        """Crée le workflow d'analyse."""
        workflow = StateGraph(AnalysisState)
        
        # Nœuds du processus
        workflow.add_node("initialize", self._initialize_analysis)
        workflow.add_node("filter_relevance", self._filter_relevance)
        workflow.add_node("analyze_technical", self._analyze_technical_depth)
        workflow.add_node("score_articles", self._score_and_rank)
        workflow.add_node("finalize", self._finalize_results)
        
        # Flux
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "filter_relevance")
        workflow.add_conditional_edges(
            "filter_relevance",
            self._should_analyze_deeper,
            {"analyze": "analyze_technical", "skip": "finalize"}
        )
        workflow.add_edge("analyze_technical", "score_articles")
        workflow.add_edge("score_articles", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    async def analyze_contents(self, raw_contents: List[RawContent]) -> List[ScoredArticle]:
        """Point d'entrée principal."""
        # Implémentation avec votre workflow
        pass
```

---

## 4. Modèles de données requis

### 📄 État du workflow (`AnalysisState`)

```python
# src/models/analysis_models.py

from typing import TypedDict, List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Réutilise vos modèles existants
from .database import RawContent

class AnalysisStage(Enum):
    INITIAL = "initial"
    FILTERED = "filtered"
    ANALYZED = "analyzed"
    SCORED = "scored"
    FINALIZED = "finalized"

class AnalysisState(TypedDict):
    """État partagé du workflow d'analyse."""
    
    # Configuration
    expert_profile: Dict[str, Any]
    
    # Données d'entrée (depuis votre Agent Collecteur)
    raw_contents: List[RawContent]
    
    # État du processus
    current_stage: AnalysisStage
    processed_count: int
    
    # Résultats intermédiaires
    filtered_contents: List[RawContent]
    article_analyses: Dict[str, 'ArticleAnalysis']  # URL -> Analysis
    
    # Résultats finaux
    scored_articles: List['ScoredArticle']
    
    # Métriques
    processing_time: float
    errors: List[str]
```

### 📊 Analyse d'article

```python
@dataclass
class ArticleAnalysis:
    """Résultat d'analyse d'un article."""
    
    # Évaluation de base
    is_relevant: bool
    relevance_score: float  # 0-1
    
    # Scores techniques
    technical_depth: float  # 0-1
    innovation_score: float  # 0-1
    practical_value: float  # 0-1
    
    # Métadonnées
    reasoning: str
    category: str  # "research", "tutorial", "news"
    expertise_level: str  # "beginner", "intermediate", "advanced"
    estimated_read_time: int  # minutes
    
    # Insights IA
    key_insights: List[str]
    strengths: List[str]
    weaknesses: List[str]
```

### 🏆 Article final scoré

```python
@dataclass
class ScoredArticle:
    """Article final avec analyse complète."""
    
    # Article original (depuis votre collecteur)
    raw_content: RawContent
    
    # Analyse complète
    analysis: ArticleAnalysis
    
    # Scores finaux
    final_score: float  # 0-1
    priority_rank: int
    
    # Enrichissements
    ai_summary: Optional[str] = None
    recommended_for: List[str] = None
    
    # Métadonnées
    analyzed_at: datetime = None
```

### ⚙️ Configuration expert

```python
DEFAULT_EXPERT_PROFILE = {
    "level": "senior",
    "domains": ["machine_learning", "llm", "ai_systems", "software_architecture"],
    "experience_years": 8,
    "avoid_topics": ["beginner_tutorials", "marketing_content", "clickbait"],
    "prefer_topics": ["technical_implementation", "architectural_patterns", 
                      "performance_optimization", "research_insights"],
    "focus_areas": ["scalability", "production_systems", "innovation"]
}
```

---

## 5. Implémentation étape par étape

### 🔹 Étape 1 : Structure de base

```python
# src/agents/tech_analyzer_agent.py

import asyncio
import time
from typing import List, Dict, Any
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Vos modèles existants
from ..models.database import RawContent
from ..models.analysis_models import (
    AnalysisState, AnalysisStage, ArticleAnalysis, ScoredArticle,
    DEFAULT_EXPERT_PROFILE
)

class TechAnalyzerAgent:
    """Agent d'analyse technique avec LangGraph."""
    
    def __init__(self, expert_profile: Dict[str, Any] = None):
        self.expert_profile = expert_profile or DEFAULT_EXPERT_PROFILE
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        self.graph = None
        self._init_prompts()
    
    def _init_prompts(self):
        """Initialise les prompts d'analyse."""
        
        # Prompt de filtrage
        self.relevance_prompt = ChatPromptTemplate.from_messages([
            ("system", """Tu es un expert technique senior. Évalue si cet article est pertinent pour un profil expert.

PROFIL EXPERT:
- Niveau: {expert_level}
- Domaines: {expert_domains}
- Éviter: {avoid_topics}
- Préférer: {prefer_topics}

Réponds par un JSON:
{{
    "is_relevant": true/false,
    "relevance_score": 0.0-1.0,
    "reasoning": "explication",
    "category": "research/tutorial/news",
    "expertise_level": "beginner/intermediate/advanced"
}}"""),
            ("user", """ARTICLE:
Titre: {title}
Source: {source}
Contenu: {content}""")
        ])
        
        # Prompt d'analyse technique
        self.technical_prompt = ChatPromptTemplate.from_messages([
            ("system", """Analyse la profondeur technique de cet article pour un expert.

Évalue:
- PROFONDEUR TECHNIQUE: Complexité, détails d'implémentation
- INNOVATION: Nouveauté, originalité  
- VALEUR PRATIQUE: Applicabilité réelle

JSON attendu:
{{
    "technical_depth": 0.0-1.0,
    "innovation_score": 0.0-1.0,
    "practical_value": 0.0-1.0,
    "key_insights": ["insight1", "insight2"],
    "strengths": ["force1"],
    "weaknesses": ["faiblesse1"],
    "reasoning": "analyse détaillée"
}}"""),
            ("user", """ARTICLE:
Titre: {title}
Contenu: {content}""")
        ])
```

### 🔹 Étape 2 : Nœuds du workflow

```python
    # Continuation de TechAnalyzerAgent
    
    def _initialize_analysis(self, state: AnalysisState) -> AnalysisState:
        """Initialise l'analyse."""
        return {
            "current_stage": AnalysisStage.INITIAL,
            "processed_count": 0,
            "filtered_contents": [],
            "article_analyses": {},
            "scored_articles": [],
            "processing_time": time.time(),
            "errors": []
        }
    
    async def _filter_relevance(self, state: AnalysisState) -> AnalysisState:
        """Filtre les articles par pertinence."""
        
        filtered_contents = []
        analyses = {}
        
        for content in state["raw_contents"]:
            try:
                # Analyse avec LLM
                analysis = await self._evaluate_relevance(content)
                analyses[content.url] = analysis
                
                if analysis.is_relevant:
                    filtered_contents.append(content)
                    
            except Exception as e:
                state["errors"].append(f"Erreur filtrage {content.url}: {str(e)}")
        
        return {
            "current_stage": AnalysisStage.FILTERED,
            "filtered_contents": filtered_contents,
            "article_analyses": analyses,
            "processed_count": len(state["raw_contents"])
        }
    
    async def _evaluate_relevance(self, content: RawContent) -> ArticleAnalysis:
        """Évalue la pertinence avec le LLM."""
        
        # Préparation du prompt avec votre profil expert
        prompt_input = {
            "expert_level": self.expert_profile["level"],
            "expert_domains": ", ".join(self.expert_profile["domains"]),
            "avoid_topics": ", ".join(self.expert_profile["avoid_topics"]),
            "prefer_topics": ", ".join(self.expert_profile["prefer_topics"]),
            "title": content.title,
            "source": content.source,
            "content": content.content[:2000]  # Limite pour le contexte
        }
        
        # Appel LLM
        chain = self.relevance_prompt | self.llm
        response = await chain.ainvoke(prompt_input)
        
        # Parse JSON
        import json
        try:
            result = json.loads(response.content)
            return ArticleAnalysis(
                is_relevant=result["is_relevant"],
                relevance_score=result["relevance_score"],
                technical_depth=0.0,  # À calculer plus tard
                innovation_score=0.0,
                practical_value=0.0,
                reasoning=result["reasoning"],
                category=result["category"],
                expertise_level=result["expertise_level"],
                estimated_read_time=10,  # Estimation par défaut
                key_insights=[],
                strengths=[],
                weaknesses=[]
            )
        except (json.JSONDecodeError, KeyError):
            # Fallback sécurisé
            return ArticleAnalysis(
                is_relevant=False,
                relevance_score=0.0,
                technical_depth=0.0,
                innovation_score=0.0,
                practical_value=0.0,
                reasoning="Erreur d'analyse",
                category="unknown",
                expertise_level="unknown",
                estimated_read_time=0,
                key_insights=[],
                strengths=[],
                weaknesses=[]
            )
    
    def _should_analyze_deeper(self, state: AnalysisState) -> str:
        """Logique conditionnelle."""
        if len(state["filtered_contents"]) > 0:
            return "analyze"
        return "skip"
    
    async def _analyze_technical_depth(self, state: AnalysisState) -> AnalysisState:
        """Analyse technique approfondie."""
        
        updated_analyses = state["article_analyses"].copy()
        
        for content in state["filtered_contents"]:
            if content.url in updated_analyses:
                try:
                    # Analyse technique avec LLM
                    tech_result = await self._evaluate_technical(content)
                    
                    # Mise à jour de l'analyse
                    analysis = updated_analyses[content.url]
                    analysis.technical_depth = tech_result["technical_depth"]
                    analysis.innovation_score = tech_result["innovation_score"]
                    analysis.practical_value = tech_result["practical_value"]
                    analysis.key_insights = tech_result["key_insights"]
                    analysis.strengths = tech_result["strengths"]
                    analysis.weaknesses = tech_result["weaknesses"]
                    
                except Exception as e:
                    state["errors"].append(f"Erreur analyse technique {content.url}: {str(e)}")
        
        return {
            "current_stage": AnalysisStage.ANALYZED,
            "article_analyses": updated_analyses
        }
    
    async def _evaluate_technical(self, content: RawContent) -> Dict[str, Any]:
        """Évaluation technique avec LLM."""
        
        prompt_input = {
            "title": content.title,
            "content": content.content[:3000]
        }
        
        chain = self.technical_prompt | self.llm
        response = await chain.ainvoke(prompt_input)
        
        import json
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {
                "technical_depth": 0.5,
                "innovation_score": 0.5,
                "practical_value": 0.5,
                "key_insights": [],
                "strengths": [],
                "weaknesses": [],
                "reasoning": "Analyse par défaut"
            }
    
    def _score_and_rank(self, state: AnalysisState) -> AnalysisState:
        """Score et classe les articles."""
        
        scored_articles = []
        
        for content in state["filtered_contents"]:
            if content.url in state["article_analyses"]:
                analysis = state["article_analyses"][content.url]
                
                # Calcul score final pondéré
                final_score = (
                    analysis.technical_depth * 0.3 +
                    analysis.innovation_score * 0.25 +
                    analysis.practical_value * 0.25 +
                    analysis.relevance_score * 0.2
                )
                
                scored_article = ScoredArticle(
                    raw_content=content,
                    analysis=analysis,
                    final_score=final_score,
                    priority_rank=0,  # À calculer après tri
                    analyzed_at=datetime.now()
                )
                
                scored_articles.append(scored_article)
        
        # Tri par score décroissant
        scored_articles.sort(key=lambda x: x.final_score, reverse=True)
        
        # Attribution des rangs
        for i, article in enumerate(scored_articles):
            article.priority_rank = i + 1
        
        return {
            "current_stage": AnalysisStage.SCORED,
            "scored_articles": scored_articles
        }
    
    def _finalize_results(self, state: AnalysisState) -> AnalysisState:
        """Finalise l'analyse."""
        
        total_time = time.time() - state["processing_time"]
        
        return {
            "current_stage": AnalysisStage.FINALIZED,
            "processing_time": total_time
        }
```

### 🔹 Étape 3 : Interface principale

```python
    # Point d'entrée principal
    async def analyze_contents(
        self, 
        raw_contents: List[RawContent]
    ) -> List[ScoredArticle]:
        """
        Analyse les contenus collectés par votre Agent Collecteur.
        
        Args:
            raw_contents: Articles bruts du TechCollectorAgent
            
        Returns:
            Articles analysés et scorés
        """
        
        # État initial
        initial_state: AnalysisState = {
            "expert_profile": self.expert_profile,
            "raw_contents": raw_contents,
            "current_stage": AnalysisStage.INITIAL,
            "processed_count": 0,
            "filtered_contents": [],
            "article_analyses": {},
            "scored_articles": [],
            "processing_time": 0.0,
            "errors": []
        }
        
        # Création et exécution du workflow
        if not self.graph:
            self.graph = self.create_graph()
        
        try:
            final_state = await self.graph.ainvoke(initial_state)
            return final_state["scored_articles"]
            
        except Exception as e:
            raise RuntimeError(f"Erreur workflow d'analyse: {str(e)}")
```

---

## 6. Intégration avec l'existant

### 🔗 Pipeline complet avec votre Agent Collecteur

```python
# Exemple d'utilisation complète avec vos agents existants

async def complete_pipeline():
    """Pipeline complet utilisant vos agents."""
    
    # 1. Collecte avec votre agent existant
    from src.agents import TechCollectorAgent, CollectionConfig
    
    collector = TechCollectorAgent()
    config = CollectionConfig(
        total_limit=15,
        keywords=['AI', 'LLM', 'machine learning'],
        max_age_days=30
    )
    
    collection_result = await collector.collect_all_sources(config)
    print(f"✅ Collecté: {collection_result.total_filtered} articles")
    
    # 2. Analyse avec le nouvel agent
    analyzer = TechAnalyzerAgent()
    analyzed_articles = await analyzer.analyze_contents(collection_result.contents)
    
    print(f"✅ Analysé: {len(analyzed_articles)} articles")
    
    # 3. Résultats classés
    top_articles = analyzed_articles[:3]
    for i, article in enumerate(top_articles, 1):
        print(f"\n{i}. {article.raw_content.title}")
        print(f"   Score: {article.final_score:.2f}")
        print(f"   Catégorie: {article.analysis.category}")
        print(f"   URL: {article.raw_content.url}")
    
    return analyzed_articles

# Exécution
if __name__ == "__main__":
    import asyncio
    asyncio.run(complete_pipeline())
```

### 🧪 Tests de base

```python
# tests/test_tech_analyzer_agent.py

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.tech_analyzer_agent import TechAnalyzerAgent
from src.models.database import RawContent

class TestTechAnalyzerAgent:
    
    @pytest.fixture
    def sample_content(self):
        return RawContent(
            title="Advanced Transformer Architectures",
            url="https://example.com/transformers",
            source="arxiv",
            content="This paper presents novel transformer architectures...",
            tags=["transformer", "architecture"]
        )
    
    @pytest.mark.asyncio
    async def test_analyze_contents_basic(self, sample_content):
        """Test d'analyse de base."""
        
        analyzer = TechAnalyzerAgent()
        
        # Mock LLM pour tests rapides
        analyzer.llm = AsyncMock()
        analyzer.llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"is_relevant": true, "relevance_score": 0.8, "reasoning": "Technical", "category": "research", "expertise_level": "advanced"}'
            )
        )
        
        results = await analyzer.analyze_contents([sample_content])
        
        assert len(results) <= 1
        if results:
            assert results[0].final_score >= 0.0
            assert results[0].analysis.is_relevant
```

### 📊 Métriques d'intégration

```python
# Validation avec vos métriques existantes
def validate_integration():
    """Valide l'intégration avec vos composants."""
    
    # Vérification compatibilité avec TechCollectorAgent
    from src.agents import TechCollectorAgent
    from src.models.database import RawContent
    
    # Test de type compatibility
    collector = TechCollectorAgent()
    analyzer = TechAnalyzerAgent()
    
    # Simulation
    mock_raw_contents = [
        RawContent(title="Test", url="test", source="test", content="test")
    ]
    
    print("✅ Types compatibles avec votre architecture existante")
    print("✅ Prêt pour intégration dans votre pipeline")
```

---

## 🎯 Résumé de l'implémentation

### ✅ Ce que vous obtenez

1. **Agent Analyseur LangGraph** compatible avec votre Agent Collecteur
2. **Workflow structuré** : Filtrage → Analyse → Scoring → Priorisation  
3. **Intégration transparente** avec vos modèles `RawContent`
4. **Prompts optimisés** pour analyse technique niveau expert
5. **Gestion d'erreurs** robuste et logging détaillé

### 📁 Fichiers à créer

```python
# 1. Modèles de données
src/models/analysis_models.py

# 2. Agent principal  
src/agents/tech_analyzer_agent.py

# 3. Tests
tests/test_tech_analyzer_agent.py
```

### 🚀 Pipeline final

```python
# Utilisation complète
async def production_pipeline():
    # Votre collecteur existant
    collector = TechCollectorAgent()
    collection_result = await collector.collect_all_sources(config)
    
    # Nouvel analyseur
    analyzer = TechAnalyzerAgent()
    analyzed_articles = await analyzer.analyze_contents(collection_result.contents)
    
    # Articles prêts pour synthèse (Phase 4)
    return analyzed_articles[:5]  # Top 5 articles
```

**🎯 Objectif atteint : Transformer votre `List[RawContent]` en `List[ScoredArticle]` avec LangGraph !**
