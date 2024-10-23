"""This module implements generation into Petri net models which are defined
at https://github.com/DARPA-ASKEM/Model-Representations/tree/main/petrinet.
"""

__all__ = ["AMRPetriNetModel", "ModelSpecification",
           "template_model_to_petrinet_json"]

import json
import logging
from copy import deepcopy
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from mira.metamodel import expression_to_mathml, TemplateModel, SympyExprStr
from mira.sources.amr import sanity_check_amr

from .. import Model
from .utils import add_metadata_annotations

logger = logging.getLogger(__name__)

SCHEMA_VERSION = '0.6'
SCHEMA_URL = ('https://raw.githubusercontent.com/DARPA-ASKEM/'
              'Model-Representations/petrinet_v%s/petrinet/'
              'petrinet_schema.json') % SCHEMA_VERSION


class AMRPetriNetModel:
    """A class representing a PetriNet model."""

    def __init__(self, model: Model):
        """Instantiate a petri net model from a generic transition model.

        Parameters
        ----------
        model:
            The pre-compiled transition model
        """
        self.properties = {}
        self.initials = []
        self.rates = []
        self.states = []
        self.transitions = []
        self.parameters = []
        self.metadata = {}
        self.time = None
        self.observables = []
        self.model_name = 'Model'
        if model.template_model.annotations and \
                model.template_model.annotations.name:
            self.model_name = model.template_model.annotations.name
        self.model_description = self.model_name
        if model.template_model.annotations and \
                model.template_model.annotations.description:
            self.model_description = \
                model.template_model.annotations.description
        vmap = {}
        for key, var in model.variables.items():
            # Use the variable's concept name if possible but fall back
            # on the key otherwise
            vmap[key] = name = var.concept.name or str(key)
            display_name = var.concept.display_name or name
            description = var.concept.description
            # State structure
            # {
            #   'id': str,
            #   'name': str,
            #   'grounding': {identifiers, modifiers},
            # }
            states_dict = {
                'id': name,
                'name': display_name
            }
            if description:
                states_dict['description'] = description
            states_dict['grounding'] =  {
                    'identifiers': {k: v for k, v in
                                    var.concept.identifiers.items()
                                    if k != 'biomodels.species'},
                    'modifiers': var.concept.context,
                },

            if var.concept.units:
                states_dict['units'] = {
                    'expression': str(var.concept.units.expression),
                    'expression_mathml': expression_to_mathml(
                        var.concept.units.expression.args[0]
                    ),
                }

            self.states.append(states_dict)
            # 'initial' object structure
            # {
            #   'target': str,  # refers to a state id above
            #   'expression': str,
            #   'expression_mathml': str,
            # }
            initial = var.data.get('expression')
            if initial is not None:
                initial_data = {
                    'target': name,
                    'expression': str(initial),
                    'expression_mathml': expression_to_mathml(initial)
                }
                self.initials.append(initial_data)

        for key, observable in model.observables.items():
            display_name = observable.observable.display_name \
                if observable.observable.display_name \
                else observable.observable.name
            obs_data = {
                'id': observable.observable.name,
                'name': display_name,
                'expression': str(observable.observable.expression),
                'expression_mathml': expression_to_mathml(
                    observable.observable.expression.args[0]),
            }
            self.observables.append(obs_data)

        if model.template_model.time:
            self.time = {'id': model.template_model.time.name}
            if model.template_model.time.units:
                self.time['units'] = {
                    'expression': str(model.template_model.time.units.expression),
                    'expression_mathml': expression_to_mathml(
                        model.template_model.time.units.expression.args[0]),
                }
        else:
            self.time = None

        # Transition structure
        # {
        #   "id": "t1",
        #   "input": ["s1", "s2"],
        #   "output": ["s3", "s4"],
        #   "grounding": {identifiers, modifiers},
        #   "properties": {...}, keys: name, grounding > {identifiers, modifiers}
        # }
        # Rate structure:
        # {
        #   target: string,  # refers to a transition id above
        #   expression: string,
        #   expression_mathml
        # }
        for idx, transition in enumerate(model.transitions.values()):
            tid = transition.template.name \
                if transition.template.name else f"t{idx + 1}"
            # fixme: get grounding for transition
            transition_dict = {"id": tid}

            inputs = []
            outputs = []
            for c in transition.control:
                inputs.append(vmap[c.key])
                outputs.append(vmap[c.key])
            for c in transition.consumed:
                inputs.append(vmap[c.key])
            for p in transition.produced:
                outputs.append(vmap[p.key])

            transition_dict['input'] = inputs
            transition_dict['output'] = outputs

            # Include rate law
            if transition.template.rate_law:
                rate_law = transition.template.rate_law.args[0]
                self.rates.append({
                    'target': tid,
                    'expression': str(rate_law),
                    'expression_mathml': expression_to_mathml(rate_law)
                })

            transition_dict['properties'] = {
                'name': tid,
            }

            self.transitions.append(transition_dict)

        for key, param in model.parameters.items():
            if param.placeholder:
                continue
            param_dict = {'id': str(key)}
            if param.display_name:
                param_dict['name'] = param.display_name
            if param.description:
                param_dict['description'] = param.description
            if param.value is not None:
                param_dict['value'] = param.value
            if not param.distribution:
                pass
            elif param.distribution.type is None:
                logger.warning("can not add distribution without type: %s", param.distribution)
            else:
                serialized_distr_parameters = {}
                for param_key, param_value in param.distribution.parameters.items():
                    if isinstance(param_value, SympyExprStr):
                        serialized_distr_parameters[param_key] = \
                            str(param_value.args[0])
                    else:
                        serialized_distr_parameters[param_key] = param_value
                param_dict['distribution'] = {
                    'type': param.distribution.type,
                    'parameters': serialized_distr_parameters,
                }
            if param.concept and param.concept.units:
                param_dict['units'] = {
                    'expression': str(param.concept.units.expression),
                    'expression_mathml': expression_to_mathml(
                        param.concept.units.expression.args[0]),
                }
            self.parameters.append(param_dict)

        add_metadata_annotations(self.metadata, model)

    def to_json(
        self,
        name: str = None,
        description: str = None,
        model_version: str = None
    ):
        """Return a JSON dict structure of the Petri net model.

        Parameters
        ----------
        name :
            The name of the model. Defaults to the name of the original
            template model that produced the input Model instance or, if not
            available, 'Model'.
        description :
            A description of the model. Defaults to the description of the
            original template model that produced the input Model instance or,
            if not available, the name of the model.
        model_version :
            The version of the model. Defaults to '0.1'.

        Returns
        -------
        : JSON
            A JSON dict representing the Petri net model.
        """
        json_data = {
            'header': {
                'name': name or self.model_name,
                'schema': SCHEMA_URL,
                'schema_name': 'petrinet',
                'description': description or self.model_description,
                'model_version': model_version or '0.1',
            },
            'properties': self.properties,
            'model': {
                'states': self.states,
                'transitions': self.transitions,
            },
            'semantics': {'ode': {
                'rates': self.rates,
                'initials': self.initials,
                'parameters': self.parameters,
                'observables': self.observables,
                'time': self.time if self.time else {'id': 't'}
            }},
            'metadata': self.metadata,
        }
        try:
            sanity_check_amr(json_data)
        except Exception as e:
            logger.warning("Error in AMR sanity check: %s", str(e))
        return json_data

    def to_pydantic(self, name=None, description=None, model_version=None) -> "ModelSpecification":
        """Return a Pydantic model representation of the Petri net model.

        Parameters
        ----------
        name :
            The name of the model. Defaults to the name of the original
            template model that produced the input Model instance or, if not
            available, 'Model'.
        description :
            A description of the model. Defaults to the description of the
            original template model that produced the input Model instance or,
            if not available, the name of the model.
        model_version :
            The version of the model. Defaults to '0.1'.

        Returns
        -------
        :
            A Pydantic model representation of the Petri net model.
        """
        return ModelSpecification(
            header=Header(
                name=name or self.model_name,
                schema=SCHEMA_URL,
                schema_name='petrinet',
                description=description or self.model_description,
                model_version=model_version or '0.1',
            ),
            properties=self.properties,
            model=PetriModel(
                states=[State.model_validate(s) for s in self.states],
                transitions=[Transition.model_validate(t) for t in self.transitions],
            ),
            semantics=Ode(ode=OdeSemantics(
                rates=[Rate.model_validate(r) for r in self.rates],
                initials=[Initial.model_validate(i) for i in self.initials],
                parameters=[Parameter.model_validate(p) for p in self.parameters],
                observables=[Observable.model_validate(o) for o in self.observables],
                time=Time.model_validate(self.time) if self.time else Time(id='t')
            )),
            metadata=self.metadata,
        )

    def to_json_str(self, **kwargs) -> str:
        """Return a JSON string representation of the Petri net model.

        Parameters
        ----------
        kwargs :
            Additional keyword arguments to pass to :func:`json.dumps`.

        Returns
        -------
        :
            A JSON string representation of the Petri net model.
        """
        return json.dumps(self.to_json(), **kwargs)

    def to_json_file(self, fname, name=None, description=None,
                     model_version=None, **kwargs):
        """Write the Petri net model to a JSON file

        Parameters
        ----------
        fname : str
            The file name to write to.
        name : str, optional
            The name of the model.
        description : str, optional
            A description of the model.
        model_version : str, optional
            The version of the model.
        kwargs :
            Additional keyword arguments to pass to :func:`json.dump`.
        """
        indent = kwargs.pop('indent', 1)
        js = self.to_json(name=name, description=description,
                          model_version=model_version)
        with open(fname, 'w') as fh:
            json.dump(js, fh, indent=indent, **kwargs)


