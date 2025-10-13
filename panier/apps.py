from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class PanierConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'panier'
    
    def ready(self):
        """Initialise le système RAG dès le démarrage."""
        try:
            from .utils.loader import load_ui_docs
            from .utils.chunker import split_documents
            from .utils.embedding import get_embeddings
            from .utils.vectorstore import build_vectorstore
            from .utils.rag import create_rag
            from .utils import rag_system

            documents = load_ui_docs()
            logger.info(f"{len(documents)} documents RAG chargés au démarrage.")

            chunks = split_documents(documents)
            logger.info(f"{len(chunks)} chunks créés.")

            embeddings = get_embeddings()
            vectorstore = build_vectorstore(chunks, embeddings)

            qa = create_rag(vectorstore)

            # Stockage global
            rag_system.qa = qa
            rag_system.vectorstore = vectorstore

            logger.info("Système RAG initialisé avec succès au démarrage.")

        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du RAG : {e}", exc_info=True)
    
