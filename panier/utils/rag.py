# rag.py
# TEMPORAIREMENT DÉSACTIVÉ - À réactiver quand le système RAG sera fixé
# from langchain.chains import RetrievalQA
# from langchain_openai import ChatOpenAI

def create_rag(vectorstore):
    """
    TEMPORAIREMENT DÉSACTIVÉ
    Crée une chaîne RAG pour répondre aux questions sur l'interface utilisateur.
    """
    # retriever = vectorstore.as_retriever()
    # qa = RetrievalQA.from_chain_type(
    #     llm=ChatOpenAI(temperature=0),
    #     chain_type="stuff",
    #     retriever=retriever
    # )
    # return qa
    raise NotImplementedError("Le système RAG est temporairement désactivé")
