from pydantic import BaseModel, Field
from typing import Optional, List


class SourceDocument(BaseModel):
    source_type: str = Field(..., description="Type: 'url', 'file', or 'text'")
    source_id: str = Field(..., description="URL, filename, or 'inline'")
    content: str
    metadata: dict = {}


class LearningRequest(BaseModel):
    learning_objective: str = Field(..., description="The learning goal")
    content: Optional[str] = Field(None, description="Raw inline text")
    urls: List[str] = Field(default_factory=list, description="URLs to fetch content from")


class BundleResponse(BaseModel):
    curated_bundle: str = Field(..., description="Key concepts extracted from the content")
    dynamic_challenge: str = Field(..., description="Real-world scenario testing the objective")
    rationale: str = Field(..., description="Why this challenge fits the content and objective")
    required_output: str = Field(..., description="Exactly what the learner needs to submit")


class LearnerSubmission(BaseModel):
    session_id: str = Field(..., description="Session ID from the curation response")
    answer: str = Field(..., description="The learner's submitted answer")


class EvaluationResult(BaseModel):
    score: float = Field(..., description="Score from 0.0 to 1.0")
    feedback: str = Field(..., description="Detailed feedback on the answer")
    passed: bool = Field(..., description="Whether the learner passed")
