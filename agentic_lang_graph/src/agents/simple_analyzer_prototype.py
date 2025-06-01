"""
Prototype simple de l'Agent Analyse Tech.

Version initiale qui analyse les contenus avec un LLM basique,
sans LangGraph pour valider l'approche.
"""
import asyncio
import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from openai import AsyncOpenAI
from loguru import logger
from dotenv import load_dotenv

# Chargement automatique des variables d'environnement
load_dotenv()

from ..connectors import RawContent


class DifficultyLevel(Enum):
    """Niveaux de difficulté des contenus."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate" 
    EXPERT = "expert"


class ExpertLevel(Enum):
    """Niveaux d'expertise du profil."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


@dataclass
class ExpertProfile:
    """Profil de l'expert pour personnaliser l'analyse."""
    level: ExpertLevel = ExpertLevel.INTERMEDIATE
    interests: List[str] = field(default_factory=lambda: [
        "LangGraph", "LangChain", "Multi-agent", "RAG", "GenAI", "LLM"
    ])
    avoid_topics: List[str] = field(default_factory=lambda: [
        "basic tutorials", "introduction to programming", "hello world"
    ])
    preferred_content_types: List[str] = field(default_factory=lambda: [
        "technical implementation", "case studies", "best practices", "architecture"
    ])


@dataclass
class ContentAnalysis:
    """Résultat de l'analyse d'un contenu par le LLM."""
    relevance_score: float          # 0-10
    difficulty_level: DifficultyLevel
    main_topics: List[str]          # Sujets principaux extraits  
    key_insights: str               # Résumé des insights clés
    practical_value: float          # 0-10 (théorique vs pratique)
    reasons: List[str]              # Raisons du score
    recommended: bool               # Recommandé pour le profil expert
    

@dataclass 
class AnalyzedContent:
    """Contenu enrichi avec l'analyse intelligence."""
    raw_content: RawContent
    analysis: ContentAnalysis
    analyzed_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_recommended(self) -> bool:
        """Indique si le contenu est recommandé."""
        return self.analysis.recommended
    
    @property 
    def score(self) -> float:
        """Score de pertinence (alias)."""
        return self.analysis.relevance_score


