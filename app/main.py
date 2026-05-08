import json
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.graph import curator_graph
from app.models import BundleResponse, EvaluationResult, ImprovedSolution, LearnerSubmission
from app.tools.evaluators import answer_evaluator, improve_answer

app = FastAPI(title="Curator Agent", version="2.0.0")

# In-memory session store: session_id → final graph state
_sessions: dict = {}

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


# ─── BFF Endpoints ────────────────────────────────────────────────────────────

@app.post("/api/curate")
async def curate(
    learning_objective: str = Form(...),
    content: Optional[str] = Form(None),
    urls: str = Form("[]"),
    files: list[UploadFile] = File(default=[]),
):
    """
    Main curation endpoint. Accepts multipart form data with optional files and URLs.
    Returns a BundleResponse plus session_id for subsequent answer submission.
    """
    try:
        url_list: list[str] = json.loads(urls) if urls else []
    except json.JSONDecodeError:
        url_list = [u.strip() for u in urls.split(",") if u.strip()]

    file_dicts: list[dict] = []
    for f in files:
        raw_bytes = await f.read()
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = raw_bytes.decode("latin-1", errors="replace")
        file_dicts.append({"name": f.filename or "upload", "content": text})

    initial_state = {
        "learning_objective": learning_objective,
        "raw_content": content or "",
        "urls": url_list,
        "files": file_dicts,
        "source_documents": [],
        "aggregated_content": "",
        "total_chars": 0,
        "num_sources": 0,
        "strategy": "",
        "retrieved_context": "",
        "bundle_response": None,
        "faithfulness_score": 0.0,
        "error": None,
    }

    final_state = await curator_graph.ainvoke(initial_state)

    if final_state.get("error"):
        err = final_state["error"]
        if "NO_RELEVANT_CONTEXT" in err:
            raise HTTPException(status_code=400, detail="No relevant context found for the given objective.")
        if "PARSE_ERROR" in err:
            raise HTTPException(status_code=502, detail="LLM failed to produce a valid response. Please retry.")
        raise HTTPException(status_code=500, detail=err)

    bundle = final_state.get("bundle_response") or {}
    if not bundle:
        raise HTTPException(status_code=500, detail="No response generated.")

    session_id = uuid.uuid4().hex
    _sessions[session_id] = final_state

    return {
        "session_id": session_id,
        "strategy_used": final_state.get("strategy"),
        "faithfulness_score": final_state.get("faithfulness_score", 0.0),
        "attached_files": [f["name"] for f in file_dicts],
        "url_sources": url_list,
        "learning_objective": learning_objective,
        "aggregated_content_preview": (final_state.get("aggregated_content") or "")[:300],
        "bundle": bundle,
    }


@app.post("/api/evaluate")
async def evaluate_answer(submission: LearnerSubmission):
    """Evaluates a learner's answer against the stored challenge."""
    session = _sessions.get(submission.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    bundle = session.get("bundle_response") or {}
    challenge = bundle.get("dynamic_challenge", "")
    required_output = bundle.get("required_output", "")

    if not challenge:
        raise HTTPException(status_code=400, detail="No challenge found in session.")

    result: EvaluationResult = answer_evaluator(
        challenge=challenge,
        required_output=required_output,
        learner_answer=submission.answer,
    )
    return result


class ImproveSolutionRequest(BaseModel):
    session_id: str
    answer: str


@app.post("/api/improve")
async def improve_solution(submission: ImproveSolutionRequest) -> ImprovedSolution:
    session = _sessions.get(submission.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    bundle = (session.get("bundle_response") or {})
    challenge = bundle.get("dynamic_challenge", "")
    required_output = bundle.get("required_output", "")
    if not challenge:
        raise HTTPException(status_code=400, detail="No challenge found in session.")
    return improve_answer(challenge, required_output, submission.answer)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ─── Frontend Serving ─────────────────────────────────────────────────────────

@app.get("/")
async def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Frontend not built.")
    return FileResponse(str(index))


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
