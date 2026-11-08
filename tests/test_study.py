import json
import shutil

import pytest
from pydantic import ValidationError
from rppg_types.benchmark import BenchmarkReview

from benchmarks.analysis.review import read_run, summaries
from benchmarks.manifest import BenchmarkError
from benchmarks.study import create_demo, run_study


@pytest.fixture(scope="module")
def study(tmp_path_factory):
    root = tmp_path_factory.mktemp("study") / "demo"
    review = create_demo(root)
    return root, BenchmarkReview.model_validate_json(review.read_text())


def test_real_runner_to_review_reports_and_figures(study):
    root, review = study
    assert {r.window_s for r in review.runs} == {10, 20, 30}
    assert all(r.result_kind == "synthetic_demonstration" for r in review.runs)
    assert all(len(r.manifest_sha256) == 64 for r in review.runs)
    report = root / "results/review/report.md"
    assert "ARTIFICIAL" in report.read_text()
    assert "Pendências" in report.read_text()
    assert (root / "results/review/comparison.png").read_bytes().startswith(b"\x89PNG")
    for run in review.runs:
        raw = json.loads((root / f"results/{run.run_id}/benchmark-v1.json").read_text())
        computed = summaries(
            BenchmarkReview(
                title="Test", hypothesis="Artificial", runs=[run], pending=[], limitations=[]
            )
        )[run.run_id]
        assert computed == raw["summary"]


def test_study_freeze_rejects_plan_or_input_changes(study, tmp_path):
    root, _ = study
    copy = tmp_path / "copy"
    shutil.copytree(root, copy)
    plan = copy / "study.json"
    data = json.loads(plan.read_text())
    data["hypothesis"] += " changed"
    plan.write_text(json.dumps(data))
    with pytest.raises(BenchmarkError, match="changed"):
        run_study(plan, copy / "study-lock.json", copy / "new-result")
    assert not (copy / "new-result").exists()
    shutil.copyfile(root / "study.json", plan)
    csv = copy / "inputs/synthetic01.csv"
    csv.write_text(csv.read_text() + "\n")
    with pytest.raises(BenchmarkError):
        run_study(plan, copy / "study-lock.json", copy / "new-result")
    assert not (copy / "new-result").exists()


def test_contract_rejects_inconsistent_eligibility_duplicates_and_mixed_kind(study):
    _, review = study
    data = review.model_dump(mode="json")
    row = next(w for w in data["runs"][0]["windows"] if w["eligible"])
    row["reference_bpm"] = None
    with pytest.raises(ValidationError, match="reference"):
        BenchmarkReview.model_validate(data)
    data = review.model_dump(mode="json")
    data["runs"][0]["windows"].append(data["runs"][0]["windows"][0])
    with pytest.raises(ValidationError, match="Duplicate"):
        BenchmarkReview.model_validate(data)
    data = review.model_dump(mode="json")
    data["runs"][1]["dataset"] = "UBFC-rPPG"
    data["runs"][1]["result_kind"] = "dataset_evaluation"
    with pytest.raises(ValidationError, match="mix"):
        BenchmarkReview.model_validate(data)


def test_no_accepted_pairs_have_no_error_metric(study):
    _, review = study
    run = review.runs[0].model_copy(deep=True)
    for row in run.windows:
        row.bpm = None
        row.reasons = ["no_face"]
    result = summaries(
        BenchmarkReview(
            title="Artificial",
            hypothesis="No accepted data",
            runs=[run],
            pending=[],
            limitations=[],
        )
    )[run.run_id]
    for method in result.values():
        assert method["macro_errors"]["mae"] is None
        assert method["window_coverage"] == 0
        assert method["participants_without_error_pairs"]


def test_converter_requires_known_source_schema(tmp_path):
    source = tmp_path / "bad.json"
    source.write_text('{"schema_version":"unsupported"}')
    with pytest.raises(ValueError, match="benchmark-v1"):
        read_run(source, "unknown")