class SimpleAnalyzerPrototype:
    """
    Prototype simple de l'Agent Analyse Tech.
    
    Version basique qui utilise directement OpenAI sans LangGraph
    pour valider l'approche d'analyse intelligente.
    """
    
    def __init__(self, expert_profile: ExpertProfile = None, api_key: str = None):
        """
        Initialise l'analyseur prototype.
        
        Args:
            expert_profile: Profil de l'expert (utilise le défaut si None)
            api_key: Clé API OpenAI (utilise variable d'env si None)
        """
        self.profile = expert_profile or ExpertProfile()
        
        # Gestion de la clé API
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv('OPENAI_API_KEY')
            
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY manquante. "
                "Définissez-la dans .env ou passez-la en paramètre."
            )
        
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.logger = logger.bind(component="SimpleAnalyzerPrototype")
        
        # Configuration LLM
        self.model = "gpt-4o-mini"  # Modèle rapide et économique pour prototype
        self.max_tokens = 500
        self.temperature = 0.1      # Peu créatif, plus factuel
    
    async def analyze_contents(self, raw_contents: List[RawContent]) -> List[AnalyzedContent]:
        """
        Analyse une liste de contenus et retourne les résultats enrichis.
        
        Args:
            raw_contents: Contenus bruts à analyser
            
        Returns:
            Liste des contenus analysés et scorés
        """
        if not raw_contents:
            return []
        
        self.logger.info(f"🧠 Début analyse de {len(raw_contents)} contenus")
        
        analyzed_contents = []
        
        # Analyse séquentielle pour le prototype (parallèle plus tard)
        for i, content in enumerate(raw_contents, 1):
            try:
                self.logger.debug(f"Analyse {i}/{len(raw_contents)}: {content.title[:50]}...")
                
                analysis = await self._analyze_single_content(content)
                analyzed_content = AnalyzedContent(
                    raw_content=content,
                    analysis=analysis
                )
                
                analyzed_contents.append(analyzed_content)
                
                # Log du résultat
                score = analysis.relevance_score
                recommended = "✅" if analysis.recommended else "❌"
                self.logger.info(f"{recommended} {score:.1f}/10 - {content.title[:50]}...")
                
            except Exception as e:
                self.logger.error(f"❌ Erreur analyse {content.title[:30]}...: {e}")
                # Continue avec les autres contenus
        
        # Tri par score décroissant
        analyzed_contents.sort(key=lambda x: x.score, reverse=True)
        
        self.logger.info(f"✅ Analyse terminée: {len(analyzed_contents)} contenus analysés")
        return analyzed_contents
    
    async def _analyze_single_content(self, content: RawContent) -> ContentAnalysis:
        """
        Analyse un seul contenu avec le LLM.
        
        Args:
            content: Contenu brut à analyser
            
        Returns:
            Analyse du contenu
        """
        # Construction du prompt d'analyse
        prompt = self._build_analysis_prompt(content)
        
        # Appel API OpenAI
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system", 
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        
        # Parse de la réponse JSON
        try:
            result_text = response.choices[0].message.content
            result_data = json.loads(result_text)
            
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
                main_topics=["analysis_error"],
                key_insights="Erreur d'analyse automatique",
                practical_value=5.0,
                reasons=["Erreur de parsing"],
                recommended=False
            )
    
    def _get_system_prompt(self) -> str:
        """Prompt système pour configurer le comportement du LLM."""
        return f"""Tu es un expert en veille technologique spécialisé dans l'IA, GenAI, LLM et les systèmes multi-agents.

PROFIL DE L'EXPERT:
- Niveau: {self.profile.level.value}
- Intérêts: {', '.join(self.profile.interests)}
- Éviter: {', '.join(self.profile.avoid_topics)}
- Types préférés: {', '.join(self.profile.preferred_content_types)}

TÂCHE: Analyser des articles techniques et retourner une évaluation JSON structurée.

FORMAT DE RÉPONSE (JSON obligatoire):
{{
    "relevance_score": 8.5,
    "difficulty_level": "intermediate",
    "main_topics": ["LangGraph", "Multi-agent"],
    "key_insights": "Article détaillant...",
    "practical_value": 7.0,
    "reasons": ["Contenu technique avancé", "Exemples pratiques"],
    "recommended": true
}}

CRITÈRES D'ÉVALUATION:
- relevance_score (0-10): Pertinence pour le profil expert
- difficulty_level: "beginner", "intermediate", "expert"
- practical_value (0-10): Valeur pratique vs théorique
- recommended: true si score ≥ 7 ET correspond au profil"""

    def _build_analysis_prompt(self, content: RawContent) -> str:
        """
        Construit le prompt d'analyse pour un contenu spécifique.
        
        Args:
            content: Contenu à analyser
            
        Returns:
            Prompt formaté
        """
        # Compilation des informations disponibles
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
        
        # Construction du prompt final
        prompt = f"""Analyse cet article technique:

{chr(10).join(info_parts)}

Retourne ton analyse au format JSON en évaluant:
1. La pertinence pour un expert {self.profile.level.value} 
2. Le niveau de difficulté technique
3. Les sujets principaux abordés
4. Les insights clés apportés
5. La valeur pratique vs théorique
6. Si tu le recommandes pour ce profil

Réponds uniquement en JSON valide."""
        
        return prompt
    
    async def get_recommendations(self, 
                                raw_contents: List[RawContent], 
                                limit: int = 5) -> List[AnalyzedContent]:
        """
        Retourne les top recommandations après analyse.
        
        Args:
            raw_contents: Contenus à analyser
            limit: Nombre max de recommandations
            
        Returns:
            Top contenus recommandés triés par score
        """
        analyzed = await self.analyze_contents(raw_contents)
        
        # Filtre uniquement les recommandés et applique la limite
        recommended = [c for c in analyzed if c.is_recommended][:limit]
        
        self.logger.info(f"🎯 {len(recommended)} recommandations sur {len(analyzed)} analysés")
        return recommended
    
    def print_analysis_summary(self, analyzed_contents: List[AnalyzedContent]):
        """Affiche un résumé des analyses (pour debug)."""
        if not analyzed_contents:
            print("Aucun contenu analysé")
            return
        
        print(f"\n📊 RÉSUMÉ D'ANALYSE - {len(analyzed_contents)} contenus")
        print("=" * 80)
        
        recommended_count = sum(1 for c in analyzed_contents if c.is_recommended)
        avg_score = sum(c.score for c in analyzed_contents) / len(analyzed_contents)
        
        print(f"Recommandés: {recommended_count}/{len(analyzed_contents)}")
        print(f"Score moyen: {avg_score:.1f}/10")
        print()
        
        print("TOP 5 CONTENUS:")
        for i, content in enumerate(analyzed_contents[:5], 1):
            status = "✅" if content.is_recommended else "❌"
            difficulty = content.analysis.difficulty_level.value
            print(f"{i}. {status} {content.score:.1f}/10 [{difficulty}] {content.raw_content.title}")
            if content.analysis.key_insights:
                insights = content.analysis.key_insights[:100] + "..." if len(content.analysis.key_insights) > 100 else content.analysis.key_insights
                print(f"   💡 {insights}")
            print()
