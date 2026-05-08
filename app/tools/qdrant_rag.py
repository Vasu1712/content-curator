import uuid
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.models import SourceDocument

QDRANT_URL = "http://localhost:6333"


def build_qdrant_context(source_docs: list[SourceDocument], objective: str) -> str:
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    client = QdrantClient(url=QDRANT_URL)
    collection_name = f"curator_{uuid.uuid4().hex[:8]}"

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts, metadatas = [], []

    for doc in source_docs:
        if not doc.content.strip():
            continue
        for chunk in splitter.split_text(doc.content):
            texts.append(chunk)
            metadatas.append({"source": doc.source_id, "type": doc.source_type})

    if not texts:
        return ""

    sample_vec = embeddings.embed_query("test")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=len(sample_vec), distance=Distance.COSINE),
    )

    try:
        vectorstore = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings,
        )
        vectorstore.add_texts(texts=texts, metadatas=metadatas)

        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        relevant_docs = retriever.invoke(objective)
        return "\n\n".join(d.page_content for d in relevant_docs)
    finally:
        client.delete_collection(collection_name)
