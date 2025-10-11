# loader.py
import json
from pathlib import Path
from langchain.schema import Document

def load_ui_docs():
    """Charge les étapes UI depuis ui_docs.json et les transforme en Documents."""
    path = Path(__file__).resolve().parent.parent / "data" / "ui_docs.json"
    with open(path, "r", encoding="utf-8") as f:
        ui_docs = json.load(f)

    documents = []
    for doc in ui_docs:
        title = doc["title"]
        steps = "\n".join(f"{i+1}. {step}" for i, step in enumerate(doc["steps"]))
        content = f"{title}\n{steps}"
        documents.append(Document(page_content=content, metadata={"title": title}))
    return documents
