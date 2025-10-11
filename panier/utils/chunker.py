# chunker.py
from langchain.text_splitter import CharacterTextSplitter

def split_documents(documents, chunk_size=500, chunk_overlap=50):
    splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = []
    for doc in documents:
        text_chunks = splitter.split_text(doc.page_content)
        for chunk in text_chunks:
            chunks.append(Document(page_content=chunk, metadata=doc.metadata))
    return chunks
