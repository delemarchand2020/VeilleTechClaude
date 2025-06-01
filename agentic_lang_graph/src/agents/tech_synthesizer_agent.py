"""
Agent Synthétiseur Tech avec LangGraph - Générateur de Digest Quotidien.

Cet agent transforme les articles analysés en digest quotidien structuré
avec résumé exécutif, insights clés et recommandations actionables.
"""
import asyncio
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import asdict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig
from loguru import logger
from dotenv import load_dotenv
import os

# Chargement automatique des variables d'environnement
load_dotenv()

# Imports des modèles
from ..agents.tech_analyzer_agent import AnalyzedContent
from ..models.synthesis_models import (
    SynthesisState, SynthesisStage, ReportSection,
    ArticleSynthesis, ActionableRecommendation, TechnicalTrend, DailyDigest,
    DEFAULT_SYNTHESIS_CONFIG, SYNTHESIS_PROMPTS
)


class TechSynthesizerAgent:
    """
    Agent Synthétiseur Tech avec LangGraph.
    
    Workflow intelligent pour créer des digests quotidiens à partir
    d'articles analysés avec :
    - Synthèse exécutive automatisée
    - Extraction d'insights transversaux
    - Génération de recommandations actionables
    - Formatage Markdown professionnel
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialise l'agent synthétiseur.
        
        Args:
            config: Configuration de synthèse (utilise la config par défaut si None)
        """
        self.config = config or DEFAULT_SYNTHESIS_CONFIG.copy()
        self.logger = logger.bind(component="TechSynthesizerAgent")
        
        # Configuration LLM - utilise GPT-4o pour la synthèse qualitative
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.2,  # Légèrement plus créatif pour la synthèse
            max_tokens=1000,
            api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Construction du workflow LangGraph
        self.workflow = self._build_workflow()
        self.compiled_workflow = self.workflow.compile()
        
        self.logger.info("📝 Agent Synthétiseur Tech (LangGraph) initialisé")
    
    def _build_workflow(self) -> StateGraph:
        """Construit le workflow LangGraph pour la synthèse."""
        
        # Création du graphe d'état
        workflow = StateGraph(SynthesisState)
        
        # Ajout des nœuds
        workflow.add_node("prepare_content", self._prepare_synthesis)
        workflow.add_node("generate_summary", self._generate_executive_summary)
        workflow.add_node("synthesize_articles", self._synthesize_articles)
        workflow.add_node("extract_insights", self._extract_key_insights)
        workflow.add_node("create_recommendations", self._create_recommendations)
        workflow.add_node("format_digest", self._format_markdown_digest)
        workflow.add_node("finalize", self._finalize_synthesis)
        
        # Définition des arêtes - workflow séquentiel
        workflow.set_entry_point("prepare_content")
        
        workflow.add_edge("prepare_content", "generate_summary")
        workflow.add_edge("generate_summary", "synthesize_articles")
        workflow.add_edge("synthesize_articles", "extract_insights")
        workflow.add_edge("extract_insights", "create_recommendations")
        workflow.add_edge("create_recommendations", "format_digest")
        workflow.add_edge("format_digest", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow
    
    async def create_daily_digest(
        self, 
        analyzed_articles: List[AnalyzedContent],
        config: Optional[RunnableConfig] = None
    ) -> DailyDigest:
        """
        Point d'entrée principal pour créer un digest quotidien.
        
        Args:
            analyzed_articles: Articles analysés depuis l'Agent Analyseur
            config: Configuration LangGraph optionnelle
            
        Returns:
            Digest quotidien complet avec contenu Markdown
        """
        if not analyzed_articles:
            raise ValueError("Aucun article analysé fourni pour la synthèse")
        
        self.logger.info(f"📝 Début création digest de {len(analyzed_articles)} articles")
        
        # Filtrage des articles recommandés pour le digest
        recommended_articles = [
            article for article in analyzed_articles 
            if article.analysis.recommended
        ][:self.config["max_articles_in_digest"]]
        
        if not recommended_articles:
            self.logger.warning("Aucun article recommandé trouvé, utilisation des top articles")
            recommended_articles = analyzed_articles[:self.config["max_articles_in_digest"]]
        
        # État initial
        initial_state: SynthesisState = {
            "synthesis_config": self.config,
            "target_audience": self.config["target_audience"],
            "analyzed_articles": recommended_articles,
            "current_stage": SynthesisStage.INITIAL,
            "processed_sections": [],
            "executive_summary": None,
            "articles_synthesis": [],
            "key_insights": [],
            "technical_trends": [],
            "recommendations": [],
            "final_digest": None,
            "generation_time": 0.0,
            "word_count": 0,
            "errors": []
        }
        
        # Exécution du workflow
        try:
            start_time = time.time()
            final_state = await self.compiled_workflow.ainvoke(
                initial_state,
                config=config or {}
            )
            
            # Extraction du digest final
            digest = final_state.get("final_digest")
            if not digest:
                raise RuntimeError("Échec de la génération du digest")
            
            # Calcul du temps de génération
            generation_time = time.time() - start_time
            digest.generation_time = generation_time
            
            # Logging des résultats
            self.logger.info(f"✅ Digest créé en {generation_time:.2f}s")
            self.logger.info(f"📊 {len(digest.top_articles)} articles, {digest.word_count} mots")
            self.logger.info(f"🎯 {len(digest.recommendations)} recommandations")
            
            if final_state.get("errors"):
                self.logger.warning(f"⚠️ {len(final_state['errors'])} erreurs pendant la génération")
            
            return digest
            
        except Exception as e:
            self.logger.error(f"❌ Erreur workflow synthèse: {e}")
            raise
    
    async def _prepare_synthesis(self, state: SynthesisState) -> SynthesisState:
        """Nœud de préparation du contenu pour la synthèse."""
        self.logger.debug("🔄 Préparation du contenu pour synthèse")
        
        # Validation des articles
        articles = state["analyzed_articles"]
        if not articles:
            state["errors"].append("Aucun article à synthétiser")
            return state
        
        # Tri par score décroissant pour garantir la qualité
        sorted_articles = sorted(
            articles, 
            key=lambda x: x.analysis.relevance_score, 
            reverse=True
        )
        
        # Limitation au nombre configuré
        max_articles = state["synthesis_config"]["max_articles_in_digest"]
        final_articles = sorted_articles[:max_articles]
        
        self.logger.info(f"📋 Préparation: {len(final_articles)} articles sélectionnés")
        
        return {
            "current_stage": SynthesisStage.PREPARED,
            "analyzed_articles": final_articles,
            "processed_sections": [ReportSection.TOP_ARTICLES]
        }
    
    async def _generate_executive_summary(self, state: SynthesisState) -> SynthesisState:
        """Génère le résumé exécutif du digest."""
        self.logger.debug("📄 Génération résumé exécutif")
        
        articles = state["analyzed_articles"]
        
        # Préparation du contexte pour le prompt
        articles_overview = "\n".join([
            f"- {article.raw_content.title} (Score: {article.analysis.relevance_score:.2f}, {article.analysis.category})"
            for article in articles
        ])
        
        # Construction du prompt
        prompt_content = SYNTHESIS_PROMPTS["executive_summary"].format(
            target_audience=state["target_audience"],
            articles_count=len(articles),
            articles_overview=articles_overview
        )
        
        try:
            # Appel LLM
            messages = [
                SystemMessage(content="Tu es un expert technique qui rédige des synthèses de veille."),
                HumanMessage(content=prompt_content)
            ]
            
            response = await self.llm.ainvoke(messages)
            executive_summary = response.content.strip()
            
            self.logger.debug(f"✅ Résumé exécutif généré ({len(executive_summary)} caractères)")
            
            return {
                "current_stage": SynthesisStage.SUMMARIZED,
                "executive_summary": executive_summary,
                "processed_sections": state["processed_sections"] + [ReportSection.EXECUTIVE_SUMMARY]
            }
            
        except Exception as e:
            error_msg = f"Erreur génération résumé exécutif: {str(e)}"
            self.logger.error(error_msg)
            state["errors"].append(error_msg)
            
            # Fallback
            return {
                "executive_summary": "Résumé exécutif indisponible (erreur de génération)",
                "current_stage": SynthesisStage.SUMMARIZED
            }
    
    async def _synthesize_articles(self, state: SynthesisState) -> SynthesisState:
        """Synthétise chaque article individuellement."""
        self.logger.debug(f"📝 Synthèse de {len(state['analyzed_articles'])} articles")
        
        articles_synthesis = []
        
        for article in state["analyzed_articles"]:
            try:
                synthesis = await self._synthesize_single_article(article)
                articles_synthesis.append(synthesis)
                
                self.logger.debug(f"✅ Article synthétisé: {synthesis.title_refined[:50]}...")
                
            except Exception as e:
                error_msg = f"Erreur synthèse article {article.raw_content.title[:30]}...: {str(e)}"
                self.logger.error(error_msg)
                state["errors"].append(error_msg)
                
                # Création d'une synthèse de fallback
                fallback_synthesis = ArticleSynthesis(
                    original_article=article,
                    title_refined=article.raw_content.title,
                    executive_summary="Synthèse indisponible (erreur de génération)",
                    key_takeaways=["Contenu technique à analyser manuellement"],
                    technical_highlights=["Détails d'implémentation à examiner"],
                    relevance_for_audience=article.analysis.relevance_score,
                    actionability_score=0.5,
                    innovation_level="unknown",
                    estimated_read_time=10,
                    complexity_level=article.analysis.expertise_level
                )
                articles_synthesis.append(fallback_synthesis)
        
        return {
            "current_stage": SynthesisStage.INSIGHTS_EXTRACTED,
            "articles_synthesis": articles_synthesis
        }
    
    async def _synthesize_single_article(self, article: AnalyzedContent) -> ArticleSynthesis:
        """Synthétise un article unique avec le LLM."""
        
        # Préparation du prompt
        prompt_content = SYNTHESIS_PROMPTS["article_synthesis"].format(
            title=article.raw_content.title,
            source=article.raw_content.source,
            category=article.analysis.category,
            score=article.analysis.relevance_score,
            insights=', '.join(article.analysis.key_insights) if article.analysis.key_insights else "N/A",
            content=article.raw_content.content[:2000] if article.raw_content.content else article.raw_content.excerpt or "Contenu non disponible"
        )
        
        messages = [
            SystemMessage(content="Tu es un expert qui synthétise des articles techniques pour des ingénieurs seniors."),
            HumanMessage(content=prompt_content)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        # Parse de la réponse JSON
        try:
            result_data = json.loads(response.content)
            
            return ArticleSynthesis(
                original_article=article,
                title_refined=result_data.get("title_refined", article.raw_content.title),
                executive_summary=result_data.get("executive_summary", ""),
                key_takeaways=result_data.get("key_takeaways", []),
                technical_highlights=result_data.get("technical_highlights", []),
                relevance_for_audience=article.analysis.relevance_score,
                actionability_score=article.analysis.practical_value,
                innovation_level=result_data.get("innovation_level", "incremental"),
                estimated_read_time=max(5, len(article.raw_content.content or "") // 200),
                complexity_level=result_data.get("complexity_level", article.analysis.expertise_level)
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Erreur parsing synthèse article: {e}")
            # Retourne une synthèse basique
            return ArticleSynthesis(
                original_article=article,
                title_refined=article.raw_content.title,
                executive_summary=article.analysis.key_insights or "Article technique à analyser",
                key_takeaways=["Contenu technique pertinent"],
                technical_highlights=["Implémentation et architecture"],
                relevance_for_audience=article.analysis.relevance_score,
                actionability_score=article.analysis.practical_value,
                innovation_level="incremental",
                estimated_read_time=10,
                complexity_level=article.analysis.expertise_level
            )
    
    async def _extract_key_insights(self, state: SynthesisState) -> SynthesisState:
        """Extrait les insights clés transversaux."""
        self.logger.debug("🔍 Extraction des insights clés")
        
        # Préparation du contexte depuis les synthèses d'articles
        articles_summaries = "\n\n".join([
            f"ARTICLE: {synthesis.title_refined}\n"
            f"Résumé: {synthesis.executive_summary}\n"
            f"Points clés: {', '.join(synthesis.key_takeaways)}\n"
            f"Aspects techniques: {', '.join(synthesis.technical_highlights)}"
            for synthesis in state["articles_synthesis"]
        ])
        
        prompt_content = SYNTHESIS_PROMPTS["insights_extraction"].format(
            articles_summaries=articles_summaries
        )
        
        try:
            messages = [
                SystemMessage(content="Tu es un expert en veille technologique qui identifie les tendances émergentes."),
                HumanMessage(content=prompt_content)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Parse des insights (un par ligne)
            insights_text = response.content.strip()
            insights = [
                insight.strip().lstrip('- ').lstrip('* ') 
                for insight in insights_text.split('\n') 
                if insight.strip() and not insight.strip().startswith('#')
            ]
            
            # Limitation au nombre configuré
            max_insights = state["synthesis_config"]["max_insights"]
            final_insights = insights[:max_insights]
            
            self.logger.debug(f"✅ {len(final_insights)} insights extraits")
            
            return {
                "current_stage": SynthesisStage.INSIGHTS_EXTRACTED,
                "key_insights": final_insights,
                "processed_sections": state["processed_sections"] + [ReportSection.KEY_INSIGHTS]
            }
            
        except Exception as e:
            error_msg = f"Erreur extraction insights: {str(e)}"
            self.logger.error(error_msg)
            state["errors"].append(error_msg)
            
            # Fallback
            return {
                "key_insights": ["Analyse des tendances indisponible"],
                "current_stage": SynthesisStage.INSIGHTS_EXTRACTED
            }
    
    async def _create_recommendations(self, state: SynthesisState) -> SynthesisState:
        """Crée les recommandations actionables."""
        self.logger.debug("🎯 Création des recommandations actionables")
        
        # Préparation du contexte avec articles et insights
        content_summary = f"""ARTICLES SYNTHÉTISÉS:
{chr(10).join([f"- {s.title_refined}: {s.executive_summary}" for s in state["articles_synthesis"]])}

INSIGHTS CLÉS:
{chr(10).join([f"- {insight}" for insight in state["key_insights"]])}"""
        
        prompt_content = SYNTHESIS_PROMPTS["recommendations"].format(
            content_summary=content_summary,
            target_audience=state["target_audience"]
        )
        
        try:
            messages = [
                SystemMessage(content="Tu es un tech lead qui transforme la veille en actions concrètes."),
                HumanMessage(content=prompt_content)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Parse des recommandations JSON
            result_data = json.loads(response.content)
            recommendations_data = result_data.get("recommendations", [])
            
            recommendations = []
            for rec_data in recommendations_data:
                recommendation = ActionableRecommendation(
                    title=rec_data.get("title", "Recommandation"),
                    description=rec_data.get("description", ""),
                    action_items=rec_data.get("action_items", []),
                    based_on_articles=[article.raw_content.url for article in state["analyzed_articles"]],
                    category=rec_data.get("category", "investigation"),
                    priority=rec_data.get("priority", "medium"),
                    time_investment=rec_data.get("time_investment", "1-4h"),
                    complexity="intermediate",
                    suggested_next_steps=[],
                    related_technologies=[]
                )
                recommendations.append(recommendation)
            
            # Limitation au nombre configuré
            max_recommendations = state["synthesis_config"]["max_recommendations"]
            final_recommendations = recommendations[:max_recommendations]
            
            self.logger.debug(f"✅ {len(final_recommendations)} recommandations créées")
            
            return {
                "current_stage": SynthesisStage.RECOMMENDATIONS_CREATED,
                "recommendations": final_recommendations,
                "processed_sections": state["processed_sections"] + [ReportSection.RECOMMENDATIONS]
            }
            
        except (json.JSONDecodeError, KeyError, Exception) as e:
            error_msg = f"Erreur création recommandations: {str(e)}"
            self.logger.error(error_msg)
            state["errors"].append(error_msg)
            
            # Fallback avec recommandations basiques
            fallback_recommendation = ActionableRecommendation(
                title="Approfondir les technologies émergentes",
                description="Explorer les innovations identifiées dans la veille",
                action_items=["Lire les articles sélectionnés", "Évaluer l'impact sur vos projets"],
                based_on_articles=[],
                category="learning",
                priority="medium",
                time_investment="1-4h",
                complexity="intermediate",
                suggested_next_steps=[],
                related_technologies=[]
            )
            
            return {
                "recommendations": [fallback_recommendation],
                "current_stage": SynthesisStage.RECOMMENDATIONS_CREATED
            }
    
    async def _format_markdown_digest(self, state: SynthesisState) -> SynthesisState:
        """Formate le digest final en Markdown."""
        self.logger.debug("📋 Formatage du digest Markdown")
        
        try:
            # Construction du digest final
            digest = DailyDigest(
                date=datetime.now(),
                title=f"Tech Digest - {datetime.now().strftime('%d %B %Y')}",
                subtitle="Veille technologique GenAI/LLM/Agentic pour ingénieurs seniors",
                target_audience=state["target_audience"],
                executive_summary=state["executive_summary"] or "Résumé non disponible",
                top_articles=state["articles_synthesis"],
                key_insights=state["key_insights"],
                technical_trends=[],  # Simplifié pour cette version
                recommendations=state["recommendations"],
                total_articles_analyzed=len(state["analyzed_articles"]),
                articles_recommended=len([a for a in state["analyzed_articles"] if a.analysis.recommended]),
                average_quality_score=sum(a.analysis.relevance_score for a in state["analyzed_articles"]) / len(state["analyzed_articles"]),
                all_article_links=[
                    {"title": a.raw_content.title, "url": a.raw_content.url, "source": a.raw_content.source}
                    for a in state["analyzed_articles"]
                ],
                suggested_reading=[],
                generated_at=datetime.now(),
                generator_version="1.0",
                llm_model_used="gpt-4o"
            )
            
            # Génération du contenu Markdown
            markdown_content = self._generate_markdown_content(digest)
            digest.markdown_content = markdown_content
            digest.word_count = len(markdown_content.split())
            digest.estimated_read_time = max(1, digest.word_count // 200)  # 200 mots/minute
            
            self.logger.debug(f"✅ Digest formaté ({digest.word_count} mots, {digest.estimated_read_time}min)")
            
            return {
                "current_stage": SynthesisStage.FORMATTED,
                "final_digest": digest,
                "word_count": digest.word_count,
                "processed_sections": state["processed_sections"] + [ReportSection.RESOURCES]
            }
            
        except Exception as e:
            error_msg = f"Erreur formatage digest: {str(e)}"
            self.logger.error(error_msg)
            state["errors"].append(error_msg)
            
            # Digest minimal de fallback
            fallback_digest = DailyDigest(
                date=datetime.now(),
                title="Tech Digest - Erreur de génération",
                subtitle="Erreur lors de la génération du digest",
                target_audience=state["target_audience"],
                executive_summary="Erreur de génération du digest",
                top_articles=[],
                key_insights=[],
                technical_trends=[],
                recommendations=[],
                total_articles_analyzed=0,
                articles_recommended=0,
                average_quality_score=0.0,
                all_article_links=[],
                suggested_reading=[],
                markdown_content="# Erreur\n\nÉchec de la génération du digest.",
                word_count=0,
                estimated_read_time=0
            )
            
            return {
                "final_digest": fallback_digest,
                "current_stage": SynthesisStage.FORMATTED
            }
    
    def _generate_markdown_content(self, digest: DailyDigest) -> str:
        """Génère le contenu Markdown du digest."""
        
        # En-tête
        markdown = f"""# {digest.title}

> {digest.subtitle}  
> 📅 {digest.date.strftime('%d %B %Y')} • 🎯 {digest.target_audience} • ⏱️ {digest.estimated_read_time} min de lecture

---

## 📊 Résumé Exécutif

{digest.executive_summary}

**📈 Métriques de veille:**
- 📄 **Articles analysés:** {digest.total_articles_analyzed}
- ✅ **Articles recommandés:** {digest.articles_recommended}
- 🎯 **Score moyen de qualité:** {digest.average_quality_score:.2f}/1.0

---

## 🏆 Top Articles

"""
        
        # Articles
        for i, article in enumerate(digest.top_articles, 1):
            innovation_emoji = {"breakthrough": "🚀", "significant": "💡", "incremental": "📈"}.get(article.innovation_level, "📄")
            complexity_emoji = {"expert": "🔬", "advanced": "🧠", "intermediate": "📚"}.get(article.complexity_level, "📖")
            
            markdown += f"""### {i}. {innovation_emoji} {article.title_refined}

**{complexity_emoji} {article.complexity_level.title()} • ⏱️ {article.estimated_read_time}min • 📊 {article.relevance_for_audience:.2f}/1.0**

{article.executive_summary}

**🔑 Points clés:**
"""
            for takeaway in article.key_takeaways:
                markdown += f"- {takeaway}\n"
            
            if article.technical_highlights:
                markdown += "\n**⚙️ Aspects techniques:**\n"
                for highlight in article.technical_highlights:
                    markdown += f"- {highlight}\n"
            
            markdown += f"\n🔗 **Source:** [{article.original_article.raw_content.source}]({article.original_article.raw_content.url})\n\n---\n\n"
        
        # Insights
        if digest.key_insights:
            markdown += "## 💡 Insights Clés\n\n"
            for insight in digest.key_insights:
                markdown += f"- **{insight}**\n"
            markdown += "\n---\n\n"
        
        # Recommandations
        if digest.recommendations:
            markdown += "## 🎯 Recommandations Actionables\n\n"
            for i, rec in enumerate(digest.recommendations, 1):
                priority_emoji = {"high": "🔥", "medium": "⚡", "low": "📌"}.get(rec.priority, "📋")
                category_emoji = {"learning": "📚", "implementation": "⚙️", "investigation": "🔍", "monitoring": "👀"}.get(rec.category, "📋")
                
                markdown += f"""### {i}. {priority_emoji} {rec.title}

**{category_emoji} {rec.category.title()} • ⏱️ {rec.time_investment} • 🎯 {rec.priority.title()} priority**

{rec.description}

**Actions concrètes:**
"""
                for action in rec.action_items:
                    markdown += f"- [ ] {action}\n"
                
                markdown += "\n---\n\n"
        
        # Ressources
        markdown += "## 📚 Ressources\n\n"
        markdown += "### 🔗 Liens des articles\n\n"
        for link in digest.all_article_links:
            markdown += f"- [{link['title']}]({link['url']}) *({link['source']})*\n"
        
        # Footer
        markdown += f"""

---

*Digest généré le {digest.generated_at.strftime('%d/%m/%Y à %H:%M')} par {digest.generator_version} • LLM: {digest.llm_model_used}*
"""
        
        return markdown
    
    async def _finalize_synthesis(self, state: SynthesisState) -> SynthesisState:
        """Finalise la synthèse."""
        self.logger.debug("✅ Finalisation de la synthèse")
        
        return {
            "current_stage": SynthesisStage.FINALIZED,
            "generation_time": time.time()
        }
    
    async def save_digest_to_file(self, digest: DailyDigest, output_dir: str = "output/reports") -> str:
        """Sauvegarde le digest dans un fichier Markdown."""
        
        # Création du répertoire de sortie
        os.makedirs(output_dir, exist_ok=True)
        
        # Nom du fichier avec date
        filename = f"tech_digest_{digest.date.strftime('%Y%m%d')}.md"
        filepath = os.path.join(output_dir, filename)
        
        # Écriture du fichier
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(digest.markdown_content)
        
        self.logger.info(f"📝 Digest sauvegardé: {filepath}")
        return filepath
