"""
graph.py — Définition du graphe LangGraph pour l'agent PanierFacile.

CONCEPTS CLÉS LANGGRAPH
────────────────────────
LangGraph modélise un agent comme un graphe orienté :

  [nœud agent] ──► [nœud tools] ──► [nœud agent] ──► END

- Chaque nœud est une fonction qui reçoit l'état courant et retourne
  un état mis à jour.
- Les arêtes conditionnelles décident vers quel nœud aller ensuite
  selon ce que l'agent a décidé (appeler un outil ou répondre).
- L'état (AgentState) est le seul canal de communication entre les nœuds.
  Aucune variable globale, aucun effet de bord.

ÉTAT DE L'AGENT (AgentState)
──────────────────────────────
Un TypedDict avec une seule clé `messages` : la liste complète des
messages échangés (HumanMessage, AIMessage, ToolMessage...).
`add_messages` est un reducer : au lieu de remplacer la liste, il
AJOUTE les nouveaux messages à la fin — indispensable pour l'historique.

NŒUD "agent"
─────────────
Appelle le LLM (ChatOpenAI) avec les outils liés via `bind_tools`.
Le LLM retourne soit :
  - Un AIMessage avec `tool_calls` → il veut utiliser un outil
  - Un AIMessage sans `tool_calls` → il a sa réponse finale

NŒUD "tools"
─────────────
ToolNode exécute automatiquement les outils demandés par le LLM
et retourne les résultats sous forme de ToolMessage.

ARÊTE CONDITIONNELLE
─────────────────────
Après chaque réponse du LLM, `should_continue` vérifie :
  - tool_calls présents → retour au nœud "tools" (boucle)
  - tool_calls absents  → END (réponse finale)
"""

import logging
from typing import Annotated

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from .tools import AgentTools

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# ÉTAT DU GRAPHE
# ─────────────────────────────────────────────

class AgentState(TypedDict):
    """
    État partagé entre tous les nœuds du graphe.

    `messages` utilise le reducer `add_messages` :
    chaque nœud AJOUTE ses messages à la liste existante
    au lieu de la remplacer — c'est ce qui permet l'historique
    de conversation multi-tours.
    """
    messages: Annotated[list, add_messages]


# ─────────────────────────────────────────────
# PROMPT SYSTÈME
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """Tu es l'assistant de PanierFacile, une application de gestion \
de listes de courses en famille.

Tu peux :
- Créer des courses (articles) et les ajouter à un panier
- Créer un nouveau panier
- Lister les paniers existants
- Répondre aux questions sur l'utilisation de l'application

Règles :
- Réponds toujours en français
- Si l'utilisateur veut ajouter un article, crée d'abord la course
  puis ajoute-la au panier en cours
- Si aucun panier n'existe, propose d'en créer un
- Pour les questions sur l'interface, utilise l'outil rag_search
"""


# ─────────────────────────────────────────────
# CLASSE PRINCIPALE
# ─────────────────────────────────────────────

class PanierAgent:
    """
    Encapsule le graphe LangGraph pour l'agent PanierFacile.

    Usage :
        agent = PanierAgent()
        response = agent.run(user=request.user, question="Ajoute du lait")

    Le graphe est compilé une seule fois à l'instanciation.
    Les outils sont recréés à chaque appel `run()` pour injecter
    le bon utilisateur (pattern closure via AgentTools).
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialise le LLM. Le graphe sera compilé dans `run()`
        car les outils dépendent de l'utilisateur.

        Args:
            model: Nom du modèle OpenAI à utiliser.
                   gpt-4o-mini est suffisant et moins coûteux.
        """
        self.llm = ChatOpenAI(model=model, temperature=0)
        self.tools_factory = AgentTools()
        logger.info(f"PanierAgent initialisé avec le modèle {model}")

    def _build_graph(self, tools: list):
        """
        Construit et compile le graphe LangGraph pour un jeu d'outils donné.

        Structure du graphe :
            START → agent → (tools → agent)* → END

        Le LLM est lié aux outils via `bind_tools` : il connaît leur
        signature et peut décider de les appeler.

        Args:
            tools: Liste d'outils @tool créés par AgentTools.make_tools()

        Returns:
            CompiledGraph prêt à être invoqué.
        """
        # LLM avec connaissance des outils disponibles
        llm_with_tools = self.llm.bind_tools(tools)

        # ── Nœud "agent" ──────────────────────────────────────────────
        # Reçoit l'état courant, appelle le LLM, retourne sa réponse.
        # Le SystemMessage injecte les instructions à chaque tour.
        def agent_node(state: AgentState) -> dict:
            """Appelle le LLM avec l'historique des messages."""
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
            response = llm_with_tools.invoke(messages)
            # On retourne un dict partiel : add_messages l'ajoutera à la liste
            return {"messages": [response]}

        # ── Nœud "tools" ──────────────────────────────────────────────
        # ToolNode exécute automatiquement les outils demandés par le LLM
        # et retourne les résultats sous forme de ToolMessage.
        tool_node = ToolNode(tools)

        # ── Arête conditionnelle ───────────────────────────────────────
        # Appelée après chaque réponse du LLM pour décider la suite.
        def should_continue(state: AgentState) -> str:
            """
            Retourne "tools" si le LLM veut appeler un outil,
            "end" s'il a sa réponse finale.
            """
            last_message = state["messages"][-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return "end"

        # ── Construction du graphe ─────────────────────────────────────
        graph = StateGraph(AgentState)

        # Enregistrement des nœuds
        graph.add_node("agent", agent_node)
        graph.add_node("tools", tool_node)

        # Point d'entrée
        graph.set_entry_point("agent")

        # Arête conditionnelle depuis "agent"
        graph.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",   # → exécuter les outils
                "end": END,         # → réponse finale
            }
        )

        # Après les outils, on revient toujours à l'agent
        graph.add_edge("tools", "agent")

        return graph.compile()

    def run(self, user, question: str) -> str:
        """
        Point d'entrée principal. Crée les outils pour cet utilisateur,
        compile le graphe, et retourne la réponse finale.

        Args:
            user: Instance Django User (request.user)
            question: Message de l'utilisateur

        Returns:
            Réponse finale de l'agent (str)
        """
        from langchain_core.messages import HumanMessage

        # Outils créés avec l'utilisateur injecté par closure
        tools = self.tools_factory.make_tools(user)

        # Graphe compilé avec ces outils
        compiled = self._build_graph(tools)

        # État initial : un seul message humain
        initial_state = {"messages": [HumanMessage(content=question)]}

        logger.info(f"Agent run — user={user.username} question={question[:80]}")

        # Invocation du graphe — retourne l'état final
        final_state = compiled.invoke(initial_state)

        # Le dernier message est la réponse finale de l'agent
        return final_state["messages"][-1].content
