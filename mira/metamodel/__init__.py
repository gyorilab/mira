__all__ = ["Concept", "Template", "Provenance", "ControlledConversion"]

from typing import List, Mapping, Optional


class Concept:
    def __init__(self, name: str,
                 identifiers: Optional[Mapping[str, str]] = None,
                 context: Optional[Mapping[str, str]] = None):
        self.name = name
        self.identifiers = identifiers if identifiers else {}
        self.context = context if context else {}

    def to_json(self):
        return {
            "name": self.name,
            "identifiers": self.identifiers,
            "context": self.context,
        }

    @classmethod
    def from_json(cls, json_dict):
        return cls(name=json_dict["name"],
                   identifiers=json_dict["identifiers"],
                   context=json_dict["context"])


class Template:
    pass


class Provenance:
    pass


class ControlledConversion(Template):
    def __init__(self, controller: Concept,
                 subject: Concept,
                 outcome: Concept,
                 provenance: Optional[List[Provenance]] = None):
        self.controller = controller
        self.subject = subject
        self.outcome = outcome
        self.provenance = provenance if provenance else []

    def to_json(self):
        return {
            "type": "ControlledConversion",
            "controller": self.controller.to_json(),
            "subject": self.subject.to_json(),
            "outcome": self.outcome.to_json(),
        }

    @classmethod
    def from_json(cls, json_dict: Mapping[str, str]):
        return cls(
            controller=Concept.from_json(json_dict["controller"]),
            subject=Concept.from_json(json_dict["subject"]),
            outcome=Concept.from_json(json_dict["outcome"]),
        )


class NaturalConversion(Template):
    def __init__(self, subject: Concept, outcome: Concept,
                 provenance: Optional[List[Provenance]] = None):
        self.subject = subject
        self.outcome = outcome
        self.provenance = provenance if provenance else []

    def to_json(self):
        return {
            "type": "NaturalConversion",
            "subject": self.subject.to_json(),
            "outcome": self.outcome.to_json(),
        }

    @classmethod
    def from_json(cls, json_dict: Mapping[str, str]):
        return cls(
            subject=Concept.from_json(json_dict["subject"]),
            outcome=Concept.from_json(json_dict["outcome"]),
        )