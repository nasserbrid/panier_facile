# retriever.py
from langchain_core.documents import Document

def query_vectorstore(vectorstore, query, k=3):
    """
    Effectue une recherche par similarité dans le vectorstore.

    Args:
        vectorstore: un objet FAISS (ou autre vectorstore) contenant les documents.
        query: la question ou texte à rechercher.
        k: nombre de documents similaires à retourner.

    Returns:
        Un string contenant le contexte concaténé des documents les plus pertinents.
    """
    docs = vectorstore.similarity_search(query, k=k)
    context = "\n\n".join([doc.page_content for doc in docs])
    return context
