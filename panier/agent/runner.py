"""
runner.py — Point d'entrée Django pour l'agent PanierFacile.

RÔLE DE CE FICHIER
───────────────────
`graph.py` définit la logique de l'agent.
`runner.py` expose une interface simple pour le reste de l'application :
une seule fonction `run_agent(user, question)` que la vue Django appellera.

SINGLETON `_agent`
───────────────────
`PanierAgent` est instancié une seule fois au démarrage du module
(pattern singleton léger). Cela évite de recréer le client OpenAI
à chaque requête. Les outils, eux, sont recréés à chaque appel
`run()` pour injecter le bon utilisateur.
"""

import logging
from .graph import PanierAgent

logger = logging.getLogger(__name__)

# Instance unique partagée pour toute la durée de vie du process
_agent: PanierAgent | None = None


def get_agent() -> PanierAgent:
    """
    Retourne l'instance singleton de PanierAgent.
    Crée l'instance au premier appel (lazy initialization).
    """
    global _agent
    if _agent is None:
        _agent = PanierAgent()
        logger.info("PanierAgent instancié (singleton).")
    return _agent


def run_agent(user, question: str) -> str:
    """
    Point d'entrée principal appelé par la vue Django.

    Args:
        user    : request.user — l'utilisateur connecté
        question: message saisi par l'utilisateur dans le chatbot

    Returns:
        Réponse finale de l'agent (str)

    Exemple d'utilisation dans une vue :
        from panier.agent.runner import run_agent

        def agent_chat(request):
            question = request.GET.get("question", "")
            answer = run_agent(user=request.user, question=question)
            return JsonResponse({"answer": answer})
    """
    agent = get_agent()
    return agent.run(user=user, question=question)
