import asyncio
import operator
import re
import json
from typing import TypedDict, Annotated, Optional

from langgraph.graph import StateGraph, END, START
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

from app.models import SourceDocument, BundleResponse
from app.tools.retrieval import url_retrieval_tool, file_retrieval_tool, text_processor_tool
from app.tools.qdrant_rag import build_qdrant_context
from app.tools.neo4j_rag import build_neo4j_context
from app.tools.evaluators import faithfulness_evaluator


_GENERATION_PROMPT = PromptTemplate(
    template="""You are an expert instructional designer. Based STRICTLY on the provided context, build a learning challenge.

Learning Objective: {objective}
Source Context: {context}

Rules:
1. Rely ONLY on facts and concepts present in the context.
2. Make the challenge actionable and specific.
3. Do NOT invent outside facts.

Respond with ONLY a JSON object — no markdown fences, no explanation, no preamble. Use exactly these keys:
{{
  "curated_bundle": "<key concepts extracted from the content>",
  "dynamic_challenge": "<real-world scenario testing the objective>",
  "rationale": "<why this challenge fits the content and objective>",
  "required_output": "<exactly what the learner needs to submit>"
}}""",
    input_variables=["objective", "context"],
)


def _flatten_to_str(v) -> str:
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        for key in ("description", "text", "content", "output_format", "title"):
            if key in v and isinstance(v[key], str):
                return v[key]
        return " ".join(str(vv) for vv in v.values() if vv)
    if isinstance(v, list):
        return " ".join(str(item) for item in v if item)
    return str(v)


