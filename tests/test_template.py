import json
import sympy
from mira.metamodel import *
from mira.metamodel.templates import Config
from mira.dkg.web_client import is_ontological_child_web

# Provide to tests that are not meant to test ontological refinements;
# returning False ensures that tests that check context refinements only
# pass when the context refinement is True
simple_refinement_func = lambda x, y: False


def test_concept_name_equal():
    assert Concept(name='x').is_equal_to(Concept(name='x'))
    assert not Concept(name='x').is_equal_to(Concept(name='y'))


def test_templates_equal():
    infected = Concept(name="infected population", identifiers={"ido": "0000511"})
    susceptible = Concept(name="susceptible population", identifiers={"ido": "0000514"})
    c1 = ControlledConversion(
        subject=Concept(name="susceptible"),
        outcome=Concept(name="infected"),
        controller=Concept(name="infected"),
    )
    c1_gnd = ControlledConversion(
        subject=susceptible,
        outcome=infected,
        controller=infected,
    )
    c2 = ControlledConversion(
        subject=Concept(name="susceptible"),
        outcome=Concept(name="infected"),
        controller=Concept(name="infected"),
    )
    c1_gnd_ctx = c1_gnd.with_context(location="Stockholm")
    c2_ctx = c2.with_context(location="Stockholm")
    # Name equivalence is the fallback when both are ungrounded
    assert c1.is_equal_to(c2, with_context=False)
    assert c1_gnd.is_equal_to(c1_gnd, with_context=False)
    assert c1_gnd.is_equal_to(c1_gnd_ctx, with_context=False)
    assert not c1_gnd.is_equal_to(c1_gnd_ctx, with_context=True)
    assert not c1.is_equal_to(c2_ctx, with_context=True)
    # Name equivalence is the fallback when both are ungrounded
    assert c1.is_equal_to(c2_ctx, with_context=False)


def test_templates_equal_lists():
    t1 = GroupedControlledConversion(
        subject=Concept(name='a'), outcome=Concept(name='b'),
        controllers=[Concept(name='x'), Concept(name='y')]
    )
    t2 = GroupedControlledConversion(
        subject=Concept(name='a'), outcome=Concept(name='b'),
        controllers=[Concept(name='y'), Concept(name='x')]
    )
    t3 = GroupedControlledConversion(
        subject=Concept(name='a'), outcome=Concept(name='b'),
        controllers=[Concept(name='y')]
    )
    t4 = GroupedControlledConversion(
        subject=Concept(name='a'), outcome=Concept(name='b'),
        controllers=[Concept(name='y'), Concept(name='z')]
    )
    assert t1.is_equal_to(t2)
    assert not t1.is_equal_to(t3)
    assert not t1.is_equal_to(t4)

    p1 = GroupedControlledProduction(
        controllers=[Concept(name='a'), Concept(name='b')],
        outcome=Concept(name="x")
    )
    p2 = GroupedControlledProduction(
        controllers=[Concept(name='a'), Concept(name='b')],
        outcome=Concept(name="y")
    )
    p3 = GroupedControlledProduction(
        controllers=[Concept(name='b'), Concept(name='a')],
        outcome=Concept(name="x")
    )
    p4 = GroupedControlledProduction(
        controllers=[Concept(name='a'), Concept(name='c')],
        outcome=Concept(name="x")
    )
    assert not p1.is_equal_to(p2)
    assert p1.is_equal_to(p3)
    assert not p1.is_equal_to(p4)


def test_concepts_equal():
    c1 = Concept(name="infected population", identifiers={"ido": "0000511"})
    c1_w_ctx = c1.with_context(location="Berlin")
    c2 = Concept(name="infected population", identifiers={"ido": "0000511"})
    c2_w_ctx = c2.with_context(location="Stockholm")
    c3 = Concept(name="infected population", context={"location": "Stockholm"})
    c4 = Concept(name="infected population", context={"location": "Berlin"})

    assert c1.is_equal_to(c2)
    assert not c1_w_ctx.is_equal_to(c2_w_ctx, with_context=True)
    assert c1_w_ctx.is_equal_to(c2_w_ctx, with_context=False)
    assert c3.is_equal_to(c4, with_context=False)
    assert not c3.is_equal_to(c4, with_context=True)


