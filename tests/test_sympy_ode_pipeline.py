from mira.sources.sympy_ode.agent_pipeline import (
    PhaseResult,
    ExtractionResult,
    CorrectionResult,
    PipelineResult,
)


def test_phase_result_success():
    assert PhaseResult().success
    assert PhaseResult(status="complete").success
    assert not PhaseResult(status="failed", error="boom").success


def test_best_ode_str_prefers_correction():
    result = PipelineResult(
        extraction=ExtractionResult(ode_str="extracted"),
        correction=CorrectionResult(ode_str="corrected"),
    )
    assert result.best_ode_str == "corrected"


def test_best_ode_str_falls_back_to_extraction():
    result = PipelineResult(
        extraction=ExtractionResult(ode_str="extracted"),
        correction=CorrectionResult(status="failed", error="boom"),
    )
    assert result.best_ode_str == "extracted"


def test_best_ode_str_extraction_only():
    result = PipelineResult(extraction=ExtractionResult(ode_str="extracted"))
    assert result.best_ode_str == "extracted"


def test_best_ode_str_none_when_extraction_failed():
    result = PipelineResult(
        extraction=ExtractionResult(status="failed", error="boom")
    )
    assert result.best_ode_str is None


def test_best_ode_str_none_when_empty():
    assert PipelineResult().best_ode_str is None
