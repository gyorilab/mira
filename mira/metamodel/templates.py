"""
Data models for metamodel templates.

Regenerate the JSON schema by running ``python -m mira.metamodel.templates``.
"""
__all__ = ["Concept", "Template", "Provenance", "ControlledConversion", "NaturalConversion"]

import json
import sys
from collections import ChainMap
from pathlib import Path
from typing import List, Mapping, Optional, Tuple

import pydantic
from pydantic import BaseModel, Field

HERE = Path(__file__).parent.resolve()
SCHEMA_PATH = HERE.joinpath("schema.json")


class Config(BaseModel):
    prefix_priority: List[str]


DEFAULT_CONFIG = Config(
    prefix_priority=[
        "ido",
    ],
)


class Concept(BaseModel):
    name: str = Field(..., description="The name of the concept.")
    identifiers: Mapping[str, str] = Field(default_factory=dict, description="A mapping of namespaces to identifiers.")
    context: Mapping[str, str] = Field(default_factory=dict, description="A mapping of context keys to values.")

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

    def is_equal_to(self, other: "Concept", with_context: bool = False):
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
            raise NotImplementedError(
                f"No comparison implemented for type {type(other)} with Concept"
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
        if (
            len(self.identifiers) > 0
            and len(other.identifiers) > 0
            and not self.get_curie() == other.get_curie()
        ):
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
            raise NotImplementedError(
                f"Comparison between Template and {type(other)} not implemented"
            )
        return templates_equal(self, other, with_context)


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
            f"Cannot compare template of type {templ.type} with template of "
            f"type {other_templ.type}"
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

    Parameters
    ----------
    refined_concept :
        The more detailed Concept
    other_concept :
        The less detailed Concept

    Returns
    -------
    :
        True if `refined_concept` truly is strictly more detailed than 
        `other_concept`, i.e. two identical Concept contexts can't be 
        refinements of each other.
    """
    # 1. Undecided/True if both don't have context
    if len(refined_concept.context) == 0 and len(other_concept.context) == 0:
        return True
    # 2. True if refined concept has context and the other one not
    elif len(refined_concept.context) > 0 and len(other_concept.context) == 0:
        return True
    # 3. False if refined concept does not have context and the other does
    elif len(refined_concept.context) == 0 and len(other_concept.context) > 0:
        return False
    # 4. Both have context
    else:
        # False if refined Concept has less (or equal) context
        if set(refined_concept.context.keys()).issubset(
                other_concept.context.keys()):
            return False

        # Other Concept context is a subset; check equality for the matches
        for other_context_key, other_context_value in other_concept.context.items():
            if refined_concept.context[other_context_key] != other_context_value:
                return False

    return True


def main():
    """Generate the JSON schema file."""
    schema = get_json_schema()
    SCHEMA_PATH.write_text(json.dumps(schema, indent=2))


if __name__ == "__main__":
    main()
