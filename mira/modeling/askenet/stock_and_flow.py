from mira.modeling import Model
from mira.metamodel import *


class AskeNetStockFlowModel:

    def __init__(self, model: Model):
        self.properties = {}
        self.stocks = []
        self.flows = []
        self.links = []
        self.model_name = 'Model'

        for idx, flow in enumerate(model.transitions.values()):
            fid = f"{idx + 1}"
            fname = flow.template.name

            input = flow.consumed[0].key
            output = flow.produced[0].key

            rate_law_str = None
            if flow.template.rate_law:
                rate_law_str = str(flow.template.rate_law)

                for param_key, param_obj in model.parameters.items():
                    if param_obj.placeholder:
                        continue
                    index = rate_law_str.find(param_key)
                    if index < 0:
                        continue
                    rate_law_str = rate_law_str[:index] + 'p.' + rate_law_str[index:]

                for var_obj in model.variables.values():
                    index = rate_law_str.find(var_obj.concept.display_name)
                    if index < 0:
                        continue
                    rate_law_str = rate_law_str[:index] + 'u.' + rate_law_str[index:]

            flow_dict = {'_id': fid,
                         'u': input,
                         'd': output,
                         'fname': fname,
                         'ϕf': rate_law_str}

            self.flows.append(flow_dict)

        vmap = {}
        for var_key, var in model.variables.items():
            vmap[var_key] = name = var.concept.name or str(var_key)
            display_name = var.concept.display_name or name

            stocks_dict = {
                '_id': name,
                'sname': display_name,
            }
            self.stocks.append(stocks_dict)

    def to_json(self):
        return {
            'Flow': self.flows,
            'Stock': self.stocks,
        }


def template_model_to_stock_flow_json(tm: TemplateModel):
    return AskeNetStockFlowModel(Model(tm)).to_json()