def test_template_type_inequality_is_equal():
    infected = Concept(name="infected population", identifiers={"ido": "0000511"})
    susceptible = Concept(name="susceptible population", identifiers={"ido": "0000514"})
    immune = Concept(name="immune population", identifiers={"ido": "0000592"})
    c1 = ControlledConversion(
        subject=susceptible,
        outcome=infected,
        controller=infected,
    )
    n1 = NaturalConversion(subject=infected, outcome=immune)
    assert not c1.is_equal_to(n1)


def test_template_type_inequality_refinement():
    infected = Concept(name="infected population", identifiers={"ido": "0000511"})
    susceptible = Concept(name="susceptible population", identifiers={"ido": "0000514"})
    immune = Concept(name="immune population", identifiers={"ido": "0000592"})
    c1 = ControlledConversion(
        subject=susceptible,
        outcome=infected,
        controller=infected,
    )
    n1 = NaturalConversion(subject=infected, outcome=immune)

    assert not c1.refinement_of(n1, refinement_func=simple_refinement_func)
    assert not n1.refinement_of(c1, refinement_func=simple_refinement_func)


def test_class_incompatibility_is_equal():
    infected = Concept(name="infected population", identifiers={"ido": "0000511"})
    immune = Concept(name="immune population", identifiers={"ido": "0000592"})
    nc = NaturalConversion(subject=infected, outcome=immune)

    assert not infected.is_equal_to(nc)
    assert not nc.is_equal_to(infected)


def test_class_incompatibility_refinement():
    infected = Concept(name="infected population", identifiers={"ido": "0000511"})
    immune = Concept(name="immune population", identifiers={"ido": "0000592"})
    natural_conversion = NaturalConversion(subject=infected, outcome=immune)

    assert not infected.refinement_of(natural_conversion, refinement_func=simple_refinement_func)
    assert not natural_conversion.refinement_of(infected, refinement_func=simple_refinement_func)
    assert not natural_conversion.is_equal_to(infected)


def test_template_context_refinement():
    infected = Concept(name="infected population", identifiers={"ido": "0000511"})
    immune = Concept(name="immune population", identifiers={"ido": "0000592"})
    natural_conversion = NaturalConversion(subject=infected, outcome=immune)
    nc_context = natural_conversion.with_context(location="Boston")
    # Test context refinement
    assert nc_context.refinement_of(
        natural_conversion, refinement_func=simple_refinement_func, with_context=True
    )


# Concepts refinement tests
def test_concept_refinement_grounding():
    # spatial region
    spatial_region = Concept(name="spatial region")
    spatial_region_gnd = Concept(name="spatial region", identifiers={"bfo": "0000006"})
    # one-dimensional spatial region
    one_dim_spat = Concept(name="one-dimensional spatial region")
    one_dim_spat_gnd = Concept(
        name="one-dimensional spatial region", identifiers={"bfo": "0000026"}
    )
    one_dim_spat_gnd_ctx = one_dim_spat_gnd.with_context(location="Stockholm")
    # test grounded
    assert one_dim_spat_gnd.refinement_of(
        spatial_region_gnd, refinement_func=is_ontological_child_web, with_context=False
    )
    assert not one_dim_spat_gnd.refinement_of(
        spatial_region, refinement_func=is_ontological_child_web, with_context=False
    )
    assert one_dim_spat_gnd.refinement_of(
        spatial_region_gnd, refinement_func=is_ontological_child_web, with_context=True
    )
    assert not one_dim_spat_gnd.refinement_of(
        spatial_region, refinement_func=is_ontological_child_web, with_context=True
    )
    assert one_dim_spat_gnd_ctx.refinement_of(
        one_dim_spat_gnd, refinement_func=is_ontological_child_web, with_context=True
    )

    # test ungrounded
    assert not spatial_region.refinement_of(
        one_dim_spat, refinement_func=is_ontological_child_web, with_context=False
    )
    spatial_region_ctx = spatial_region.with_context(location="Stockholm")
    assert spatial_region_ctx.refinement_of(
        spatial_region, refinement_func=is_ontological_child_web, with_context=True
    )
    assert not spatial_region_ctx.refinement_of(
        spatial_region_gnd, refinement_func=is_ontological_child_web, with_context=True
    )


