"""Gilda grounding blueprint."""

from typing import List, Optional

from fastapi import APIRouter, Request
from gilda.grounder import ScoredMatch
from pydantic import BaseModel, Field

__all__ = [
    "grounding_blueprint",
]

grounding_blueprint = APIRouter()


class GroundRequest(BaseModel):
    text: str = Field(..., description="The text to be grounded")
    context: Optional[str] = Field(description="Context around the text to be grounded")
    organisms: Optional[List[str]] = None
    namespaces: Optional[List[str]] = None


class GroundResult(BaseModel):
    url: str
    score: float
    prefix: str
    identifier: str
    status: str

    @classmethod
    def from_scored_match(cls, scored_match: ScoredMatch) -> "GroundResult":
        identifier = scored_match.term.id
        if identifier.startswith(scored_match.term.db):
            identifier = identifier[len(scored_match.term.db) + 1 :]
        return cls(
            url=scored_match.url,
            score=scored_match.score,
            prefix=scored_match.term.db,
            identifier=identifier,
            status=scored_match.term.status,
        )


class GroundResults(BaseModel):
    query: str
    results: List[GroundResult]


@grounding_blueprint.post("/ground", response_model=GroundResults)
def ground(ground_request: GroundRequest, request: Request) -> GroundResults:
    """Ground text with Gilda."""
    return _ground(
        request=request,
        text=ground_request.text,
        context=ground_request.context,
        organisms=ground_request.organisms,
        namespaces=ground_request.namespaces,
    )


@grounding_blueprint.get("/ground/<text>", response_model=GroundResults)
def ground_get(text: str, request: Request):
    """Ground text with Gilda."""
    return _ground(request=request, text=text)


def _ground(
    request: Request,
    text: str,
    context: Optional[str] = None,
    organisms: Optional[List[str]] = None,
    namespaces: Optional[List[str]] = None,
) -> GroundResults:
    results = request.app.state.grounder.ground(
        text, context=context, organisms=organisms, namespaces=namespaces
    )
    return GroundResults(
        query=text,
        results=[GroundResult.from_scored_match(scored_match) for scored_match in results],
    )
