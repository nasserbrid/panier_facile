"""
Vues pour le chatbot RAG.
"""
import logging
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
