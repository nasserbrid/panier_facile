# embeddings.py
# TEMPORAIREMENT DÉSACTIVÉ - À réactiver quand le système RAG sera fixé
import os
# from langchain_openai import OpenAIEmbeddings

def get_embeddings():
    """
    TEMPORAIREMENT DÉSACTIVÉ
    Retourne un objet OpenAIEmbeddings configuré.
    """
    raise NotImplementedError("Le système RAG est temporairement désactivé")
    # api_key = os.getenv("OPENAI_API_KEY")
    # if not api_key:
    #     raise ValueError("OPENAI_API_KEY non définie !")
    # return OpenAIEmbeddings(openai_api_key=api_key)

