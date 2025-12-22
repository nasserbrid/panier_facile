# rag.py
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

def create_rag(vectorstore):
    """
    Crée une chaîne RAG pour répondre aux questions sur l'interface utilisateur.
    """
    retriever = vectorstore.as_retriever()
    qa = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(temperature=0),
        chain_type="stuff",
        retriever=retriever
    )
    return qa
