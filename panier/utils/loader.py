# loader.py
# TEMPORAIREMENT DÉSACTIVÉ - À réactiver quand le système RAG sera fixé
import json
from pathlib import Path
# from langchain_core.documents import Document

def load_ui_docs():
    """
    TEMPORAIREMENT DÉSACTIVÉ
    Charge les étapes UI depuis ui_docs.json et les transforme en Documents.
    """
    raise NotImplementedError("Le système RAG est temporairement désactivé")
    # path = Path(__file__).resolve().parent.parent / "data" / "ui_docs.json"
    # with open(path, "r", encoding="utf-8") as f:
    #     ui_docs = json.load(f)

    # documents = []
    # for doc in ui_docs:
    #     title = doc["title"]
    #     steps = "\n".join(f"{i+1}. {step}" for i, step in enumerate(doc["steps"]))
    #     content = f"{title}\n{steps}"
    #     documents.append(Document(page_content=content, metadata={"title": title}))
    # return documents
