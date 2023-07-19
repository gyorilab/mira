import copy
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import List, Union

import sympy
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mira.examples.sir import sir_parameterized, sir, \
    sir_parameterized_init, sir_init_val_norm
from mira.dkg.model import model_blueprint, ModelComparisonResponse
from mira.dkg.api import RelationQuery
from mira.dkg.web_client import is_ontological_child_web, get_relations_web
from mira.metamodel import Concept, ControlledConversion, NaturalConversion, \
    TemplateModel, Distribution, Annotations, Time, Observable
from mira.metamodel.ops import stratify
from mira.metamodel.templates import SympyExprStr
from mira.metamodel.comparison import TemplateModelComparison, \
    TemplateModelDelta, RefinementClosure, ModelComparisonGraphdata
from mira.modeling import Model
from mira.modeling.askenet.petrinet import AskeNetPetriNetModel
from mira.modeling.bilayer import BilayerModel
from mira.modeling.petri import PetriNetModel, PetriNetResponse
from mira.modeling.viz import GraphicalModel
from mira.sources.askenet.petrinet import template_model_from_askenet_json
from mira.sources.bilayer import template_model_from_bilayer
from mira.sources.biomodels import get_sbml_model
from mira.sources.petri import template_model_from_petri_json
from mira.sources.sbml import template_model_from_sbml_string


def sorted_json_str(json_dict, ignore_key=None, skip_empty: bool = False) -> str:
    """Create a sorted json string from a json compliant object

    Parameters
    ----------
    json_dict :
        A json compliant object
    ignore_key :
        Key to ignore in dictionaries
    skip_empty :
        Skip values that evaluates to False, except for 0, 0.0, and False

    Returns
    -------
    :
        A sorted string representation of the json_dict object
    """
    if isinstance(json_dict, str):
        if skip_empty and not json_dict:
            return ""
        return json_dict
    elif isinstance(json_dict, (int, float, SympyExprStr)):
        if skip_empty and not json_dict and json_dict != 0 and json_dict != 0.0:
            return ""
        return str(json_dict)
    elif isinstance(json_dict, (tuple, list, set)):
        if skip_empty and not json_dict:
            return ""
        out_str = "[%s]" % (
            ",".join(sorted(sorted_json_str(s, ignore_key, skip_empty) for s in
                            json_dict))
        )
        if skip_empty and out_str == "[]":
            return ""
        return out_str
    elif isinstance(json_dict, dict):
        if skip_empty and not json_dict:
            return ""

        # Here skip the key value pair if skip_empty is True and the value is empty
        def _k_v_gen(d):
            for k, v in d.items():
                if ignore_key is not None and k == ignore_key:
                    continue
                if skip_empty and not v and v != 0 and v != 0.0 and v is not False:
                    continue
                yield k, v

        dict_gen = (
            str(k) + sorted_json_str(v, ignore_key, skip_empty)
            for k, v in _k_v_gen(json_dict)
        )
        out_str = "{%s}" % (",".join(sorted(dict_gen)))
        if skip_empty and out_str == "{}":
            return ""
        return out_str
    elif json_dict is None:
        return json.dumps(json_dict)
    else:
        raise TypeError("Invalid type: %s" % type(json_dict))


def _get_sir_templatemodel() -> TemplateModel:
    infected = Concept(
        name="infected population",
        identifiers={"ido": "0000511"},
        display_name="I"
    )
    susceptible = Concept(
        name="susceptible population",
        identifiers={"ido": "0000514"},
        display_name="S"
    )
    immune = Concept(name="immune population",
                     identifiers={"ido": "0000592"},
                     display_name="R")

    template1 = ControlledConversion(
        controller=infected,
        subject=susceptible,
        outcome=infected,
    )
    template2 = NaturalConversion(subject=infected, outcome=immune)
    return TemplateModel(
        templates=[template1, template2],
        annotations=Annotations(name="SIR", description="SIR model")
    )


class MockNeo4jClient:
    @staticmethod
    def query_relations(
        source_curie: str,
        relation_type: Union[str, List[str]],
        target_curie: str,
    ) -> List:
        rq = RelationQuery(
            source_curie=source_curie,
            target_curie=target_curie,
            relations=relation_type,
        )
        res = get_relations_web(relations_model=rq)
        return [r.dict(exclude_unset=True) for r in res]


