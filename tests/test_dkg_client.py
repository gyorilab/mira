from mira.dkg.client import search_priority_list, similarity_score
from mira.dkg.models import Synonym


class MockEntity:
    def __init__(self, id, name, synonyms=None):
        self.id = id
        self.name = name
        self.synonyms = synonyms if synonyms else []


def test_similarity_score():
    entity = MockEntity('ido:0000511', 'x')
    sim_score = similarity_score('x', entity)
    assert sim_score[0] == 0  # First entry in the priority list
    assert sim_score[1] == 1  # One word
    assert sim_score[2] == 0  # Exact name match to the query
    assert sim_score[3] == 1  # No synonyms

    entity2 = MockEntity('ncit:C71902', 'x')
    sim_score2 = similarity_score('x', entity2)
    assert 0 < sim_score2[0] < len(search_priority_list)  # In the list

    assert sorted([sim_score, sim_score2]) == [sim_score, sim_score2]

    entity3 = MockEntity(
        'foo:bar', 'infected population',
        [Synonym(value='infected individuals', type="skos:exactMatch")],
    )
    sim_score3 = similarity_score('infected', entity3)
    assert sim_score3[0] == len(search_priority_list)  # Not in the list
    assert sim_score3[3] < 1  # Has a partial synonym match