def test_concept_refinement_simple_context():
    spatial_region_gnd = Concept(name="spatial region", identifiers={"bfo": "0000006"})
    spatial_region_ctx = spatial_region_gnd.with_context(location="Stockholm")
    assert len(spatial_region_ctx.context)
    kw = {"refinement_func": is_ontological_child_web, "with_context": True}

    # Test both empty
    assert spatial_region_gnd.refinement_of(spatial_region_gnd, **kw)

    # Test refined has context, other does not
    assert spatial_region_ctx.refinement_of(spatial_region_gnd, **kw)

    # Test other has context, refined does not
    assert not spatial_region_gnd.refinement_of(spatial_region_ctx, **kw)


def test_concept_refinement_context():
    spatial_region_gnd = Concept(name="spatial region", identifiers={"bfo": "0000006"})
    spatial_region_ctx = spatial_region_gnd.with_context(location="Stockholm")
    spatial_region_more_ctx = spatial_region_gnd.with_context(location="Stockholm", year=2010)
    spatial_region_diff_ctx = spatial_region_gnd.with_context(year=2007, count=10)

    kw = {"refinement_func": is_ontological_child_web, "with_context": True}

    # Exactly equal context
    assert spatial_region_ctx.refinement_of(spatial_region_ctx, **kw)

    # Refined is subset of other
    assert not spatial_region_ctx.refinement_of(spatial_region_more_ctx, **kw)

    # Different contexts
    assert not spatial_region_more_ctx.refinement_of(spatial_region_diff_ctx, **kw)

    # Other is subset of refined
    assert spatial_region_more_ctx.refinement_of(spatial_region_ctx, **kw)


def test_provide_refinement_func():
    spatial_region_gnd = Concept(name="spatial region", identifiers={"bfo": "0000006"})
    two_dim_region_gnd = Concept(
        name="two-dimensional spatial region", identifiers={"bfo": "0000009"}
    )

    # This random function only check bfo grounded entities and the
    # identifier numbers, which is probably not a good idea in a real use case
    def refiner_func(child: str, parent: str) -> bool:
        if child.startswith("bfo") and parent.startswith("bfo"):
            child_id = int(child.split(":")[1])
            parent_id = int(parent.split(":")[1])
            return child_id > parent_id

        return False

    assert two_dim_region_gnd.refinement_of(spatial_region_gnd, refinement_func=refiner_func)


def test_get_curie_default():
    infected = Concept(
        name="Infected",
        identifiers={
            "ido": "0000511",
            "ncit": "C171133",
            "biomodels.species": "BIOMD0000000970:Infected",
        },
    )
    assert infected.get_curie() == ("ido", "0000511")

    infected_biomodels = Concept(
        name="Infected",
        identifiers={
            "biomodels.species": "BIOMD0000000970:Infected",
        },
    )
    assert infected_biomodels.get_curie() == ("", "Infected")


def test_get_curie_custom():
    infected = Concept(
        name="Infected",
        identifiers={
            "ido": "0000511",
            "ncit": "C171133",
            "biomodels.species": "BIOMD0000000970:Infected",
        },
    )

    custom_config = Config(prefix_priority=["ncit"],
                           prefix_exclusions=["biomodels.species", "ido"])
    assert infected.get_curie(config=custom_config) == ("ncit", "C171133")


