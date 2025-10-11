# embeddings.py
from langchain.embeddings.openai import OpenAIEmbeddings

def get_embeddings():
    return OpenAIEmbeddings()
