"""
Vues pour le chatbot RAG et l'agent LangGraph.

DEUX ENDPOINTS COEXISTENT
──────────────────────────
1. `chatbot_ui`  — ancien chatbot RAG pur (questions UI seulement)
2. `agent_chat`  — nouvel agent LangGraph (actions + questions UI)

POURQUOI GARDER LES DEUX ?
────────────────────────────
`chatbot_ui` reste actif pour ne pas casser le frontend existant.
`agent_chat` est le nouveau endpoint que le frontend appellera
progressivement. Une fois la migration complète, `chatbot_ui`
pourra être supprimé.

AUTHENTIFICATION
─────────────────
`agent_chat` exige `@login_required` car l'agent agit au nom
de l'utilisateur (création de courses, paniers). `chatbot_ui`
ne l'exigeait pas car il ne faisait que répondre à des questions.
"""
import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django_ratelimit.decorators import ratelimit
from openai import OpenAIError, RateLimitError

from ..utils import rag_system
from ..utils.loader import load_ui_docs
from ..utils.chunker import split_documents
from ..utils.embedding import get_embeddings
from ..utils.vectorstore import build_vectorstore
from ..utils.rag import create_rag
from ..agent.runner import run_agent

logger = logging.getLogger(__name__)


def init_rag_if_needed():
    """Initialise le RAG seulement si ce n'est pas déjà fait."""
    if rag_system.qa and rag_system.vectorstore:
        return

    try:
        documents = load_ui_docs()
        logger.info(f"{len(documents)} documents RAG chargés.")

        chunks = split_documents(documents)
        logger.info(f"{len(chunks)} chunks créés.")

        embeddings = get_embeddings()
        vectorstore = build_vectorstore(chunks, embeddings)
        qa = create_rag(vectorstore)

        rag_system.qa = qa
        rag_system.vectorstore = vectorstore
        logger.info("Système RAG initialisé à la demande.")

    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du RAG : {e}", exc_info=True)
        raise e


@ratelimit(key='user_or_ip', rate='30/m', method='GET')
def chatbot_ui(request):
    """
    Endpoint du chatbot avec support RAG.
    Rate limit: 30 requêtes par minute par utilisateur ou IP.
    """
    if getattr(request, 'limited', False):
        return JsonResponse({
            "error": "Trop de requêtes au chatbot. Veuillez patienter quelques instants."
        }, status=429)

    question = request.GET.get("question", "").strip()
    if not question:
        return JsonResponse({"answer": "", "error": "Aucune question fournie"}, status=400)

    try:
        init_rag_if_needed()

        qa = rag_system.qa
        vectorstore = rag_system.vectorstore

        if not qa or not vectorstore:
            return JsonResponse({
                "error": "Le chatbot est temporairement indisponible car le quota OpenAI est dépassé ou le système n'a pas pu être initialisé. Veuillez réessayer plus tard."
            }, status=503)

        logger.info(f"Question: {question[:100]}...")

        try:
            answer = qa.invoke(question)
        except RateLimitError:
            answer = "Le service est temporairement saturé, veuillez réessayer plus tard."
        except OpenAIError as e:
            answer = f"Erreur OpenAI : {str(e)}"

        return JsonResponse({"answer": answer, "question": question})

    except Exception as e:
        logger.error(f"Erreur RAG : {e}", exc_info=True)
        return JsonResponse({
            "error": "Le système RAG n'a pas pu être initialisé",
            "detail": str(e)
        }, status=500)


@login_required
@ratelimit(key='user', rate='20/m', method='GET')
def agent_chat(request):
    """
    Endpoint principal de l'agent LangGraph.

    DIFFÉRENCE AVEC chatbot_ui
    ───────────────────────────
    chatbot_ui   → RAG pur, répond seulement aux questions sur l'UI
    agent_chat   → Agent LangGraph, peut AGIR (créer courses, paniers)
                   ET répondre aux questions via l'outil rag_search

    FLUX D'UNE REQUÊTE
    ───────────────────
    1. La vue reçoit la question
    2. `run_agent(user, question)` est appelé (runner.py)
    3. runner.py délègue à PanierAgent.run() (graph.py)
    4. Le graphe LangGraph s'exécute :
       - LLM décide des outils à utiliser (tools.py)
       - Outils accèdent au Django ORM avec le bon user
       - LLM formule la réponse finale
    5. La réponse finale est retournée en JSON

    PARAMÈTRES GET
    ───────────────
    question (str) : message de l'utilisateur

    RÉPONSE JSON
    ─────────────
    succès  : {"answer": "...", "question": "..."}
    erreur  : {"error": "...", "detail": "..."} + status HTTP approprié

    RATE LIMIT
    ───────────
    20 requêtes/minute par utilisateur connecté.
    Plus restrictif que chatbot_ui (30/min) car chaque appel
    peut déclencher plusieurs appels OpenAI (LLM + outils).
    """
    if getattr(request, 'limited', False):
        return JsonResponse(
            {"error": "Trop de requêtes. Veuillez patienter quelques instants."},
            status=429
        )

    question = request.GET.get("question", "").strip()
    if not question:
        return JsonResponse(
            {"error": "Aucune question fournie"},
            status=400
        )

    logger.info(f"Agent chat — user={request.user.username} question={question[:80]}")

    try:
        # run_agent injecte request.user dans les outils via closure
        # L'agent peut ainsi créer des objets pour le bon utilisateur
        answer = run_agent(user=request.user, question=question)
        return JsonResponse({"answer": answer, "question": question})

    except RateLimitError:
        return JsonResponse(
            {"error": "Le service OpenAI est temporairement saturé. Réessayez dans quelques instants."},
            status=503
        )
    except OpenAIError as e:
        logger.error(f"Erreur OpenAI agent : {e}", exc_info=True)
        return JsonResponse(
            {"error": f"Erreur OpenAI : {str(e)}"},
            status=502
        )
    except Exception as e:
        logger.error(f"Erreur agent : {e}", exc_info=True)
        return JsonResponse(
            {"error": "L'agent n'a pas pu traiter votre demande.", "detail": str(e)},
            status=500
        )


@staff_member_required
def reset_rag_system(request):
    """Réinitialise le système RAG (réservé au staff)."""
    rag_system.qa = None
    rag_system.vectorstore = None

    logger.info(f"Système RAG réinitialisé par {request.user.username}")

    return JsonResponse({
        "status": "success",
        "message": "Système RAG réinitialisé avec succès"
    })
