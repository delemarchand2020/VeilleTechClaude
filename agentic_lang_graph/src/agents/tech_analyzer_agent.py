"""
Agent Analyse Tech avec LangGraph - Version Production.

Transformation du prototype simple en workflow LangGraph structuré
avec parallélisation, gestion d'état et patterns avancés.
"""
import asyncio
import json
import os
from typing import List, Dict, Optional, Any, Annotated
from dataclasses import dataclass, field
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.runnables import RunnableConfig
from loguru import logger
from dotenv import load_dotenv

# Chargement automatique des variables d'environnement
load_dotenv()

# Imports des modèles centralisés
from ..connectors import RawContent
from ..models.analysis_models import (
    ExpertProfile,
    ContentAnalysis,
    AnalyzedContent,
    DifficultyLevel
)
from ..utils.prompt_loader import load_prompt


@dataclass
class AnalysisState:
    """État du workflow d'analyse LangGraph."""
    
    # Input
    raw_contents: List[RawContent] = field(default_factory=list)
    expert_profile: Optional[ExpertProfile] = None
    
    # Processing state
    current_batch: List[RawContent] = field(default_factory=list)
    analysis_results: List[AnalyzedContent] = field(default_factory=list)
    failed_analyses: List[Dict[str, Any]] = field(default_factory=list)
    
    # Configuration
    batch_size: int = 3  # Nombre de contenus analysés en parallèle
    max_retries: int = 2
    
    # Metadata
    total_contents: int = 0
    processed_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Messages pour debugging
    messages: Annotated[list, add_messages] = field(default_factory=list)


