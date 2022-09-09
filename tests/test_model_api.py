import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mira.dkg.model import model_blueprint
from mira.metamodel import Concept, ControlledConversion, NaturalConversion
from mira.modeling import TemplateModel, Model
from mira.modeling.petri import PetriNetModel

test_app = FastAPI()
test_app.include_router(model_blueprint, prefix="/api")


def sorted_json_str(json_dict) -> str:
    if isinstance(json_dict, str):
        return json_dict
    elif isinstance(json_dict, (int, float)):
        return str(json_dict)
    elif isinstance(json_dict, (tuple, list, set)):
        return "[%s]" % (",".join(sorted(sorted_json_str(s) for s in json_dict)))
    elif isinstance(json_dict, dict):
        return "{%s}" % (",".join(sorted(k + sorted_json_str(v) for k, v in json_dict.items())))
    else:
        raise TypeError("Invalid type: %s" % type(json_dict))


def _get_sir_templatemodel() -> TemplateModel:
    infected = Concept(name="infected population",
                       identifiers={"ido": "0000511"})
    susceptible = Concept(name="susceptible population",
                          identifiers={"ido": "0000514"})
    immune = Concept(name="immune population", identifiers={"ido": "0000592"})

    template1 = ControlledConversion(
        controller=infected,
        subject=susceptible,
        outcome=infected,
    )
    template2 = NaturalConversion(subject=infected, outcome=immune)
    return TemplateModel(templates=[template1, template2])


class TestModelApi(unittest.TestCase):

    def setUp(self) -> None:
        """Set up the test case"""
        self.client = TestClient(test_app)

    def test_petri(self):
        """Test the petrinet endpoint"""
        sir_model_templ = _get_sir_templatemodel()
        response = self.client.post("/api/to_petrinet", json=sir_model_templ.dict())
        self.assertEqual(response.status_code, 200, msg=response.content)
        resp_json_str = sorted_json_str(response.json())

        model = Model(sir_model_templ)
        petri_net = PetriNetModel(model)
        petri_net_json_str = sorted_json_str(petri_net.to_json())

        self.assertEqual(resp_json_str, petri_net_json_str)
