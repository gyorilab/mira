from ..metamodel import Concept

__all__ = [
    "susceptible",
    "infected",
    "recovered",
    "exposed",
    "dead",
]

susceptible = Concept(name="susceptible_population", identifiers={"ido": "0000514"})
infected = Concept(name="infected_population", identifiers={"ido": "0000511"})
recovered = Concept(name="immune_population", identifiers={"ido": "0000592"})
exposed = susceptible.with_context(property="ido:0000597")
dead = Concept(name="dead", identifiers={"ncit": "C28554"})