def _parse_bundle(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM output: {raw[:200]}")
    data = json.loads(match.group())
    required = {"curated_bundle", "dynamic_challenge", "rationale", "required_output"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Missing keys in LLM output: {missing}")
    return {k: (_flatten_to_str(data[k]) if k in required else data[k]) for k in data}


class CuratorState(TypedDict):
    learning_objective: str
    raw_content: Optional[str]
    urls: list[str]
    files: list[dict]

    # Parallel retrieval accumulates docs using operator.add reducer
    source_documents: Annotated[list[SourceDocument], operator.add]

    # Set by aggregator
    aggregated_content: str
    total_chars: int
    num_sources: int

    # Set by strategy router
    strategy: str  # "direct" | "qdrant" | "neo4j"

    # Set by execution nodes
    retrieved_context: str
    bundle_response: Optional[dict]
    faithfulness_score: float

    error: Optional[str]


# ─── Node Implementations ─────────────────────────────────────────────────────

async def intent_router_node(state: CuratorState) -> dict:
    return {}


async def url_retrieval_node(state: CuratorState) -> dict:
    urls = state.get("urls") or []
    if not urls:
        return {"source_documents": []}
    docs = await url_retrieval_tool(urls)
    return {"source_documents": docs}


async def file_retrieval_node(state: CuratorState) -> dict:
    files = state.get("files") or []
    if not files:
        return {"source_documents": []}
    loop = asyncio.get_event_loop()
    docs = await loop.run_in_executor(None, file_retrieval_tool, files)
    return {"source_documents": docs}


async def text_processor_node(state: CuratorState) -> dict:
    raw = state.get("raw_content") or ""
    if not raw.strip():
        return {"source_documents": []}
    loop = asyncio.get_event_loop()
    doc = await loop.run_in_executor(None, text_processor_tool, raw)
    return {"source_documents": [doc]}


async def content_aggregator_node(state: CuratorState) -> dict:
    docs = [d for d in (state.get("source_documents") or []) if d.content.strip()]
    aggregated = "\n\n".join(d.content for d in docs)
    return {
        "aggregated_content": aggregated,
        "total_chars": len(aggregated),
        "num_sources": len(docs),
    }


async def strategy_router_node(state: CuratorState) -> dict:
    total_chars = state.get("total_chars", 0)
    num_sources = state.get("num_sources", 0)

    if total_chars < 1000:
        strategy = "direct"
    elif num_sources <= 1:
        strategy = "qdrant"
    else:
        strategy = "neo4j"

    return {"strategy": strategy}


def _route_by_strategy(state: CuratorState) -> str:
    return state.get("strategy", "direct")


async def direct_llm_node(state: CuratorState) -> dict:
    llm = OllamaLLM(model="llama3", temperature=0.1)
    chain = _GENERATION_PROMPT | llm
    context = state.get("aggregated_content", "")
    try:
        raw = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: chain.invoke({"objective": state["learning_objective"], "context": context}),
        )
        return {"bundle_response": _parse_bundle(raw), "retrieved_context": context}
    except Exception as e:
        return {"error": f"PARSE_ERROR: {e}"}


async def qdrant_rag_node(state: CuratorState) -> dict:
    llm = OllamaLLM(model="llama3", temperature=0.1)
    chain = _GENERATION_PROMPT | llm
    try:
        loop = asyncio.get_event_loop()
        context = await loop.run_in_executor(
            None, build_qdrant_context,
            state.get("source_documents", []),
            state["learning_objective"],
        )
        if not context.strip():
            return {"error": "NO_RELEVANT_CONTEXT"}
        raw = await loop.run_in_executor(
            None,
            lambda: chain.invoke({"objective": state["learning_objective"], "context": context}),
        )
        return {"bundle_response": _parse_bundle(raw), "retrieved_context": context}
    except Exception as e:
        return {"error": str(e)}


async def neo4j_rag_node(state: CuratorState) -> dict:
    llm = OllamaLLM(model="llama3", temperature=0.1)
    chain = _GENERATION_PROMPT | llm
    try:
        loop = asyncio.get_event_loop()
        context = await loop.run_in_executor(
            None, build_neo4j_context,
            state.get("source_documents", []),
            state["learning_objective"],
        )
        if not context.strip():
            return {"error": "NO_RELEVANT_CONTEXT"}
        raw = await loop.run_in_executor(
            None,
            lambda: chain.invoke({"objective": state["learning_objective"], "context": context}),
        )
        return {"bundle_response": _parse_bundle(raw), "retrieved_context": context}
    except Exception as e:
        return {"error": str(e)}


async def faithfulness_evaluator_node(state: CuratorState) -> dict:
    if state.get("error"):
        return {"faithfulness_score": 0.0}
    context = state.get("retrieved_context", "")
    bundle = state.get("bundle_response") or {}
    loop = asyncio.get_event_loop()
    score = await loop.run_in_executor(
        None, faithfulness_evaluator, context, str(bundle)
    )
    return {"faithfulness_score": score}


# ─── Graph Assembly ───────────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(CuratorState)

    builder.add_node("intent_router", intent_router_node)
    builder.add_node("url_retriever", url_retrieval_node)
    builder.add_node("file_retriever", file_retrieval_node)
    builder.add_node("text_processor", text_processor_node)
    builder.add_node("content_aggregator", content_aggregator_node)
    builder.add_node("strategy_router", strategy_router_node)
    builder.add_node("direct_llm", direct_llm_node)
    builder.add_node("qdrant_rag", qdrant_rag_node)
    builder.add_node("neo4j_rag", neo4j_rag_node)
    builder.add_node("faithfulness_evaluator", faithfulness_evaluator_node)

    # Entry → parallel retrieval fan-out
    builder.add_edge(START, "intent_router")
    builder.add_edge("intent_router", "url_retriever")
    builder.add_edge("intent_router", "file_retriever")
    builder.add_edge("intent_router", "text_processor")

    # Parallel fan-in → aggregator (waits for all three)
    builder.add_edge("url_retriever", "content_aggregator")
    builder.add_edge("file_retriever", "content_aggregator")
    builder.add_edge("text_processor", "content_aggregator")

    builder.add_edge("content_aggregator", "strategy_router")

    # Conditional routing by strategy
    builder.add_conditional_edges(
        "strategy_router",
        _route_by_strategy,
        {
            "direct": "direct_llm",
            "qdrant": "qdrant_rag",
            "neo4j": "neo4j_rag",
        },
    )

    builder.add_edge("direct_llm", "faithfulness_evaluator")
    builder.add_edge("qdrant_rag", "faithfulness_evaluator")
    builder.add_edge("neo4j_rag", "faithfulness_evaluator")
    builder.add_edge("faithfulness_evaluator", END)

    return builder.compile()


curator_graph = build_graph()
