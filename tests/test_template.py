from mira.metamodel import ControlledConversion, Concept, NaturalConversion


def test_templates_equal():
    c1 = ControlledConversion(
        subject=Concept(name="susceptible"),
        outcome=Concept(name="infected"),
        controller=Concept(name="infected"),
    )
    c2 = ControlledConversion(
        subject=Concept(name="susceptible"),
        outcome=Concept(name="infected"),
        controller=Concept(name="infected"),
    )
    c2_w_ctx = c2.with_context(location="Stockholm")
    assert c1.is_equal_to(c2, with_context=False)
    assert not c1.is_equal_to(c2_w_ctx, with_context=True)
    assert c1.is_equal_to(c2_w_ctx, with_context=False)


def test_concepts_equal():
    c1 = Concept(name="infected population", identifiers={"ido": "0000511"})
    c1_w_ctx = c1.with_context(location="Berlin")
    c2 = Concept(name="infected population", identifiers={"ido": "0000511"})
    c2_w_ctx = c2.with_context(location="Stockholm")

    assert c1.is_equal_to(c2)
    assert not c1_w_ctx.is_equal_to(c2_w_ctx, with_context=True)
    assert c1_w_ctx.is_equal_to(c2_w_ctx, with_context=False)


def test_template_type_inequality():
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
        assert isinstance(exc, TypeError)
        assert "ControlledConversion" in str(exc) and "NaturalConversion" in str(exc)
    else:
        raise AssertionError("Expected TypeError")


def test_class_incompatibility():
    infected = Concept(name="infected population", identifiers={"ido": "0000511"})
    immune = Concept(name="immune population", identifiers={"ido": "0000592"})
    nc = NaturalConversion(subject=infected, outcome=immune)

    try:
        infected.is_equal_to(nc)
    except Exception as exc:
        assert isinstance(exc, TypeError)
    else:
        raise AssertionError("Expected NotImplementedError")

    try:
        nc.is_equal_to(infected)
    except Exception as exc:
        assert isinstance(exc, TypeError)
    else:
        raise AssertionError("Expected NotImplementedError")
