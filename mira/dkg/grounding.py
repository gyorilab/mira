"""Gilda grounding blueprint."""

from typing import List, Optional

from fastapi import APIRouter, Body, Path, Request
from gilda.grounder import ScoredMatch
from pydantic import BaseModel, Field

__all__ = [
    "grounding_blueprint",
]

grounding_blueprint = APIRouter()

BR_BASE = "https://bioregistry.io"


class GroundRequest(BaseModel):
    """A model representing the parameters to be passed to :func:`gilda.ground` for grounding."""

    text: str = Field(..., description="The text to be grounded", example="Infected Population")
    # context: Optional[str] = Field(description="Context around the text to be grounded")
    namespaces: Optional[List[str]] = Field(
        description="A list of namespaces to filter groundings to.", example=["do", "mondo", "ido"]
    )


class GroundResult(BaseModel):
    """The results returned from a grounding request."""

    url: str = Field(
        ...,
        description="A URL that resolves the term to an external web service",
        example=f"{BR_BASE}/ido:0000511",
    )
    score: float = Field(
        ..., description="The matching score calculated by Gilda", ge=0.0, le=1.0, example=0.78
    )
    prefix: str = Field(
        ...,
        description="The prefix corresponding to the ontology/database from which the term comes",
        example="ido",
    )
    identifier: str = Field(
        ...,
        description="The local unique identifier for the term in the ontology/database denoted by the prefix",
        example="0000511",
    )
    curie: str = Field(
        ...,
        description="The compact URI that combines the prefix and local identifier.",
        example="ido:0000511",
    )
    name: str = Field(
        ..., description="The standard entity name for the term", example="infected population"
    )
    status: str = Field(..., description="The match status, e.g., name, synonym", example="name")

    @classmethod
    def from_scored_match(cls, scored_match: ScoredMatch) -> "GroundResult":
        identifier = scored_match.term.id
        prefix = scored_match.term.db
        if identifier.startswith(prefix):
            identifier = identifier[len(prefix) + 1 :]
        return cls(
            url=f"{BR_BASE}/{prefix}:{identifier}",
            score=round(scored_match.score, 2),
            prefix=prefix,
            identifier=identifier,
            curie=f"{prefix}:{identifier}",
            name=scored_match.term.entry_name,
            status=scored_match.term.status,
        )


class GroundResults(BaseModel):
    """A grouped set of results."""

    request: GroundRequest = Field(..., description="A request for grounding")
    results: List[GroundResult] = Field(..., description="A list of grounding results")


@grounding_blueprint.post(
    "/ground",
    response_model=GroundResults,
    response_model_exclude_unset=True,
    tags=["grounding"],
)
def ground(
    request: Request,
    ground_request: GroundRequest = Body(
        ...,
        # See https://fastapi.tiangolo.com/tutorial/schema-extra-example/#body-with-multiple-examples
        examples={
            "simple": {
                "summary": "An example with only text",
                "description": "This example only includes a text query. Note that it is a capitalization variant of the actual IDO term, which uses lowercase.",
                "value": {
                    "text": "Infected Population",
                },
            },
            "filtered": {
                "summary": "An example with text and a namespace filter",
                "description": "The namespaces field can be included to filter results based on terms coming from namespaces with the given prefixes",
                "value": {
                    "text": "infected population",
                    "namespaces": ["ido", "cido"],
                },
            },
        },
    ),
):
    """Ground text with Gilda."""
    return _ground(request=request, ground_request=ground_request)


@grounding_blueprint.get("/ground/{text}", response_model=GroundResults, tags=["grounding"])
def ground_get(
    request: Request,
    text: str = Path(
        ...,
        description="The text to be grounded. Warning: grounding does not work well for "
        "substring matches, i.e., if searching only for 'infected'. In these "
        "cases, using the search API is more appropriate.",
        example="Infected Population",
    ),
):
    """Ground text with Gilda."""
    return _ground(request=request, ground_request=GroundRequest(text=text))


def _ground(
    *,
    request: Request,
    ground_request: GroundRequest,
) -> GroundResults:
    results = request.app.state.grounder.ground(
        ground_request.text,
        # context=ground_request.context,
        namespaces=ground_request.namespaces,
    )
    return GroundResults(
        request=ground_request,
        results=[GroundResult.from_scored_match(scored_match) for scored_match in results],
    )
