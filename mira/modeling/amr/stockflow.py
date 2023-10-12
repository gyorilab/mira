import sympy

from mira.modeling import Model
from mira.metamodel import *
import logging

logger = logging.getLogger(__name__)

class AMRStockFlowModel:
    def __init__(self, model: Model):
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
            stocks_dict = {
                'id': name,
                'name': display_name,
                'grounding': {
                    'identifiers': {k: v for k, v in
                                    var.concept.identifiers.items()
                                    if k != 'biomodels.species'},
                    'modifiers': var.concept.context,
                },
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
            param_dict = {'id': str(key)}
            if key.startswith('p_'):
                param_name = key[2:]
                auxiliary_dict = {}
                auxiliary_dict['id'] = param_name
                auxiliary_dict['name'] = param_name
                expression = safe_parse_expr(f"1.0 * {key}", {key: sympy.Symbol(key)})
                auxiliary_dict['expression'] = str(expression)
                auxiliary_dict['expression_mathml'] = expression_to_mathml(expression)
                self.auxiliaries.append(auxiliary_dict)

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
            # fixme: get grounding for transition
            flow_dict = {"id": fid}
            flow_dict['name'] = flow.template.display_name
            flow_dict['upstream_stock'] = flow.consumed[0].concept.name
            flow_dict['downstream_stock'] = flow.produced[0].concept.name

            if flow.template.rate_law:
                rate_law = flow.template.rate_law.args[0]
                formatted_rate_law = format_rate_law(model, rate_law)
                flow_dict['rate_expression'] = str(formatted_rate_law)
                flow_dict['rate_expression_mathml'] = expression_to_mathml(formatted_rate_law)

            self.flows.append(flow_dict)

            for symbol in flow.template.rate_law.free_symbols:
                link_dict = {'id': f'link{link_id}'}
                str_symbol = str(symbol)
                if str_symbol in model.parameters:
                    str_symbol = str_symbol[2:]

                link_dict['source'] = str_symbol
                link_dict['target'] = fid
                link_id += 1
                self.links.append(link_dict)

    def to_json(self):
        return {
            'header': {
                'name': self.model_name,
                'schema': '',
                'description': self.model_description,
                'schema_name': 'stockflow',
                'model_version': '0.1',
            },
            'properties': self.properties,
            'model': {
                'flows': self.flows,
                'stocks': self.stocks,
                'auxiliaries': self.auxiliaries,
                'links': self.links
            },
            'semantics': {'ode': {
                'parameters': self.parameters,
                'initials': self.initials,
                'observables': self.observables,
                'time': self.time if self.time else {'id': 't'}
            }},
            'metadata': self.metadata,
        }


def format_rate_law(model, rate_law) -> sympy.Expr:
    local_dict = {}
    for symbol in rate_law.free_symbols:
        str_symbol = str(symbol)
        if str_symbol in model.parameters:
            local_dict[str_symbol] = sympy.Symbol(str_symbol[2:])
        else:
            local_dict[str_symbol] = sympy.Symbol(str_symbol)
    return safe_parse_expr(str(rate_law), local_dict)


def template_model_to_stockflow_json(tm: TemplateModel):
    return AMRStockFlowModel(Model(tm)).to_json()
