import requests
from copy import deepcopy as _d
from mira.sources.amr.stockflow import *
from mira.modeling.amr.stockflow import *

stockflow_example = 'https://raw.githubusercontent.com/DARPA-ASKEM/' \
                    'Model-Representations/7f5e377225675259baa6486c64102f559edfd79f/stockflow/examples/sir.json'


def set_up_file():
    return requests.get(stockflow_example).json()


def test_stockflow_assembley():
    old_amr = _d(set_up_file())
    tm = template_model_from_stockflow_amr_json(old_amr)
    new_amr = template_model_to_stockflow_amr_json(tm)

    def list_of_dict_to_dict(l):
        new_dict = {}
        for item in l:
            try:
                name = item.pop('id')
            except KeyError:
                name = item.pop('target')
            new_dict[name] = item
        return new_dict

    new_model = new_amr['model']
    new_semantics_ode = new_amr['semantics']['ode']

    flows_dict = list_of_dict_to_dict(new_model['flows'])
    stocks_dict = list_of_dict_to_dict(new_model['stocks'])
    auxiliary_dict = list_of_dict_to_dict(new_model['auxiliaries'])
    links_dict = list_of_dict_to_dict(new_model['links'])
    parameters_dict = list_of_dict_to_dict(new_semantics_ode['parameters'])
    initials_dict = list_of_dict_to_dict(new_semantics_ode['initials'])

    # Don't text flow expressions as we substitute auxiliary expressions into
    # their corresponding symbol in a flow rate_expression
    # Auxiliary expressions (e.g. 1.0 * p_cbeta) contain multiplication by 1 and order of symbols is not the same
    # between input and outputamr
    assert len(new_model['flows']) == 2
    for flow in old_amr['model']['flows']:
        flow_id = flow['id']
        assert flow_id in flows_dict
        assert flow['name'] == flows_dict[flow_id]['name']
        assert flow['upstream_stock'] == flows_dict[flow_id]['upstream_stock']
        assert flow['downstream_stock'] == flows_dict[flow_id]['downstream_stock']

    # test stocks
    assert len(new_model['stocks']) == 3
    for stock in old_amr['model']['stocks']:
        stock_id = stock['id']
        assert stock_id in stocks_dict
        assert stock['name'] == stocks_dict[stock_id]['name']
        if stock.get('grounding'):
            assert stock['grounding']['identifiers']['ido'] == stocks_dict[stock_id]['grounding']['identifiers'][
                'ido']

    # test auxiliaries
    assert len(new_model['auxiliaries']) == 3
    for auxiliary in old_amr['model']['auxiliaries']:
        auxiliary_id = auxiliary['id']
        assert auxiliary_id in auxiliary_dict
        assert auxiliary['name'] == auxiliary_dict[auxiliary_id]['name']
        # strip white spaces from auxiliary expression from old amr
        assert auxiliary['expression'].replace(' ', '') == auxiliary_dict[auxiliary_id]['expression']
        assert auxiliary['expression_mathml'] == auxiliary_dict[auxiliary_id]['expression_mathml']

    # linkids are not consistent in mira pipeline due to naming convention.
    # Flows have the same naming convention but we create a template
    # object for each flow and can store the flowname in a template attribute,
    # can't do same for links because no object for links
    assert len(new_model['links']) == 6
    for link in old_amr['model']['links']:
        link_id = link['id']
        assert link_id in links_dict

    # test parameters
    assert len(new_semantics_ode['parameters']) == 6
    for parameter in old_amr['semantics']['ode']['parameters']:
        parameter_id = parameter['id']
        assert parameter_id in parameters_dict
        assert parameter['name'] == parameters_dict[parameter_id]['name']
        assert parameter['description'] == parameters_dict[parameter_id]['description']
        assert parameter['value'] == parameters_dict[parameter_id]['value']

    # test initials
    assert len(new_semantics_ode['initials']) == 3
    for initial in old_amr['semantics']['ode']['initials']:
        initial_id = initial['target']
        assert initial_id in initials_dict
        assert initial['expression'] == initials_dict[initial_id]['expression']
        assert initial['expression_mathml'] == initials_dict[initial_id]['expression_mathml']