class TechAnalyzerAgent:
    """
    Agent Analyse Tech avec LangGraph - Version Production.
    
    Workflow intelligent pour analyser les contenus collectés avec :
    - Parallélisation des analyses LLM
    - Gestion d'état centralisée  
    - Retry et fallback automatiques
    - Monitoring et debugging avancés
    """
    
    def __init__(self, expert_profile: ExpertProfile = None):
        """
        Initialise l'agent analyseur avec LangGraph.
        
        Args:
            expert_profile: Profil de l'expert pour personnaliser l'analyse
        """
        self.profile = expert_profile or ExpertProfile()
        self.logger = logger.bind(component="TechAnalyzerAgent")
        
        # Configuration LLM
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=500,
            api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Construction du workflow LangGraph
        self.workflow = self._build_workflow()
        self.compiled_workflow = self.workflow.compile()
        
        self.logger.info("🔄 Agent Analyse Tech (LangGraph) initialisé")
    
    def _build_workflow(self) -> StateGraph:
        """Construit le workflow LangGraph pour l'analyse."""
        
        # Création du graphe d'état
        workflow = StateGraph(AnalysisState)
        
        # Ajout des nœuds
        workflow.add_node("initialize", self._initialize_analysis)
        workflow.add_node("batch_processor", self._process_batch)
        workflow.add_node("single_analyzer", self._analyze_single_content)
        workflow.add_node("aggregator", self._aggregate_results)
        workflow.add_node("finalizer", self._finalize_analysis)
        
        # Définition des arêtes
        workflow.set_entry_point("initialize")
        
        workflow.add_edge("initialize", "batch_processor")
        workflow.add_edge("batch_processor", "single_analyzer")
        workflow.add_edge("single_analyzer", "aggregator")
        
        # Condition pour continuer ou finaliser
        workflow.add_conditional_edges(
            "aggregator",
            self._should_continue,
            {
                "continue": "batch_processor",
                "finish": "finalizer"
            }
        )
        
        workflow.add_edge("finalizer", END)
        
        return workflow
    
    async def analyze_contents(self, 
                             raw_contents: List[RawContent],
                             config: Optional[RunnableConfig] = None) -> List[AnalyzedContent]:
        """
        Point d'entrée principal pour analyser des contenus.
        
        Args:
            raw_contents: Contenus bruts à analyser
            config: Configuration LangGraph optionnelle
            
        Returns:
            Liste des contenus analysés et enrichis
        """
        if not raw_contents:
            return []
        
        self.logger.info(f"🧠 Début analyse LangGraph de {len(raw_contents)} contenus")
        
        # État initial
        initial_state = AnalysisState(
            raw_contents=raw_contents,
            expert_profile=self.profile,
            total_contents=len(raw_contents),
            start_time=datetime.now()
        )
        
        # Exécution du workflow
        try:
            final_state = await self.compiled_workflow.ainvoke(
                initial_state,
                config=config or {}
            )
            
            # Extraction des résultats
            analyzed_contents = final_state.get("analysis_results", [])
            
            # Les résultats sont déjà triés par final_score dans _finalize_analysis
            
            # Logging des résultats
            processing_time = (final_state.get("end_time", datetime.now()) - 
                             final_state.get("start_time", datetime.now())).total_seconds()
            
            self.logger.info(f"✅ Analyse terminée en {processing_time:.2f}s")
            self.logger.info(f"📊 {len(analyzed_contents)} contenus analysés")
            
            if final_state.get("failed_analyses"):
                self.logger.warning(f"⚠️ {len(final_state['failed_analyses'])} analyses échouées")
            
            return analyzed_contents
            
        except Exception as e:
            self.logger.error(f"❌ Erreur workflow LangGraph: {e}")
            raise
    
    async def _initialize_analysis(self, state: AnalysisState) -> AnalysisState:
        """Nœud d'initialisation du workflow."""
        self.logger.debug("🔄 Initialisation analyse")
        
        state.messages.append(HumanMessage(
            content=f"Initialisation analyse de {state.total_contents} contenus"
        ))
        
        state.processed_count = 0
        state.start_time = datetime.now()
        
        return state
    
    async def _process_batch(self, state: AnalysisState) -> AnalysisState:
        """Prépare le prochain batch de contenus à analyser."""
        
        # Calcul du batch suivant
        start_idx = state.processed_count
        end_idx = min(start_idx + state.batch_size, state.total_contents)
        
        if start_idx >= state.total_contents:
            # Plus de contenus à traiter
            state.current_batch = []
            return state
        
        state.current_batch = state.raw_contents[start_idx:end_idx]
        
        self.logger.debug(f"📦 Batch {start_idx}-{end_idx}: {len(state.current_batch)} contenus")
        
        return state
    
    async def _analyze_single_content(self, state: AnalysisState) -> AnalysisState:
        """Analyse un batch de contenus en parallèle."""
        
        if not state.current_batch:
            return state
        
        self.logger.debug(f"🧠 Analyse parallèle de {len(state.current_batch)} contenus")
        
        # Analyse en parallèle avec asyncio.gather
        analysis_tasks = [
            self._analyze_content_with_llm(content, state.expert_profile)
            for content in state.current_batch
        ]
        
        try:
            # Exécution parallèle avec gestion des erreurs
            analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # Traitement des résultats
            for i, result in enumerate(analysis_results):
                content = state.current_batch[i]
                
                if isinstance(result, Exception):
                    # Gestion d'erreur
                    self.logger.error(f"❌ Erreur analyse {content.title[:30]}...: {result}")
                    state.failed_analyses.append({
                        "content": content,
                        "error": str(result),
                        "timestamp": datetime.now()
                    })
                else:
                    # Succès
                    analyzed_content = AnalyzedContent(
                        raw_content=content,
                        analysis=result
                    )
                    
                    # Calcul du score final pondéré pour compatibilité avec le synthétiseur
                    final_score = (
                        result.relevance_score * 0.4 +  # Normalisation 0-10 -> 0-1
                        result.practical_value * 0.3 +
                        (8.0 if result.recommended else 4.0) * 0.3
                    ) / 10.0  # Normalisation finale vers 0-1
                    
                    # Ajout de l'attribut final_score pour compatibilité
                    analyzed_content.final_score = final_score
                    analyzed_content.priority_rank = 0  # Sera calculé plus tard
                    
                    state.analysis_results.append(analyzed_content)
                    
                    score = result.relevance_score
                    status = "✅" if result.recommended else "❌"
                    self.logger.debug(f"{status} {score:.1f}/10 - {content.title[:50]}...")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur batch analysis: {e}")
            # Marquer tout le batch comme échoué
            for content in state.current_batch:
                state.failed_analyses.append({
                    "content": content,
                    "error": str(e),
                    "timestamp": datetime.now()
                })
        
        return state
    
    async def _analyze_content_with_llm(self, 
                                      content: RawContent, 
                                      profile: ExpertProfile) -> ContentAnalysis:
        """Analyse un contenu unique avec le LLM."""
        
        # Construction des messages
        system_prompt = self._build_system_prompt(profile)
        analysis_prompt = self._build_analysis_prompt(content)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=analysis_prompt)
        ]
        
        # Appel LLM
        response = await self.llm.ainvoke(messages)
        
        # Parse de la réponse JSON
        try:
            result_data = json.loads(response.content)
            
            return ContentAnalysis(
                relevance_score=float(result_data.get("relevance_score", 0)),
                difficulty_level=DifficultyLevel(result_data.get("difficulty_level", "intermediate")),
                main_topics=result_data.get("main_topics", []),
                key_insights=result_data.get("key_insights", ""),
                practical_value=float(result_data.get("practical_value", 0)),
                reasons=result_data.get("reasons", []),
                recommended=bool(result_data.get("recommended", False))
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Erreur parsing réponse LLM: {e}")
            # Retourne une analyse par défaut
            return ContentAnalysis(
                relevance_score=5.0,
                difficulty_level=DifficultyLevel.INTERMEDIATE,
                main_topics=["parsing_error"],
                key_insights="Erreur d'analyse automatique",
                practical_value=5.0,
                reasons=["Erreur de parsing JSON"],
                recommended=False
            )
    
    async def _aggregate_results(self, state: AnalysisState) -> AnalysisState:
        """Agrège les résultats du batch actuel."""
        
        # Mise à jour du compteur
        state.processed_count += len(state.current_batch)
        
        # Logging de progression
        progress = (state.processed_count / state.total_contents) * 100
        self.logger.info(f"📈 Progression: {state.processed_count}/{state.total_contents} ({progress:.1f}%)")
        
        # Clear du batch actuel
        state.current_batch = []
        
        return state
    
    def _should_continue(self, state: AnalysisState) -> str:
        """Détermine si le workflow doit continuer ou se terminer."""
        
        if state.processed_count >= state.total_contents:
            return "finish"
        else:
            return "continue"
    
    async def _finalize_analysis(self, state: AnalysisState) -> AnalysisState:
        """Finalise l'analyse et calcule les statistiques."""
        
        state.end_time = datetime.now()
        
        # Tri des résultats par final_score et attribution des rangs
        if state.analysis_results:
            sorted_results = sorted(
                state.analysis_results, 
                key=lambda x: x.final_score, 
                reverse=True
            )
            
            # Attribution des rangs de priorité
            for i, result in enumerate(sorted_results, 1):
                result.priority_rank = i
            
            # Remplacement de la liste par la version triée
            state.analysis_results = sorted_results
        
        # Statistiques finales
        total_analyzed = len(state.analysis_results)
        total_failed = len(state.failed_analyses)
        success_rate = (total_analyzed / state.total_contents) * 100 if state.total_contents > 0 else 0
        
        self.logger.info(f"📊 Analyse terminée:")
        self.logger.info(f"   ✅ Réussies: {total_analyzed}")
        self.logger.info(f"   ❌ Échouées: {total_failed}")
        self.logger.info(f"   📈 Taux de succès: {success_rate:.1f}%")
        
        # Recommandations
        recommended_count = sum(1 for result in state.analysis_results if result.analysis.recommended)
        self.logger.info(f"   🎯 Recommandations: {recommended_count}/{total_analyzed}")
        
        # Log des top scores
        if state.analysis_results:
            avg_score = sum(r.final_score for r in state.analysis_results) / len(state.analysis_results)
            self.logger.info(f"   📈 Score final moyen: {avg_score:.2f}")
        
        return state
    
    def _build_system_prompt(self, profile: ExpertProfile) -> str:
        """Construit le prompt système pour le LLM."""
        return load_prompt("analyzer/system", {
            "expert_level": profile.level.value,
            "interests": ', '.join(profile.interests),
            "avoid_topics": ', '.join(profile.avoid_topics),
            "preferred_content_types": ', '.join(profile.preferred_content_types)
        })

    def _build_analysis_prompt(self, content: RawContent) -> str:
        """Construit le prompt d'analyse pour un contenu spécifique."""
        
        info_parts = [
            f"TITRE: {content.title}",
            f"SOURCE: {content.source}",
            f"URL: {content.url}"
        ]
        
        if content.excerpt:
            info_parts.append(f"RÉSUMÉ: {content.excerpt}")
        
        if content.author:
            info_parts.append(f"AUTEUR: {content.author}")
        
        if content.tags:
            info_parts.append(f"TAGS: {', '.join(content.tags)}")
        
        if content.published_date:
            info_parts.append(f"DATE: {content.published_date.strftime('%Y-%m-%d')}")
        
        return load_prompt("analyzer/content_analysis", {
            "article_info": chr(10).join(info_parts),
            "expert_level": self.profile.level.value
        })
    
    async def get_recommendations(self, 
                                raw_contents: List[RawContent], 
                                limit: int = 5) -> List[AnalyzedContent]:
        """
        Retourne les top recommandations après analyse avec LangGraph.
        
        Args:
            raw_contents: Contenus à analyser
            limit: Nombre max de recommandations
            
        Returns:
            Top contenus recommandés triés par score
        """
        analyzed = await self.analyze_contents(raw_contents)
        
        # Filtre uniquement les recommandés et applique la limite
        recommended = [c for c in analyzed if c.analysis.recommended][:limit]
        
        self.logger.info(f"🎯 {len(recommended)} recommandations sur {len(analyzed)} analysés")
        return recommended
    
    def print_workflow_state(self, state: AnalysisState):
        """Affiche l'état du workflow (pour debug)."""
        print(f"\n📊 ÉTAT WORKFLOW LANGGRAPH")
        print(f"Total contenus: {state.total_contents}")
        print(f"Traités: {state.processed_count}")
        print(f"Analysés: {len(state.analysis_results)}")
        print(f"Échecs: {len(state.failed_analyses)}")
        print(f"Batch actuel: {len(state.current_batch)}")
