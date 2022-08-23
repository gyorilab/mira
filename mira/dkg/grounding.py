"""Gilda grounding blueprint."""

from typing import List, Optional

from gilda.grounder import ScoredMatch
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

__all__ = [
    "grounding_blueprint",
]

grounding_blueprint = APIRouter()


class GroundRequest(BaseModel):
    text: str = Field(..., description="The text to be grounded")
    context: Optional[str] = Field(description="Context around the text to be grounded")


class GroundResult(BaseModel):
    url: str
    score: float
    prefix: str
    identifier: str
    status: str

    @classmethod
    def from_scored_match(cls, scored_match: ScoredMatch) -> "GroundResult":
        return cls(
            url=scored_match.url,
            score=scored_match.score,
            prefix=scored_match.term.db,
            identifier=scored_match.term.id,
            status=scored_match.term.status,
        )


class GroundResults(BaseModel):
    query: str
    results: List[GroundResult]


@grounding_blueprint.post("/ground", response_model=GroundResults)
def ground(ground_request: GroundRequest, request: Request) -> GroundResults:
    """Ground text with Gilda."""
    return _ground(request=request, text=ground_request.text)


@grounding_blueprint.get("/ground/<text>", response_model=GroundResults)
def ground_get(text: str, request: Request):
    """Ground text with Gilda."""
    return _ground(request=request, text=text)


def _ground(request: Request, text: str) -> GroundResults:
    results = request.app.state.grounder.ground(text)
    return GroundResults(
        query=text,
        results=[GroundResult.from_scored_match(scored_match) for scored_match in results]
    )
