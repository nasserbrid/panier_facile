# rag.py
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

def create_rag(vectorstore):
    retriever = vectorstore.as_retriever()
    qa = RetrievalQA.from_chain_type(
        llm=ChatOpenAI(temperature=0),
        chain_type="stuff",
        retriever=retriever
    )
    return qa
