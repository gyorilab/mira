"""This module implements parsing Stock and Flow models defined in
https://github.com/DARPA-ASKEM/Model-Representations/tree/main/stockflow.
"""

__all__ = ["AMRStockFlowModel", "template_model_to_stockflow_json"]

import logging

import sympy

from mira.modeling import Model
from mira.metamodel import *
from .utils import add_metadata_annotations


logger = logging.getLogger(__name__)


class AMRStockFlowModel:
    """A class representing a Stock and Flow Model"""

    SCHEMA_VERSION = "0.1"
    SCHEMA_URL = (
        f"https://raw.githubusercontent.com/DARPA-ASKEM/Model-Representations/"
        f"stockflow_v{SCHEMA_VERSION}/stockflow/stockflow_schema.json"
    )

    def __init__(self, model: Model):
        """Instantiate a stock and flow model from a generic transition model.

                Parameters
                ----------
                model:
                    The pre-compiled transition model
        """
        self.properties = {}
        self.stocks = []
        self.flows = []
        self.links = []
        self.observables = []
        self.initials = []
        self.parameters = []
        self.auxiliaries = []
        self.time = None
        self.metadata = {}
        self.model_name = 'SIR Model'

        # Mapping of auxiliary variables to be substituted in flow rate law expressions
        auxiliary_mapping = {}

        if model.template_model.annotations and \
            model.template_model.annotations.name:
            self.model_name = model.template_model.annotations.name
        self.model_description = self.model_name
        if model.template_model.annotations and \
            model.template_model.annotations.description:
            self.model_description = \
                model.template_model.annotations.description

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

        vmap = {}
        for key, var in model.variables.items():
            vmap[key] = name = var.concept.name or str(key)
            display_name = var.concept.display_name or name
            description = var.concept.description
            stocks_dict = {
                'id': name,
                'name': display_name
            }
            if description:
                stocks_dict['description'] = description
            stocks_dict['grounding'] = {
                    'identifiers': {k: v for k, v in
                                    var.concept.identifiers.items()
                                    if k != 'biomodels.species'},
                    'modifiers': var.concept.context
                }
            if var.concept.units:
                stocks_dict['units'] = {
                    'expression': str(var.concept.units.expression),
                    'expression_mathml': expression_to_mathml(
                        var.concept.units.expression.args[0]
                    ),
                }

            self.stocks.append(stocks_dict)
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

        for key, param in model.parameters.items():
            if param.placeholder:
                continue

            # test to see if parameter is present in any of the rate laws
            used_parameter_flag = False
            for flow in model.transitions.values():
                if flow.template.rate_law is None:
                    continue
                if sympy.Symbol(key) in flow.template.rate_law.free_symbols:
                    used_parameter_flag = True
                    break

            # If the parameter is not a base level model parameter and is present within a flow rate expression
            if not key.startswith('p_') and used_parameter_flag:
                auxiliary_dict = {'id': key}
                auxiliary_dict['name'] = key
                expression = sympy.Symbol(key)
                auxiliary_dict['expression'] = key
                auxiliary_dict['expression_mathml'] = expression_to_mathml(expression)
                auxiliary_mapping[key] = key
                self.auxiliaries.append(auxiliary_dict)
            elif key.startswith('p_'):
                auxiliary_dict = {'id': key[2:]}
                auxiliary_dict['name'] = key[2:]
                expression = sympy.Symbol(key)
                auxiliary_dict['expression'] = str(expression)
                auxiliary_dict['expression_mathml'] = expression_to_mathml(expression)
                auxiliary_mapping[key] = key[2:]
                self.auxiliaries.append(auxiliary_dict)

            # Add parameter to list of model parameters regardless if it's added to list of auxiliaries
            param_dict = {'id': key}
            if param.display_name:
                param_dict['name'] = param.display_name
            if param.description:
                param_dict['description'] = param.description
            if param.value is not None:
                param_dict['value'] = param.value
                param_dict['value'] = param.value
            if not param.distribution:
                pass
            elif param.distribution.type is None:
                logger.warning("can not add distribution without type: %s", param.distribution)
            else:
                param_dict['distribution'] = {
                    'type': param.distribution.type,
                    'parameters': param.distribution.parameters,
                }
            if param.concept and param.concept.units:
                param_dict['units'] = {
                    'expression': str(param.concept.units.expression),
                    'expression_mathml': expression_to_mathml(
                        param.concept.units.expression.args[0]),
                }
            self.parameters.append(param_dict)

        link_id = 1
        for idx, flow in enumerate(model.transitions.values()):
            fid = flow.template.name \
                if flow.template.name else f"t{idx + 1}"
            flow_dict = {"id": fid}
            flow_dict['name'] = flow.template.display_name
            flow_dict['upstream_stock'] = flow.consumed[0].concept.name if flow.consumed else None
            flow_dict['downstream_stock'] = flow.produced[0].concept.name if flow.produced else None

            if flow.template.rate_law:
                rate_law = flow.template.rate_law.args[0]
                formatted_rate_law = format_rate_law(rate_law, auxiliary_mapping)
                flow_dict['rate_expression'] = str(formatted_rate_law)
                flow_dict['rate_expression_mathml'] = expression_to_mathml(formatted_rate_law)

            self.flows.append(flow_dict)

            if flow.template.rate_law is not None:
                for symbol in flow.template.rate_law.free_symbols:
                    link_dict = {'id': f'link{link_id}'}
                    str_symbol = str(symbol)

                    link_dict['source'] = str_symbol
                    link_dict['target'] = fid
                    link_id += 1
                    self.links.append(link_dict)

        add_metadata_annotations(self.metadata, model)

    def to_json(self):
        """Return a JSON dict structure of the Stock and Flow model."""
        return {
            'header': {
                'name': self.model_name,
                'schema': self.SCHEMA_URL,
                'description': self.model_description,
                'schema_name': 'stockflow',
                'model_version': '0.1',
            },
            'properties': self.properties,
            'model': {
                'flows': self.flows,
                'stocks': self.stocks,
                'auxiliaries': self.auxiliaries,
                'observables': self.observables,
                'links': self.links
            },
            'semantics': {'ode': {
                'parameters': self.parameters,
                'initials': self.initials,
                'time': self.time if self.time else {'id': 't'}
            }},
            'metadata': self.metadata,
        }


def format_rate_law(rate_law, auxiliary_mapping) -> sympy.Expr:
    for old_symbol_str, aux_symbol_str in auxiliary_mapping.items():
        rate_law = rate_law.subs(sympy.Symbol(old_symbol_str), sympy.Symbol(aux_symbol_str))
    return rate_law


def template_model_to_stockflow_json(tm: TemplateModel):
    """Convert a template model to a Stock and Flow JSON dict.

        Parameters
        ----------
        tm :
            The template model to convert.

        Returns
        -------
        : JSON
            A JSON dict representing the Stock and Flow model.
        """
    return AMRStockFlowModel(Model(tm)).to_json()
