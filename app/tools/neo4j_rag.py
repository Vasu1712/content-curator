import uuid
from langchain_ollama import OllamaEmbeddings
from langchain_neo4j import Neo4jVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from neo4j import GraphDatabase
from app.models import SourceDocument

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password123"


def build_neo4j_context(source_docs: list[SourceDocument], objective: str) -> str:
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    session_id = uuid.uuid4().hex[:8]
    index_name = f"curator_{session_id}"

    texts, metadatas = [], []
    for doc in source_docs:
        if not doc.content.strip():
            continue
        for chunk in splitter.split_text(doc.content):
            texts.append(chunk)
            metadatas.append({
                "source": doc.source_id,
                "type": doc.source_type,
                "session_id": session_id,
            })

    if not texts:
        return ""

    vectorstore = Neo4jVector.from_texts(
        texts=texts,
        metadatas=metadatas,
        embedding=embeddings,
        url=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASSWORD,
        index_name=index_name,
        node_label="ContentChunk",
        text_node_property="text",
        embedding_node_property="embedding",
    )

    try:
        retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
        relevant_docs = retriever.invoke(objective)
        return "\n\n".join(d.page_content for d in relevant_docs)
    finally:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as s:
            s.run(
                "MATCH (n:ContentChunk {session_id: $sid}) DETACH DELETE n",
                sid=session_id,
            )
        driver.close()
