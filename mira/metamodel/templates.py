"""
Data models for metamodel templates.

Regenerate the JSON schema by running ``python -m mira.metamodel.templates``.
"""
__all__ = ["Concept", "Template", "Provenance", "ControlledConversion", "NaturalConversion"]

import json
import logging
import sys
from collections import ChainMap
from pathlib import Path
from typing import List, Mapping, Optional, Tuple

import pydantic
from pydantic import BaseModel, Field

from mira.dkg.client import Neo4jClient

HERE = Path(__file__).parent.resolve()
SCHEMA_PATH = HERE.joinpath("schema.json")


logger = logging.getLogger(__name__)


class Config(BaseModel):
    prefix_priority: List[str]


DEFAULT_CONFIG = Config(
    prefix_priority=[
        "ido",
    ],
)


class Concept(BaseModel):
    name: str = Field(..., description="The name of the concept.")
    identifiers: Mapping[str, str] = Field(
        default_factory=dict, description="A mapping of namespaces to identifiers."
    )
    context: Mapping[str, str] = Field(
        default_factory=dict, description="A mapping of context keys to values."
    )

    def with_context(self, **context) -> "Concept":
        """Return this concept with extra context."""
        return Concept(
            name=self.name,
            identifiers=self.identifiers,
            context=dict(ChainMap(context, self.context)),
        )

    def get_curie(self, config: Optional[Config] = None) -> Tuple[str, str]:
        """Get the priority prefix/identifier pair for this concept."""
        if config is None:
            config = DEFAULT_CONFIG
        for prefix in config.prefix_priority:
            identifier = self.identifiers.get(prefix)
            if identifier:
                return prefix, identifier
        return sorted(self.identifiers.items())[0]

    def get_key(self, config: Optional[Config] = None):
        return (
            self.get_curie(config=config),
            tuple(sorted(self.context.items())),
        )

    def is_equal_to(self, other: "Concept", with_context: bool = False) -> bool:
        """Test for equality between concepts

        Parameters
        ----------
        other :
            Other Concept to test equality with
        with_context :
            If True, do not consider the two Concepts equal unless they also
            have exactly the same context. If there is no context,
            ``with_context`` has no effect.

        Returns
        -------
        :
            True if ``other`` is the same Concept as this one
        """
        if not isinstance(other, Concept):
            raise TypeError(
                f"Cannot check equality between instances {type(other)} and Concept."
            )

        # With context
        if with_context:
            # Check that the same keys appear in both
            if set(self.context.keys()) != set(other.context.keys()):
                return False

            # Check that the values are the same
            for k1, v1 in self.context.items():
                if v1 != other.context[k1]:
                    return False

        # Check that they are grounded to the same identifier
        if len(self.identifiers) > 0 and len(other.identifiers) > 0:
            if self.get_curie() != other.get_curie():
                return False
            else:
                pass
        # If either or both are ungrounded -> can't know -> False
        else:
            return False

        return True

    def refinement_of(
        self, other: "Concept", dkg_client: Neo4jClient, with_context: bool = False
    ) -> bool:
        """Check if this Concept is a more detailed version of another"""
        # Check context subset; either both concepts have context, or this
        # concept has context and the other, less detailed, concept does not
        if not isinstance(other, Concept):
            raise TypeError(f"Cannot check refinement between {type(other)} and Concept")

        if with_context:
            if not assert_concept_context_refinement(refined_concept=self, other_concept=other):
                return False

        # Check if this concept is a child term to other?
        if len(self.identifiers) > 0 and len(other.identifiers) > 0:
            # Check if other is a parent of this concept
            this_curie = ":".join(self.get_curie())
            other_curie = ":".join(other.get_curie())
            res = dkg_client.query_relations(
                source_curie=this_curie, relation_type="rdfs:subClassOf", target_curie=other_curie
            )
            if len(res) == 0:
                return False

        # Any of them are ungrounded -> cannot know if there is a refinement
        # -> return False
        elif len(self.identifiers) == 0 or len(other.identifiers) == 0:
            return False

        return True


class Template(BaseModel):
    @classmethod
    def from_json(cls, data) -> "Template":
        template_type = data.pop("type")
        stmt_cls = getattr(sys.modules[__name__], template_type)
        return stmt_cls(**data)

    def is_equal_to(self, other: "Template", with_context: bool = False) -> bool:
        if not isinstance(other, Template):
            raise TypeError(
                f"Comparison between Template and {type(other)} not implemented"
            )
        return templates_equal(self, other, with_context)

    def refinement_of(self, other: "Template", dkg_client: Neo4jClient) -> bool:
        """Check if this template is a more detailed version of another"""
        if not isinstance(other, Template):
            raise TypeError(
                f"Only refinement check between Template instances possible, "
                f"got instance of type {type(other)}"
            )

        if self.type != other.type:
            return False

        for field_name in self.__fields__:
            this_value = getattr(self, field_name)

            # Skip 'type'
            if field_name == "type":
                continue

            # Check refinement for any attribute that is a Concept; this is
            # strict in the sense that unless every concept of this template is a
            # refinement of the other, the Template as a whole cannot be
            # considered a refinement
            elif isinstance(this_value, Concept):
                other_concept = getattr(other, field_name)
                if not this_value.refinement_of(other_concept, dkg_client):
                    return False

            # todo: Handle Provenance
            elif isinstance(this_value, List):
                if isinstance(this_value[0], Provenance):
                    pass
                else:
                    logger.warning(f"Unhandled type List[{type(this_value[0])}]")

            else:
                logger.warning(f"Unhandled type {type(this_value)}")

        return True


