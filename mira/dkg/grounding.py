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

    text: str = Field(..., description="The text to be grounded", examples=["Infected Population"])
    context: Optional[str] = Field(
        None,
        description="Context around the text to be grounded",
        examples=["The infected population increased over the past month"],
    )
    namespaces: Optional[List[str]] = Field(
        None,
        description="A list of namespaces to filter groundings to.",
        examples=[["do", "mondo", "ido"]],
    )


class GroundResult(BaseModel):
    """The results returned from a grounding request."""

    url: str = Field(
        ...,
        description="A URL that resolves the term to an external web service",
        examples=[f"{BR_BASE}/ido:0000511"],
    )
    score: float = Field(
        ..., description="The matching score calculated by Gilda", ge=0.0, le=1.0, examples=[0.78]
    )
    prefix: str = Field(
        ...,
        description="The prefix corresponding to the ontology/database from which the term comes",
        examples=["ido"],
    )
    identifier: str = Field(
        ...,
        description="The local unique identifier for the term in the ontology/database denoted by the prefix",
        examples=["0000511"],
    )
    curie: str = Field(
        ...,
        description="The compact URI that combines the prefix and local identifier.",
        examples=["ido:0000511"],
    )
    name: str = Field(
        ..., description="The standard entity name for the term", examples=["infected population"]
    )
    status: str = Field(..., description="The match status, e.g., name, synonym", examples=["name"])

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


GROUNDING_RESPONSE_DESCRIPTION = (
    "Successful grounding returns an object containing a copy of "
    "the grounding request as well as a list of grounding results."
)


@grounding_blueprint.post(
    "/ground",
    response_model=GroundResults,
    response_model_exclude_unset=True,
    response_description=GROUNDING_RESPONSE_DESCRIPTION,
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
                "context": {
                    "summary": "An example with text and context",
                    "description": "The context field can be included to provide context for the grounding mechanism to better disambiguate the term provided",
                    "value": {
                        "text": "infected population",
                        "context": "The infected population increased the past month.",
                    },
                },
            },
        },
    ),
):
    """Ground text with Gilda."""
    return _ground(request=request, ground_request=ground_request)


@grounding_blueprint.get(
    "/ground/{text}",
    response_model=GroundResults,
    response_model_exclude_unset=True,
    response_description=GROUNDING_RESPONSE_DESCRIPTION,
    tags=["grounding"],
)
def ground_get(
    request: Request,
    text: str = Path(
        ...,
        description="The text to be grounded. Warning: grounding does not work well for "
        "substring matches, i.e., if searching only for 'infected'. In these "
        "cases, using the search API is more appropriate.",
        examples=["Infected Population"],
    ),
):
    """Ground text with Gilda."""
    return _ground(request=request, ground_request=GroundRequest(text=text))


@grounding_blueprint.post(
    "/ground_list",
    response_model=List[GroundResults],
    response_model_exclude_unset=True,
    response_description="Successful grounding returns a list of grounding results.",
    tags=["grounding"],
)
def ground_list(
    request: Request,
    ground_requests: List[GroundRequest] = Body(
        ...,
        examples={
            "simple": {
                "summary": "An example with only text",
                "description": "This example only includes a text query. Note that it is a capitalization variant of the actual IDO term, which uses lowercase.",
                "value": [
                    {
                        "text": "Infected Population",
                    },
                    {
                        "text": "Breast Cancer",
                    },
                    {
                        "text": "Myocardial Infarction",
                    },
                ],
            },
            "filtered": {
                "summary": "An example with text and a namespace filter",
                "description": "The namespaces field can be included to filter results based on terms coming from namespaces with the given prefixes",
                "value": [
                    {
                        "text": "infected population",
                        "namespaces": ["ido", "cido"],
                    },
                    {
                        "text": "cancer",
                        "namespaces": ["do"],
                    },
                    {
                        "text": "heart attack",
                        "namespaces": ["mondo"],
                    },
                ],
            },
        },
    ),
):
    """
    Ground a list of texts with Gilda.

    Returns a list of grounding results. Each element corresponds to the result for the corresponding
    input text. The results for each input text are returned in the same format as for the 'ground' endpoint.
    """
    return [_ground(request=request, ground_request=gr) for gr in ground_requests]




def _ground(
    *,
    request: Request,
    ground_request: GroundRequest,
) -> GroundResults:
    results = request.app.state.grounder.ground(
        ground_request.text,
        context=ground_request.context,
        namespaces=ground_request.namespaces,
    )
    return GroundResults(
        request=ground_request,
        results=[GroundResult.from_scored_match(scored_match) for scored_match in results],
    )
