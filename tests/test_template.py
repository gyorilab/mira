from mira.metamodel import ControlledConversion, Concept


def test_templates_equal():
    c1 = ControlledConversion(
            subject=Concept(name='susceptible'),
            outcome=Concept(name='infected'),
            controller=Concept(name='infected')
        )
    c2 = ControlledConversion(
            subject=Concept(name='susceptible'),
            outcome=Concept(name='infected'),
            controller=Concept(name='infected')
        )
    c2_w_ctx = c2.with_context(location="Stockholm")
    assert c1.is_equal_to(c2, with_context=False)
    assert not c1.is_equal_to(c2_w_ctx, with_context=True)
    assert c1.is_equal_to(c2_w_ctx, with_context=False)


def test_concepts_equal():
    c1 = Concept(name='infected population', identifiers={'ido': '0000511'})
    c1_w_ctx = c1.with_context(location="Berlin")
    c2 = Concept(name='infected population', identifiers={'ido': '0000511'})
    c2_w_ctx = c2.with_context(location="Stockholm")

    assert c1.is_equal_to(c2)
    assert not c1_w_ctx.is_equal_to(c2_w_ctx, with_context=True)
    assert c1_w_ctx.is_equal_to(c2_w_ctx, with_context=False)

