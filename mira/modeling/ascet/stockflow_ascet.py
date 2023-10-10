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
            fid = flow.template.name
            fname = flow.template.display_name

            input = flow.consumed[0].key
            output = flow.produced[0].key

            rate_law_str = str(flow.template.rate_law) if flow.template.rate_law else None
            if rate_law_str:
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

            # Declare 's' and 't' field of a link before assignment, this is because if a stock is found to be
            # a target for a flow before it is a source, then the 't' field of the link associated with a stock
            # will be displayed first
            links_dict = {'_id': name}
            links_dict['s'] = None
            links_dict['t'] = None
            for flow in model.transitions.values():
                if flow.consumed[0].concept.name == name:
                    links_dict['s'] = flow.template.name
                if flow.produced[0].concept.name == name:
                    links_dict['t'] = flow.template.name

            if not links_dict.get('s') and links_dict.get('t'):
                links_dict['s'] = links_dict.get('t')
            elif links_dict.get('s') and not links_dict.get('t'):
                links_dict['t'] = links_dict.get('s')

            self.links.append(links_dict)

    def to_json(self):
        return {
            'Flow': self.flows,
            'Stock': self.stocks,
            'Link': self.links
        }


def template_model_to_stockflow_ascet_json(tm: TemplateModel):
    return AskeNetStockFlowModel(Model(tm)).to_json()
