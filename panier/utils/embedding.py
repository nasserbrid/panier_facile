# embeddings.py
import os
from langchain_openai import OpenAIEmbeddings

def get_embeddings():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY non définie !")
    return OpenAIEmbeddings(openai_api_key=api_key)

