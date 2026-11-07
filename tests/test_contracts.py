import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from rppg_types.models import EstimateResult, RGBSample, Window

FIXTURE = json.loads(Path("tests/fixtures/contracts.json").read_text())


def test_shared_fixture() -> None:
    RGBSample.model_validate(FIXTURE["sample"])
    result = EstimateResult.model_validate(FIXTURE["estimate"])
    assert result.bpm is None


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_timestamp(value: float) -> None:
    with pytest.raises(ValidationError):
        RGBSample.model_validate({**FIXTURE["sample"], "timestamp_s": value})


@pytest.mark.parametrize("patch", [
    {"bpm": 72}, {"reasons": []}, {"status": "good"}, {"produced_at_s": 0},
])
def test_invalid_estimate(patch: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EstimateResult.model_validate({**FIXTURE["estimate"], **patch})


def test_reversed_window() -> None:
    with pytest.raises(ValidationError):
        Window(start_s=2, end_s=1, sample_count=0, effective_fps=0)