def test_rate_json():
    t = NaturalDegradation(subject=Concept(name='x'),
                           rate_law=sympy.Mul(2, sympy.Symbol('x')))
    jj = json.loads(t.json())
    assert jj.get('rate_law') == '2*x', jj
    t2 = Template.from_json(jj)
    assert isinstance(t2, NaturalDegradation)
    assert isinstance(t2.rate_law, sympy.Expr)
    assert t2.rate_law.args[0].args[1].name == 'x'
    t3 = Template.from_json(jj, rate_symbols={'x': sympy.Symbol('y')})
    assert isinstance(t3.rate_law, sympy.Expr)
    assert t3.rate_law.args[0].args[1].name == 'y'


def test_different_class_refinement():
    s = Concept(name='s')
    o = Concept(name='o')
    c1 = Concept(name='c1')
    c2 = Concept(name='c2')

    t1 = NaturalConversion(subject=s, outcome=o)
    t2 = ControlledConversion(subject=s, outcome=o, controller=c1)
    t3 = GroupedControlledConversion(subject=s, outcome=o,
                                     controllers=[c1, c2])

    assert t2.refinement_of(t1, refinement_func=is_ontological_child_web)
    assert t3.refinement_of(t1, refinement_func=is_ontological_child_web)
    assert t3.refinement_of(t2, refinement_func=is_ontological_child_web)

    t4 = ControlledConversion(subject=c1, outcome=o, controller=c1)
    assert not t4.refinement_of(t1, refinement_func=is_ontological_child_web)


def test_extend_template_model():
    from copy import deepcopy as _d

    s = Concept(name='s')
    o = Concept(name='o')
    c1 = Concept(name='c1')
    c2 = Concept(name='c2')

    t1 = NaturalConversion(subject=s, outcome=o)
    t2 = ControlledConversion(subject=s, outcome=o, controller=c1)
    t3 = GroupedControlledConversion(subject=s, outcome=o,
                                     controllers=[c1, c2])
    tm = TemplateModel(templates=[t1, t2, t3], parameters={}, initials={})

    t4 = ControlledConversion(subject=c1, outcome=o, controller=c1)

    test_initial = Initial(concept=_d(s), expression=sympy.Symbol('s'))
    test_param = Parameter(name='test_param')
    initial_mapping = {'test_initial': test_initial}
    parameter_mapping = {'test_param': test_param}

    tm2 = tm.add_template(template=t4,
                          initial_mapping=initial_mapping,
                          parameter_mapping=parameter_mapping)
    assert tm2.templates == [t1, t2, t3, t4]


def test_set_rate_law():
    s = Concept(name='s')
    o = Concept(name='o')
    t = NaturalConversion(subject=s, outcome=o, name='tx')

    # String rate
    t.set_rate_law('beta * s * o', local_dict={'beta': sympy.Symbol('beta'),
                                               's': sympy.Symbol('s'),
                                               'o': sympy.Symbol('o')})
    assert isinstance(t.rate_law, SympyExprStr)
    assert sorted(t.rate_law.args[0].args[0].free_symbols)[0].name == 'beta'

    rate = sympy.Symbol('beta') * sympy.Symbol('s') * sympy.Symbol('o')
    t.set_rate_law(rate)
    assert isinstance(t.rate_law, SympyExprStr)
    assert sorted(t.rate_law.args[0].args[0].free_symbols)[0].name == 'beta'

    rate_s = SympyExprStr(rate)
    t.set_rate_law(rate)
    assert isinstance(t.rate_law, SympyExprStr)
    assert sorted(t.rate_law.args[0].args[0].free_symbols)[0].name == 'beta'

    tm = TemplateModel(templates=[t])
    tm.set_rate_law('tx', rate_law='beta * s * o',
                    local_dict={'beta': sympy.Symbol('beta'),
                                's': sympy.Symbol('s'),
                                'o': sympy.Symbol('o')})

    assert isinstance(tm.templates[0].rate_law, SympyExprStr)
    assert sorted(tm.templates[0].rate_law.args[0].args[0].
                  free_symbols)[0].name == 'beta'
