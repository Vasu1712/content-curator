import json
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from app.models import EvaluationResult


def faithfulness_evaluator(context: str, response: str) -> float:
    llm = OllamaLLM(model="llama3", temperature=0)
    prompt = PromptTemplate(
        template="""Rate the faithfulness of the AI response to the source context on a scale 0.0-1.0.
A faithful response only uses facts from the source context.

Source Context:
{context}

AI Response:
{response}

Respond with ONLY valid JSON: {{"score": <float 0.0-1.0>, "reason": "<brief explanation>"}}""",
        input_variables=["context", "response"],
    )
    try:
        result = (prompt | llm).invoke({"context": context[:3000], "response": response[:2000]})
        parsed = json.loads(result.strip())
        return float(parsed.get("score", 0.7))
    except Exception:
        return 0.7


def answer_evaluator(challenge: str, required_output: str, learner_answer: str) -> EvaluationResult:
    llm = OllamaLLM(model="llama3", temperature=0)
    prompt = PromptTemplate(
        template="""Evaluate the learner's answer against the challenge requirements.

Challenge:
{challenge}

Required Output:
{required_output}

Learner's Answer:
{answer}

Be constructive and fair. Respond with ONLY valid JSON:
{{"score": <float 0.0-1.0>, "feedback": "<detailed feedback>", "passed": <true if score >= 0.6>}}""",
        input_variables=["challenge", "required_output", "answer"],
    )
    try:
        result = (prompt | llm).invoke({
            "challenge": challenge,
            "required_output": required_output,
            "answer": learner_answer,
        })
        parsed = json.loads(result.strip())
        score = float(parsed.get("score", 0.0))
        return EvaluationResult(
            score=score,
            feedback=parsed.get("feedback", "No feedback provided."),
            passed=bool(parsed.get("passed", score >= 0.6)),
        )
    except Exception as e:
        return EvaluationResult(
            score=0.0,
            feedback=f"Evaluation could not be completed: {str(e)}",
            passed=False,
        )
