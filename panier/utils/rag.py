# rag.py
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

def create_rag(vectorstore):
    """
    Crée une chaîne RAG pour répondre aux questions sur l'interface utilisateur.
    Utilise l'API moderne de LangChain avec des Runnables.
    """
    retriever = vectorstore.as_retriever()

    # Créer le template de prompt
    template = """Réponds à la question en te basant sur le contexte suivant :

Contexte: {context}

Question: {question}

Réponse:"""

    prompt = ChatPromptTemplate.from_template(template)

    # Créer la chaîne RAG avec l'API moderne
    llm = ChatOpenAI(temperature=0)

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    qa = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return qa
