# vectorstore.py
from langchain.vectorstores import FAISS
from langchain.schema import Document

def build_vectorstore(documents, embeddings):
    return FAISS.from_documents(documents, embeddings)
