from typing import List, Mapping


class Concept:
    def __init__(self, name: str, identifiers: List[Mapping[str, str]],
                 context: List[Mapping[str, str]]):
        self.name = name
        self.identifiers = identifiers
        self.context = context

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
    def __init__(self, controller: Concept, subject: Concept, outcome: Concept,
                 provenance: List[Provenance]):
        self.controller = controller
        self.subject = subject
        self.outcome = outcome

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