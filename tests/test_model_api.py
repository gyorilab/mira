import json
import tempfile
import unittest
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mira.dkg.model import model_blueprint#, ToGrometQuery
from mira.metamodel import Concept, ControlledConversion, NaturalConversion
from mira.modeling import Model
from mira.metamodel.templates import TemplateModel
# from mira.modeling.gromet_model import GrometModel
from mira.modeling.ops import stratify
from mira.modeling.petri import PetriNetModel
from mira.modeling.viz import GraphicalModel

test_app = FastAPI()
test_app.include_router(model_blueprint, prefix="/api")


def sorted_json_str(json_dict, ignore_key=None) -> str:
    if isinstance(json_dict, str):
        return json_dict
    elif isinstance(json_dict, (int, float)):
        return str(json_dict)
    elif isinstance(json_dict, (tuple, list, set)):
        return "[%s]" % (",".join(sorted(sorted_json_str(s, ignore_key) for s in json_dict)))
    elif isinstance(json_dict, dict):
        if ignore_key is not None:
            dict_gen = (
                k + sorted_json_str(v, ignore_key) for k, v in json_dict.items() if k != ignore_key
            )
        else:
            dict_gen = (k + sorted_json_str(v, ignore_key) for k, v in json_dict.items())
        return "{%s}" % (",".join(sorted(dict_gen)))
    elif json_dict is None:
        return json.dumps(json_dict)
    else:
        raise TypeError("Invalid type: %s" % type(json_dict))


def _get_sir_templatemodel() -> TemplateModel:
    infected = Concept(name="infected population", identifiers={"ido": "0000511"})
    susceptible = Concept(name="susceptible population", identifiers={"ido": "0000514"})
    immune = Concept(name="immune population", identifiers={"ido": "0000592"})

    template1 = ControlledConversion(
        controller=infected,
        subject=susceptible,
        outcome=infected,
    )
    template2 = NaturalConversion(subject=infected, outcome=immune)
    return TemplateModel(templates=[template1, template2])


class TestModelApi(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        """Set up the test case"""
        self.client = TestClient(test_app)
        self.temp_files: List[Path] = []

    def tearDown(self) -> None:
        for path in self.temp_files:
            path.unlink(missing_ok=True)

    def _get_tmp_file(self, file_ending: str):
        tdp = Path(tempfile.gettempdir())
        tmpfile = tdp.joinpath(f"{uuid.uuid4()}.{file_ending}")
        self.temp_files.append(tmpfile)
        return tmpfile

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

    @unittest.skip("Skipping GroMEt tests")
    def test_gromet(self):
        """Test the gromet endpoint"""
        sir_model_templ = _get_sir_templatemodel()
        model_name = "SIR"
        name = "sir_model_123"
        query_model = ToGrometQuery(
            model_name=model_name, name=name, template_model=sir_model_templ
        )
        response = self.client.post("/api/to_gromet", json=query_model.dict())
        self.assertEqual(200, response.status_code)
        resp_json_str = sorted_json_str(response.json(), ignore_key="timestamp")

        sir_model = Model(query_model.template_model)
        gm = GrometModel(sir_model, model_name=model_name, name=name)
        gromet_json_str = sorted_json_str(asdict(gm.gromet_model), ignore_key="timestamp")

        self.assertEqual(gromet_json_str, resp_json_str)

    def test_stratify(self):
        """Test the stratification endpoint"""
        sir_templ_model = _get_sir_templatemodel()
        key = "city"
        strata = ["geonames:5128581", "geonames:4930956"]
        query_json = {
            "template_model": sir_templ_model.dict(),
            "key": key,
            "strata": strata,
        }
        response = self.client.post("/api/stratify", json=query_json)
        self.assertEqual(200, response.status_code)
        resp_json_str = sorted_json_str(response.json())

        strat_templ_model = stratify(template_model=sir_templ_model, key=key, strata=set(strata))
        strat_str = sorted_json_str(strat_templ_model.dict())

        self.assertEqual(strat_str, resp_json_str)

        # Test directed True
        query_json = {
            "template_model": sir_templ_model.dict(),
            "key": key,
            "strata": strata,
            "directed": True,
        }
        response = self.client.post("/api/stratify", json=query_json)
        self.assertEqual(200, response.status_code)
        resp_json_str = sorted_json_str(response.json())

        strat_templ_model = stratify(
            template_model=sir_templ_model,
            key=key,
            strata=set(strata),
            directed=query_json["directed"],
        )
        strat_str = sorted_json_str(strat_templ_model.dict())

        self.assertEqual(strat_str, resp_json_str)

        # todo: test for conversion_cls == "controlled_conversions" when
        #  that works for stratify

    def test_to_dot_file(self):
        sir_templ_model = _get_sir_templatemodel()
        response = self.client.post("/api/viz/to_dot_file", json=sir_templ_model.dict())
        self.assertEqual(200, response.status_code)
        self.assertIn(
            "text/vnd.graphviz",
            response.headers["content-type"],
            f"Got content-type {response.headers['content-type']}",
        )
        gm = GraphicalModel(Model(sir_templ_model))
        tmpf = self._get_tmp_file(file_ending="gv")
        gm.write(path=tmpf, format="dot")
        with open(tmpf, "r") as fi:
            file_str = fi.read()
        self.assertEqual(file_str, response.text)

    def test_to_graph_image(self):
        sir_templ_model = _get_sir_templatemodel()
        response = self.client.post("/api/viz/to_image", json=sir_templ_model.dict())
        self.assertEqual(200, response.status_code)
        self.assertIn(
            "image/png",
            response.headers["content-type"],
            f"Got content-type {response.headers['content-type']}",
        )
        gm = GraphicalModel(Model(sir_templ_model))
        tmpf = self._get_tmp_file(file_ending="png")
        gm.write(path=tmpf, format="png")
        with open(tmpf, 'rb') as fi:
            file_str = fi.read()
        self.assertEqual(file_str, response.content)
