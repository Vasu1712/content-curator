# Curator Agent

An agentic content curation tool that turns any source material — URLs, files, or pasted text — into a structured learning challenge, then evaluates the learner's response with an LLM judge.

---

## Prerequisites

**Ollama** running locally with two models pulled:

```bash
ollama pull llama3
ollama pull nomic-embed-text
```

**Docker** for Qdrant and Neo4j:

```bash
docker compose up -d
```

This starts:
- Qdrant at `localhost:6333`
- Neo4j at `localhost:7474` (HTTP) / `localhost:7687` (Bolt)

**Python 3.11+** with a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Running the Server

```bash
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000` in your browser.

---

## Usage

1. **Set a learning objective** — type it in the centre field and press Enter or the arrow button. This enables the composer.

2. **Add source material** — one or more of:
   - Paste text directly into the composer
   - Attach local files (`.txt`, `.md`, `.pdf`, `.py`, `.js`, `.ts`, `.json`, `.csv`, `.html`)
   - Add URLs via the link button

3. **Submit** — the agent fetches, chunks, and routes the content through the appropriate RAG strategy, then generates a curated bundle and a dynamic challenge.

4. **Answer the challenge** — write your response in the answer field and submit. The LLM judge scores it, provides feedback, and marks it passed (≥ 0.7) or not.

5. **Improved Solution** — five seconds after your score appears, a button reveals an LLM-generated improved version of your answer with annotated improvements.

---
## Project Structure

```
app/
  main.py              FastAPI BFF — endpoints and session store
  graph.py             LangGraph workflow definition
  models.py            Pydantic models
  tools/
    retrieval.py       URL / file / text ingestion tools
    qdrant_rag.py      Standard RAG via Qdrant
    neo4j_rag.py       Graph RAG via Neo4j
    evaluators.py      Faithfulness + answer + improve evaluators
frontend/
  index.html
  style.css
  app.js
docker-compose.yml     Qdrant + Neo4j services
requirements.txt
```