def template_model_to_petrinet_json(tm: TemplateModel):
    """Convert a template model to a PetriNet JSON dict.

    Parameters
    ----------
    tm :
        The template model to convert.

    Returns
    -------
    A JSON dict representing the PetriNet model.
    """
    return AMRPetriNetModel(Model(tm)).to_json()


def template_model_to_petrinet_json_file(tm: TemplateModel, fname):
    """Convert a template model to a PetriNet JSON file.

    Parameters
    ----------
    tm :
        The template model to convert.
    fname : str
        The file name to write to.
    """
    AMRPetriNetModel(Model(tm)).to_json_file(fname)


class Initial(BaseModel):
    target: str
    expression: str
    expression_mathml: str


class TransitionProperties(BaseModel):
    name: Optional[str] = None
    grounding: Optional[Dict] = None


class Rate(BaseModel):
    target: str
    expression: str
    expression_mathml: str


class Distribution(BaseModel):
    type: str
    parameters: Dict


class Units(BaseModel):
    expression: str
    expression_mathml: str


class State(BaseModel):
    id: str
    name: Optional[str] = None
    grounding: Optional[Dict] = None
    units: Optional[Units] = None


class Transition(BaseModel):
    id: str
    input: List[str]
    output: List[str]
    grounding: Optional[Dict] = None
    properties: Optional[TransitionProperties] = None


