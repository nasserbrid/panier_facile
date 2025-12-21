# vectorstore.py
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

def build_vectorstore(documents, embeddings):
    return FAISS.from_documents(documents, embeddings)
