# vectorstore.py
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

def build_vectorstore(documents, embeddings):
    """
    Construit un vectorstore FAISS à partir des documents.
    """
    return FAISS.from_documents(documents, embeddings)