class Provenance(BaseModel):
    pass


class ControlledConversion(Template):
    type: str = Field("ControlledConversion", const=True)
    controller: Concept
    subject: Concept
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)

    def with_context(self, **context) -> "ControlledConversion":
        return self.__class__(
            type=self.type,
            subject=self.subject.with_context(**context),
            outcome=self.outcome.with_context(**context),
            controller=self.controller.with_context(**context),
            provenance=self.provenance,
        )

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.subject.get_key(config=config),
            self.controller.get_key(config=config),
            self.outcome.get_key(config=config),
        )


class NaturalConversion(Template):
    type: str = Field("NaturalConversion", const=True)
    subject: Concept
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)

    def with_context(self, **context) -> "NaturalConversion":
        return self.__class__(
            type=self.type,
            subject=self.subject.with_context(**context),
            outcome=self.outcome.with_context(**context),
            provenance=self.provenance,
        )

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.subject.get_key(config=config),
            self.outcome.get_key(config=config),
        )


def get_json_schema():
    """Get the JSON schema for MIRA."""
    rv = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://raw.githubusercontent.com/indralab/mira/main/mira/metamodel/schema.json",
    }
    rv.update(
        pydantic.schema.schema(
            [Concept, Template, NaturalConversion, ControlledConversion],
            title="MIRA Metamodel Template Schema",
            description="MIRA metamodel templates give a high-level abstraction of modeling appropriate for many domains.",
        )
    )
    return rv


def templates_equal(templ: Template, other_templ: Template, with_context: bool) -> bool:
    if templ.type != other_templ.type:
        raise TypeError(
            f"Cannot compare Template type {templ.type} with Template type {other_templ.type}"
        )

    other_dict = other_templ.__dict__
    for key, value in templ.__dict__.items():
        # Already checked type
        if key == "type":
            continue

        if isinstance(value, Concept):
            other_concept: Concept = other_dict[key]
            if not value.is_equal_to(other_concept, with_context=with_context):
                return False

        elif isinstance(value, list):
            if not all(i1 == i2 for i1, i2 in zip(value, other_dict[key])):
                return False
        else:
            raise NotImplementedError(
                f"No comparison implemented for type {type(value)} for Template"
            )
    return True


def assert_concept_context_refinement(refined_concept: Concept, other_concept: Concept) -> bool:
    """Check if one Concept's context is a refinement of another Concept's

    Special case:
    - Both contexts are empty: True

    Parameters
    ----------
    refined_concept :
        The assumed *more* detailed Concept
    other_concept :
        The assumed *less* detailed Concept

    Returns
    -------
    :
        True if the Concept `refined_concept` truly is strictly more detailed
        than `other_concept`
    """
    refined_context = refined_concept.context
    other_context = other_concept.context
    # 1. Undecided if both don't have context -> True so that other factors
    #    outside of context can decide
    if len(refined_context) == 0 and len(other_context) == 0:
        return True
    # 2. True if refined concept has context and the other one not
    elif len(refined_context) > 0 and len(other_context) == 0:
        return True
    # 3. False if refined concept does not have context and the other does
    elif len(refined_context) == 0 and len(other_context) > 0:
        return False
    # 4. Both have context
    else:
        # 1. Exactly equal context keys -> False
        # 2. False if refined Concept context is a subset of other context
        #
        # NOTE: issubset is not strict, i.e. is True for equal sets, therefore
        # we need to check for refined.issubset(other) first to be sure that
        # cases 1. and 2. are ruled out when 3. is evaluated
        if set(refined_context.keys()).issubset(other_context.keys()):
            return False

        # 3. Other Concept context is a subset; check equality for the matches
        elif set(other_context.keys()).issubset(refined_context):
            for other_context_key, other_context_value in other_context.items():
                if refined_context[other_context_key] != other_context_value:
                    return False

        # 4. Both Concepts have context, but they are different -> cannot be a
        #    refinement -> False
        elif set(other_context.keys()).symmetric_difference(set(refined_context.keys())):
            return False

        # Can't come up with what other situation would arise
        else:
            # FixMe: Remove before PR
            raise ValueError("Unhandled logic, missing at least one logical option")

    return True


def main():
    """Generate the JSON schema file."""
    schema = get_json_schema()
    SCHEMA_PATH.write_text(json.dumps(schema, indent=2))


if __name__ == "__main__":
    main()
