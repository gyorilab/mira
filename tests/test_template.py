from mira.dkg.client import Neo4jClient
from mira.metamodel import ControlledConversion, Concept, NaturalConversion


client = Neo4jClient(url="bolt://0.0.0.0:7687")


def test_templates_equal():
    infected = Concept(name='infected population',
                       identifiers={'ido': '0000511'})
    susceptible = Concept(name='susceptible population',
                          identifiers={'ido': '0000514'})
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
    assert not c1.is_equal_to(c2, with_context=False)
    assert c1_gnd.is_equal_to(c1_gnd, with_context=False)
    assert c1_gnd.is_equal_to(c1_gnd_ctx, with_context=False)
    assert not c1_gnd.is_equal_to(c1_gnd_ctx, with_context=True)
    assert not c1.is_equal_to(c2_ctx, with_context=True)
    assert not c1.is_equal_to(c2_ctx, with_context=False)


def test_concepts_equal():
    c1 = Concept(name="infected population", identifiers={"ido": "0000511"})
    c1_w_ctx = c1.with_context(location="Berlin")
    c2 = Concept(name="infected population", identifiers={"ido": "0000511"})
    c2_w_ctx = c2.with_context(location="Stockholm")

    assert c1.is_equal_to(c2)
    assert not c1_w_ctx.is_equal_to(c2_w_ctx, with_context=True)
    assert c1_w_ctx.is_equal_to(c2_w_ctx, with_context=False)


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

    try:
        c1.is_equal_to(n1)
    except Exception as exc:
        assert isinstance(exc, TypeError), "Expected TypeError"
        assert "ControlledConversion" in str(exc) and "NaturalConversion" in str(exc)
    else:
        raise AssertionError("Expected TypeError")


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

    try:
        c1.refinement_of(n1, client)
    except Exception as exc:
        assert isinstance(exc, TypeError), "Expected TypeError"
        assert "ControlledConversion" in str(exc) and "NaturalConversion" in str(exc)
    else:
        raise AssertionError("Expected TypeError")

    try:
        n1.refinement_of(c1, None)
    except Exception as exc:
        assert isinstance(exc, TypeError), "Expected TypeError"
        assert "ControlledConversion" in str(exc) and "NaturalConversion" in str(exc)
    else:
        raise AssertionError("Expected TypeError")


def test_class_incompatibility_is_equal():
    infected = Concept(name="infected population", identifiers={"ido": "0000511"})
    immune = Concept(name="immune population", identifiers={"ido": "0000592"})
    nc = NaturalConversion(subject=infected, outcome=immune)

    try:
        infected.is_equal_to(nc)
    except Exception as exc:
        assert isinstance(exc, TypeError), "Expected TypeError"
    else:
        raise AssertionError("Expected TypeError")

    try:
        nc.is_equal_to(infected)
    except Exception as exc:
        assert isinstance(exc, TypeError), "Expected TypeError"
    else:
        raise AssertionError("Expected TypeError")


def test_class_incompatibility_refinement():
    infected = Concept(name="infected population", identifiers={"ido": "0000511"})
    immune = Concept(name="immune population", identifiers={"ido": "0000592"})
    natural_conversion = NaturalConversion(subject=infected, outcome=immune)

    try:
        infected.refinement_of(natural_conversion, None)
    except Exception as exc:
        assert isinstance(exc, TypeError), "Expected TypeError"
    else:
        raise AssertionError("Expected TypeError")

    try:
        natural_conversion.is_equal_to(infected)
    except Exception as exc:
        assert isinstance(exc, TypeError), "Expected TypeError"
    else:
        raise AssertionError("Expected TypeError")


# test refinement for Templates
def test_template_refinement():
    infected = Concept(name="infected population", identifiers={"ido": "0000511"})
    immune = Concept(name="immune population", identifiers={"ido": "0000592"})
    natural_conversion = NaturalConversion(subject=infected, outcome=immune)
    nc_context = natural_conversion.with_context(location="Boston")
    assert nc_context.refinement_of(natural_conversion, client, with_context=True)


def test_concept_refinement_grounding():
    # spatial region
    spatial_region = Concept(name="spatial region")
    spatial_region_gnd = Concept(name="spatial region", identifiers={"bfo": "0000006"})
    # one-dimensional spatial region
    one_dim_spat = Concept(name="one-dimensional spatial region")
    one_dim_spat_gnd = Concept(
        name="one-dimensional spatial region", identifiers={"bfo": "0000026"}
    )
    # test grounded
    assert one_dim_spat_gnd.refinement_of(spatial_region_gnd, dkg_client=client, with_context=False)
    assert not one_dim_spat_gnd.refinement_of(spatial_region, dkg_client=client, with_context=False)
    assert one_dim_spat_gnd.refinement_of(spatial_region_gnd, dkg_client=client, with_context=True)
    assert not one_dim_spat_gnd.refinement_of(spatial_region, dkg_client=client, with_context=True)

    # test ungrounded
    assert not spatial_region.refinement_of(one_dim_spat, dkg_client=client, with_context=False)
    spatial_region_ctx = spatial_region.with_context(location="Stockholm")
    assert spatial_region_ctx.refinement_of(spatial_region, dkg_client=client, with_context=True)
    assert spatial_region_ctx.refinement_of(
        spatial_region_gnd, dkg_client=client, with_context=True
    )


def test_concept_refinement_simple_context():
    spatial_region_gnd = Concept(name="spatial region", identifiers={"bfo": "0000006"})
    spatial_region_ctx = spatial_region_gnd.with_context(location="Stockholm")
    assert len(spatial_region_ctx.context)
    kw = {"dkg_client": client, "with_context": True}

    # Test both empty
    assert not spatial_region_gnd.refinement_of(spatial_region_gnd, **kw)

    # Test refined has context, other does not
    assert spatial_region_ctx.refinement_of(spatial_region_gnd, **kw)

    # Test other has context, refined does not
    assert not spatial_region_gnd.refinement_of(spatial_region_ctx, **kw)


def test_concept_refinement_context():
    spatial_region_gnd = Concept(name="spatial region", identifiers={"bfo": "0000006"})
    spatial_region_ctx = spatial_region_gnd.with_context(location="Stockholm")
    spatial_region_more_ctx = spatial_region_gnd.with_context(location="Stockholm", year=2010)
    spatial_region_diff_ctx = spatial_region_gnd.with_context(year=2007, count=10)

    kw = {"dkg_client": client, "with_context": True}

    # Exactly equal context
    assert not spatial_region_ctx.refinement_of(spatial_region_ctx, **kw)

    # Refined is subset of other
    assert not spatial_region_ctx.refinement_of(spatial_region_more_ctx, **kw)

    # Different contexts
    assert not spatial_region_more_ctx.refinement_of(spatial_region_diff_ctx, **kw)

    # Other is subset of refined
    assert spatial_region_more_ctx.refinement_of(spatial_region_ctx, **kw)
