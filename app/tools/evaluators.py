import json
import re
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from app.models import EvaluationResult, ImprovementPoint, ImprovedSolution


def _sanitize_json_strings(s: str) -> str:
    """Escape literal control characters inside JSON string values."""
    result = []
    in_string = False
    escaped = False
    for ch in s:
        if escaped:
            result.append(ch)
            escaped = False
        elif ch == '\\' and in_string:
            result.append(ch)
            escaped = True
        elif ch == '"':
            result.append(ch)
            in_string = not in_string
        elif in_string and ch == '\n':
            result.append('\\n')
        elif in_string and ch == '\r':
            result.append('\\r')
        elif in_string and ch == '\t':
            result.append('\\t')
        else:
            result.append(ch)
    return ''.join(result)


def _extract_json(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in LLM output: {raw[:200]}")
    return json.loads(_sanitize_json_strings(match.group()))


def faithfulness_evaluator(context: str, response: str) -> float:
    llm = OllamaLLM(model="llama3", temperature=0)
    prompt = PromptTemplate(
        template="""You are a faithfulness judge. Rate how faithfully the AI response stays within the source context.

Source Context:
{context}

AI Response:
{response}

Respond with ONLY a JSON object — no markdown, no preamble:
{{"score": <float 0.0-1.0>, "reason": "<one sentence>"}}""",
        input_variables=["context", "response"],
    )
    try:
        raw = (prompt | llm).invoke({"context": context[:3000], "response": response[:2000]})
        parsed = _extract_json(raw)
        return float(parsed.get("score", 0.7))
    except Exception:
        return 0.7


def answer_evaluator(challenge: str, required_output: str, learner_answer: str) -> EvaluationResult:
    llm = OllamaLLM(model="llama3", temperature=0)
    prompt = PromptTemplate(
        template="""You are a strict instructor evaluating a learner's response.

Challenge:
{challenge}

Required criteria — the answer MUST address ALL of these:
{required_output}

Learner's answer:
{answer}

Evaluate in two steps:
1. List every criterion from "Required criteria" that is MISSING or only partially addressed in the learner's answer.
2. Score using this rubric — be strict, do not round up:
   - 0.9–1.0: every criterion fully met, answer is complete and accurate
   - 0.7–0.8: exactly 1 minor criterion missing or slightly imprecise
   - 0.5–0.6: 2 criteria missing or 1 core criterion only partially addressed
   - 0.2–0.4: most criteria missing or answer is mostly shallow
   - 0.0–0.1: does not address the challenge at all

If ANY required criterion is absent, the score must be 0.8 or lower.

Respond with ONLY a JSON object — no markdown, no preamble:
{{"score": <float 0.0-1.0>, "feedback": "<2-3 sentences: what was good, what was missing, how to improve>", "passed": <true if score >= 0.7>}}""",
        input_variables=["challenge", "required_output", "answer"],
    )
    try:
        raw = (prompt | llm).invoke({
            "challenge": challenge,
            "required_output": required_output,
            "answer": learner_answer,
        })
        parsed = _extract_json(raw)
        score = float(parsed.get("score", 0.0))
        return EvaluationResult(
            score=score,
            feedback=parsed.get("feedback", "No feedback provided."),
            passed=bool(parsed.get("passed", score >= 0.7)),
        )
    except Exception as e:
        return EvaluationResult(
            score=0.0,
            feedback=f"Evaluation could not be completed: {str(e)}",
            passed=False,
        )


def improve_answer(challenge: str, required_output: str, learner_answer: str) -> ImprovedSolution:
    llm = OllamaLLM(model="llama3", temperature=0.3)
    prompt = PromptTemplate(
        template="""You are an expert instructor. Improve the learner's answer to the challenge below.

Challenge:
{challenge}

What a good answer must include:
{required_output}

Learner's answer:
{answer}

Write a complete improved answer that fully satisfies all requirements. Then list 2-4 specific improvements you made.

Respond with ONLY a JSON object — no markdown, no preamble:
{{"improved_answer": "<complete improved answer text>", "improvements": [{{"point": "<what was improved>", "reason": "<why this matters>"}}]}}""",
        input_variables=["challenge", "required_output", "answer"],
    )
    try:
        raw = (prompt | llm).invoke({
            "challenge": challenge,
            "required_output": required_output,
            "answer": learner_answer,
        })
        parsed = _extract_json(raw)
        improvements = [
            ImprovementPoint(point=i.get("point", ""), reason=i.get("reason", ""))
            for i in parsed.get("improvements", [])
        ]
        return ImprovedSolution(
            improved_answer=parsed.get("improved_answer", ""),
            improvements=improvements,
        )
    except Exception as e:
        return ImprovedSolution(
            improved_answer="Could not generate an improved solution.",
            improvements=[ImprovementPoint(point="Error", reason=str(e))],
        )