class State:
    def __init__(self):
        self.client = MockNeo4jClient()
        self.refinement_closure = RefinementClosure(
            {('doid:0080314', 'bfo:0000016')}
        )


class TestModelApi(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        """Set up the test case"""
        self.test_app = FastAPI()
        self.test_app.state = State()
        self.test_app.include_router(model_blueprint, prefix="/api")
        self.client = TestClient(self.test_app)
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
        """Test the petrinet endpoint."""
        sir_model_templ = _get_sir_templatemodel()
        response = self.client.post(
            "/api/to_petrinet_acsets", json=sir_model_templ.dict()
        )
        self.assertEqual(response.status_code, 200, msg=response.content)
        response_petri_net = PetriNetResponse.parse_obj(response.json())
        model = Model(sir_model_templ)
        petri_net = PetriNetModel(model)
        self.assertEqual(petri_net.to_pydantic(), response_petri_net)

    def test_petri_parameterized(self):
        response = self.client.post(
            "/api/to_petrinet_acsets", json=json.loads(sir_parameterized.json())
        )
        self.assertEqual(200, response.status_code, msg=response.content)

    def test_petri_distribution(self):
        sir_distribution = copy.deepcopy(sir_parameterized)
        distr = Distribution(type='StandardUniform',
                             parameters={'minimum': 0.01, 'maximum': 0.5})
        sir_distribution.parameters['beta'].distribution = distr
        response = self.client.post(
            "/api/to_petrinet_acsets", json=json.loads(sir_distribution.json())
        )
        pm = response.json()
        assert pm['T'][0]['tprop']['parameter_distribution'] == distr.json()
        assert json.loads(pm['T'][0]['tprop']['mira_parameter_distributions']) == \
            {'beta': distr.dict()}
        self.assertEqual(200, response.status_code, msg=response.content)

    def test_petri_to_template_model(self):
        petrinet_json = PetriNetModel(Model(sir)).to_json()
        tm = template_model_from_petri_json(petrinet_json)
        response = self.client.post("/api/from_petrinet_acsets", json=petrinet_json)
        self.assertEqual(200, response.status_code, msg=response.content)
        resp_json_str = sorted_json_str(response.json())
        tm_json_str = sorted_json_str(tm.dict())
        self.assertEqual(resp_json_str, tm_json_str)

    def test_petri_to_template_model_parameterized(self):
        petrinet_json = PetriNetModel(Model(sir_parameterized)).to_json()
        tm = template_model_from_petri_json(petrinet_json)
        response = self.client.post("/api/from_petrinet_acsets", json=petrinet_json)
        self.assertEqual(200, response.status_code, msg=response.content)
        resp_json_str = sorted_json_str(response.json())
        tm_json_str = sorted_json_str(tm.dict())
        self.assertEqual(resp_json_str, tm_json_str)

    def test_askenet_to_template_model(self):
        askenet_json = AskeNetPetriNetModel(Model(sir_parameterized)).to_json()
        response = self.client.post("/api/from_petrinet", json=askenet_json)
        self.assertEqual(200, response.status_code, msg=response.content)
        template_model = TemplateModel.from_json(response.json())
        self.assertIsInstance(template_model, TemplateModel)

    def test_askenet_from_template_model(self):
        response = self.client.post("/api/to_petrinet", json=json.loads(sir_parameterized.json()))
        self.assertEqual(200, response.status_code, msg=response.content)
        template_model = template_model_from_askenet_json(response.json())
        self.assertIsInstance(template_model, TemplateModel)

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

        strat_templ_model = stratify(
            template_model=sir_templ_model, key=key, strata=set(strata)
        )
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

    def test_stratify_observable_api(self):
        from mira.examples.sir import sir_parameterized
        tm = sir_parameterized.copy(deep=True)
        symbols = set(tm.get_concepts_name_map().keys())
        expr = sympy.Add(*[sympy.Symbol(s) for s in symbols])
        tm.observables = {'half_population': Observable(
            name='half_population',
            expression=SympyExprStr(expr/2))
        }

        strata_options = dict(key='age',
                              strata=['y', 'o'],
                              structure=[],
                              cartesian_control=True)

        query_json = {"template_model": json.loads(tm.json())}
        query_json.update(strata_options)

        response = self.client.post("/api/stratify", json=query_json)
        self.assertEqual(200, response.status_code)
        # todo: test that a local stratification equals the remote stratification

    def test_to_dot_file(self):
        sir_templ_model = _get_sir_templatemodel()
        response = self.client.post(
            "/api/viz/to_dot_file", json=sir_templ_model.dict()
        )
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
        response = self.client.post(
            "/api/viz/to_image", json=sir_templ_model.dict()
        )
        self.assertEqual(200, response.status_code)
        self.assertIn(
            "image/png",
            response.headers["content-type"],
            f"Got content-type {response.headers['content-type']}",
        )
        gm = GraphicalModel(Model(sir_templ_model))
        tmpf = self._get_tmp_file(file_ending="png")
        gm.write(path=tmpf, format="png")
        with open(tmpf, "rb") as fi:
            file_str = fi.read()
        self.assertEqual(file_str, response.content)

    def test_biomodels_id_to_template_model(self):
        model_id = "BIOMD0000000956"
        response = self.client.get(f"/api/biomodels/{model_id}",
                                   params={'simplify_rate_laws': True})
        self.assertEqual(200, response.status_code)

        # Try to make a template model from the json
        tm = TemplateModel.from_json(response.json())

        # Test against locally made template model
        xml_string = get_sbml_model(model_id=model_id)
        local = template_model_from_sbml_string(
            xml_string, model_id=model_id
        )
        self.assertEqual(
            sorted_json_str(tm.dict()), sorted_json_str(local.dict())
        )

    def test_workflow(self):
        """Test downloading a BioModel and converting to PetriNet."""
        biomodel_response = self.client.get("/api/biomodels/BIOMD0000000956")
        self.assertEqual(200, biomodel_response.status_code)
        petrinet_response = self.client.post("/api/to_petrinet_acsets", json=biomodel_response.json())
        self.assertEqual(200, petrinet_response.status_code)
        petrinet_json = petrinet_response.json()
        self.assertIn("S", petrinet_json)

    def test_biomodels_id_bad_request(self):
        response = self.client.get(f"/api/biomodels/not_a_model")
        self.assertEqual(400, response.status_code)

    def test_bilayer_json_to_template_model(self):
        from mira.examples.sir import sir_bilayer

        response = self.client.post("/api/bilayer_to_model", json=sir_bilayer)
        self.assertEqual(response.status_code, 200)

        # Try to make a TemplateModel of the json
        tm = TemplateModel.from_json(response.json())
        tm2 = template_model_from_bilayer(bilayer_json=sir_bilayer)
        sorted1 = sorted(tm.templates, key=lambda t: t.get_key())
        sorted2 = sorted(tm2.templates, key=lambda t: t.get_key())
        assert all(t1.is_equal_to(t2) for t1, t2 in zip(sorted1, sorted2))

    def test_template_model_to_bilayer_json(self):
        from mira.examples.sir import sir_bilayer

        tm = template_model_from_bilayer(bilayer_json=sir_bilayer)
        bj = BilayerModel(Model(tm)).bilayer

        response = self.client.post("/api/model_to_bilayer",
                                    json=json.loads(tm.json()))
        self.assertEqual(response.status_code, 200)
        bj_res = response.json()

        self.assertEqual(sorted_json_str(bj), sorted_json_str(bj_res))

    def test_xml_str_to_template_model(self):
        model_id = "BIOMD0000000956"
        xml_string = get_sbml_model(model_id=model_id)

        response = self.client.post(
            "/api/sbml_xml_to_model", json={"xml_string": xml_string}
        )
        self.assertEqual(response.status_code, 200)
        tm_res = TemplateModel.from_json(response.json())

        local = template_model_from_sbml_string(xml_string)
        self.assertEqual(
            sorted_json_str(tm_res.dict()), sorted_json_str(local.dict())
        )

    def test_models_to_templatemodel_delta_graph_json(self):
        sir_templ_model = _get_sir_templatemodel()
        sir_templ_model_ctx = TemplateModel(
            templates=[
                t.with_context(location="geonames:5128581")
                for t in sir_templ_model.templates
            ]
        )

        response = self.client.post(
            "/api/models_to_delta_graph",
            json={
                "template_model1": sir_templ_model.dict(),
                "template_model2": sir_templ_model_ctx.dict(),
            },
        )
        self.assertEqual(200, response.status_code)

        tmd = TemplateModelDelta(
            template_model1=sir_templ_model,
            template_model2=sir_templ_model_ctx,
            # If the dkg is out of sync with what is on the server,
            # the is_ontological_child functions might give different results
            refinement_function=is_ontological_child_web,
        )
        local_str = sorted_json_str(tmd.graph_as_json())
        resp_str = sorted_json_str(response.json())

        self.assertEqual(local_str, resp_str)

    def test_models_to_templatemodel_delta_graph_image(self):
        sir_templ_model = _get_sir_templatemodel()
        sir_templ_model_ctx = TemplateModel(
            templates=[
                t.with_context(location="geonames:5128581")
                for t in sir_templ_model.templates
            ]
        )

        response = self.client.post(
            "/api/models_to_delta_image",
            json={
                "template_model1": sir_templ_model.dict(),
                "template_model2": sir_templ_model_ctx.dict(),
            },
        )
        self.assertEqual(200, response.status_code)
        self.assertIn(
            "image/png",
            response.headers["content-type"],
            f"Got content-type {response.headers['content-type']}",
        )
        tmd = TemplateModelDelta(
            template_model1=sir_templ_model,
            template_model2=sir_templ_model_ctx,
            # If the dkg is out of sync with what is on the server,
            # the is_ontological_child functions might give different results
            refinement_function=is_ontological_child_web,
        )

        tmpf = self._get_tmp_file(file_ending="png")
        tmd.draw_graph(path=tmpf.absolute().as_posix())
        with open(tmpf, "rb") as fi:
            file_str = fi.read()
        self.assertEqual(file_str, response.content)

    def test_add_transition(self):
        sir_templ_model = _get_sir_templatemodel()
        s = {'name': 'susceptible population',
             'identifiers': {'ido': '0000514'}}
        x = {'name': 'new_state'}
        response = self.client.post(
            "/api/add_transition",
            json={
                "template_model": sir_templ_model.dict(),
                "subject_concept": s,
                "outcome_concept": x,
                "parameter": {'name': 's_to_x', 'value': 0.1}}
        )
        self.assertEqual(200, response.status_code)

    def test_n_way_comparison(self):
        sir_templ_model = _get_sir_templatemodel()
        sir_templ_model_ctx = TemplateModel(
            templates=[
                t.with_context(location="geonames:5128581")
                for t in sir_templ_model.templates
            ]
        )
        mmts = [sir_templ_model, sir_templ_model_ctx]

        response = self.client.post(
            "/api/model_comparison",
            json={"template_models": [m.dict() for m in mmts]},
        )
        self.assertEqual(200, response.status_code)

        # See if the response json can be parsed with ModelComparisonResponse
        resp_model = ModelComparisonResponse(**response.json())

        # Check that the response is the same as the local version
        # explicitly don't use TemplateModelComparison.from_template_models
        local = TemplateModelComparison(
            template_models=mmts, refinement_func=is_ontological_child_web
        )
        model_comparson_graph_data = local.model_comparison
        local_response = ModelComparisonResponse(
            graph_comparison_data=model_comparson_graph_data,
            similarity_scores=model_comparson_graph_data.get_similarity_scores(),
        )
        self.assertEqual(
            sorted_json_str(local_response.dict()),
            sorted_json_str(resp_model.dict()),
        )

    def test_n_way_comparison_askenet(self):
        # Copy all data from the askenet test, but set location context for
        # the second model
        sir_templ_model = _get_sir_templatemodel()
        sir_parameterized_ctx = TemplateModel(
            templates=[
                t.with_context(location="geonames:5128581")
                for t in sir_templ_model.templates
            ]
        )
        # Copy parameters, annotations, initials and observables from the
        # original model
        sir_parameterized_ctx.parameters = {
            k: v.copy(deep=True)
            for k, v in sir_templ_model.parameters.items()
        }
        sir_parameterized_ctx.annotations = \
            sir_templ_model.annotations.copy(deep=True)
        sir_parameterized_ctx.observables = {
            k: v.copy(deep=True)
            for k, v in sir_templ_model.observables.items()
        }
        sir_parameterized_ctx.initials = {
            k: v.copy(deep=True) for k, v in sir_templ_model.initials.items()
        }
        sir_parameterized_ctx.time = copy.deepcopy(sir_templ_model.time)
        askenet_list = []
        for sp in [sir_templ_model, sir_parameterized_ctx]:
            for idx, template in enumerate(sp.templates):
                template.name = f"t{idx + 1}"
            sp.time = Time(id='t')
            askenet_list.append(
                AskeNetPetriNetModel(Model(sp)).to_json()
            )

        response = self.client.post(
            "/api/askenet_model_comparison",
            json={"petrinet_models": askenet_list},
        )
        self.assertEqual(200, response.status_code)

        # See if the response json can be parsed with ModelComparisonResponse
        resp_json = response.json()
        resp_model = ModelComparisonResponse(
            graph_comparison_data=ModelComparisonGraphdata(**resp_json["graph_comparison_data"]),
            similarity_scores=resp_json["similarity_scores"],

        )

        # Check that the response is the same as the local version
        local = TemplateModelComparison(
            template_models=[sir_templ_model, sir_parameterized_ctx],
            refinement_func=is_ontological_child_web
        )
        model_comparson_graph_data = local.model_comparison
        local_response = ModelComparisonResponse(
            graph_comparison_data=model_comparson_graph_data,
            similarity_scores=model_comparson_graph_data.get_similarity_scores(),
        )

        dict_options = {
            "exclude_defaults": True,
            "exclude_unset": True,
            "exclude_none": True,
            "skip_defaults": True,
        }
        # Compare the ModelComparisonResponse models
        assert local_response == resp_model  # If assertion fails the diff is printed
        local_sorted_str = sorted_json_str(
            json.loads(local_response.json(**dict_options)), skip_empty=True
        )
        resp_sorted_str = sorted_json_str(
            json.loads(resp_model.json(**dict_options)), skip_empty=True
        )
        self.assertEqual(local_sorted_str, resp_sorted_str)

    def test_counts_to_dimensionless_mira(self):
        # Test counts_to_dimensionless
        old_beta = sir_parameterized_init.parameters['beta'].value

        response = self.client.post(
            "/api/counts_to_dimensionless_mira",
            json={
                "model": json.loads(sir_parameterized_init.json()),
                "counts_unit": "person",
                "norm_factor": sir_init_val_norm,
            },
        )
        self.assertEqual(200, response.status_code)

        tm_dimless_json = response.json()
        tm_dimless = TemplateModel.from_json(tm_dimless_json)

        for template in tm_dimless.templates:
            for concept in template.get_concepts():
                assert concept.units.expression.args[0].equals(1), \
                    concept.units

        assert tm_dimless.parameters['beta'].units.expression.args[0].equals(
            1 / sympy.Symbol('day'))
        assert tm_dimless.parameters['beta'].value == \
               old_beta * sir_init_val_norm

        assert tm_dimless.initials['susceptible_population'].value == \
               (sir_init_val_norm - 1) / sir_init_val_norm
        assert tm_dimless.initials['infected_population'].value == \
               1 / sir_init_val_norm
        assert tm_dimless.initials['immune_population'].value == 0

        for initial in tm_dimless.initials.values():
            assert initial.concept.units.expression.args[0].equals(1)

    def test_counts_to_dimensionless_amr(self):
        # Same test as test_counts_to_dimensionless_mira but with sending
        # the model as an askenetpetrinet instead of a mira model
        norm = sir_init_val_norm
        old_beta = sir_parameterized_init.parameters['beta'].value

        # transform to askenetpetrinet
        amr_json = AskeNetPetriNetModel(Model(sir_parameterized_init)).to_json()

        # Post to /api/counts_to_dimensionless_amr
        response = self.client.post(
            "/api/counts_to_dimensionless_amr",
            json={
                "model": amr_json,
                "counts_unit": "person",
                "norm_factor": norm,
            },
        )
        self.assertEqual(200, response.status_code)

        # transform json > amr > template model
        amr_dimless_json = response.json()
        tm_dimless = template_model_from_askenet_json(amr_dimless_json)

        for template in tm_dimless.templates:
            for concept in template.get_concepts():
                assert concept.units.expression.args[0].equals(1), \
                    concept.units

        assert tm_dimless.parameters['beta'].units.expression.args[0].equals(
            1 / sympy.Symbol('day'))
        assert tm_dimless.parameters['beta'].value == old_beta * norm

        assert tm_dimless.initials['susceptible_population'].value \
               == (norm - 1) / norm
        assert tm_dimless.initials['infected_population'].value == 1 / norm
        assert tm_dimless.initials['immune_population'].value == 0

        for initial in tm_dimless.initials.values():
            assert initial.concept.units.expression.args[0].equals(1)

    def test_reconstruct_ode_semantics_endpoint(self):
        # Load test file
        from mira.sources.askenet.flux_span import test_file_path, \
            docker_test_file_path
        from mira.sources.askenet.petrinet import template_model_from_askenet_json
        path = test_file_path if test_file_path.exists() else \
            docker_test_file_path

        strat_model = json.load(path.open())
        response = self.client.post(
            "/api/reconstruct_ode_semantics",
            json={"model": strat_model}
        )
        self.assertEqual(200, response.status_code)

        flux_span_amr_json = response.json()
        flux_span_tm = template_model_from_askenet_json(flux_span_amr_json)
        assert len(flux_span_tm.templates) == 10
        assert len(flux_span_tm.parameters) == 11
        assert all(t.rate_law for t in flux_span_tm.templates)

    def test_deactivation_endpoint(self):
        # Deliberately create a stratifiction that will lead to nonsense
        # transitions, i.e. a transitions between age groups
        age_strata = stratify(sir_parameterized_init,
                              key='age',
                              strata=['y', 'o'],
                              cartesian_control=True)

        amr_sir = AskeNetPetriNetModel(Model(age_strata)).to_json()

        # Test the endpoint itself
        # Should fail with 422 because of missing transitions or parameters
        response = self.client.post(
            "/api/deactivate_transitions",
            json={"model": amr_sir}
        )
        self.assertEqual(422, response.status_code)

        # Should fail with 422 because of empty transition list
        response = self.client.post(
            "/api/deactivate_transitions",
            json={"model": amr_sir, "transitions": [[]]}
        )
        self.assertEqual(422, response.status_code)

        # Should fail with 422 because of transitions are triples
        response = self.client.post(
            "/api/deactivate_transitions",
            json={"model": amr_sir, "transitions": [['a', 'b', 'c']]}
        )
        self.assertEqual(422, response.status_code)

        # Should fail with 422 because of empty parameters list
        response = self.client.post(
            "/api/deactivate_transitions",
            json={"model": amr_sir, "parameters": []}
        )
        self.assertEqual(422, response.status_code)

        # Actual Test
        # Assert that there are old to young transitions
        transition_list = []
        for template in age_strata.templates:
            if hasattr(template, 'subject') and hasattr(template, 'outcome'):
                subj, outc = template.subject.name, template.outcome.name
                if subj.endswith('_o') and outc.endswith('_y') or \
                        subj.endswith('_y') and outc.endswith('_o'):
                    transition_list.append((subj, outc))
        assert len(transition_list), "No old to young transitions found"
        response = self.client.post(
            "/api/deactivate_transitions",
            json={"model": amr_sir, "transitions": transition_list}
        )
        self.assertEqual(200, response.status_code)

        # Check that the transitions are deactivated
        amr_sir_deactivated = response.json()
        tm_deactivated = template_model_from_askenet_json(amr_sir_deactivated)
        for template in tm_deactivated.templates:
            if hasattr(template, 'subject') and hasattr(template, 'outcome'):
                subj, outc = template.subject.name, template.outcome.name
                if (subj, outc) in transition_list:
                    assert template.rate_law.args[0] == \
                           sympy.core.numbers.Zero(), \
                        template.rate_law

        # Test using parameter names for deactivation
        deactivate_key = list(age_strata.parameters.keys())[0]
        response = self.client.post(
            "/api/deactivate_transitions",
            json={"model": amr_sir, "parameters": [deactivate_key]}
        )
        self.assertEqual(200, response.status_code)
        amr_sir_deactivated_params = response.json()
        tm_deactivated_params = template_model_from_askenet_json(
            amr_sir_deactivated_params)
        for template in tm_deactivated_params.templates:
            # All rate laws must either be zero or not contain the deactivated
            # parameter
            if template.rate_law and not template.rate_law.is_zero:
                for symb in template.rate_law.atoms():
                    assert str(symb) != deactivate_key
            else:
                assert (template.rate_law.args[0] == sympy.core.numbers.Zero(),
                        template.rate_law)