class Parameter(BaseModel):
    id: str
    description: Optional[str] = None
    value: Optional[float] = None
    grounding: Optional[Dict] = None
    distribution: Optional[Distribution] = None
    units: Optional[Units] = None

    @classmethod
    def from_dict(cls, d):
        d = deepcopy(d)
        d['id'] = str(d['id'])
        return cls.model_validate(d)


class Time(BaseModel):
    id: str
    units: Optional[Units] = None


class Observable(BaseModel):
    id: str
    name: Optional[str] = None
    grounding: Optional[Dict] = None
    expression: str
    expression_mathml: str


class PetriModel(BaseModel):
    states: List[State]
    transitions: List[Transition]


class OdeSemantics(BaseModel):
    rates: List[Rate]
    initials: List[Initial]
    parameters: List[Parameter]
    time: Optional[Time] = None
    observables: List[Observable]


class Ode(BaseModel):
    ode: Optional[OdeSemantics] = None


class Header(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    name: str
    schema_url: str = Field(..., alias='schema')
    schema_name: str
    description: str
    model_version: str


class ModelSpecification(BaseModel):
    """A Pydantic model corresponding to the PetriNet JSON schema."""
    header: Header
    properties: Optional[Dict] = None
    model: PetriModel
    semantics: Optional[Ode] = None
    metadata: Optional[Dict] = None
