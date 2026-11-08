import json
from pathlib import Path

from rppg_types.models import EstimateResult, Experiment, QualityAssessment, RGBSample, Window

destination = Path("packages/rppg_types/schemas")
destination.mkdir(parents=True, exist_ok=True)
for model in (RGBSample, Window, EstimateResult, Experiment, QualityAssessment):
    (destination / f"{model.__name__}.json").write_text(
        json.dumps(model.model_json_schema(), indent=2) + "\n"
    )
