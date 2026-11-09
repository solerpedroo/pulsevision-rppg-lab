"""Predeclare/freeze/run variants of existing benchmark manifests. No dataset downloads."""

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Literal

from pydantic import Field
from rppg_types.benchmark import BenchmarkReview

from benchmarks.analysis.review import export_review, read_run
from benchmarks.manifest import BenchmarkError, StrictModel, code_state, digest, verify_lock
from benchmarks.runners.run import run_benchmark


class Variant(StrictModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$")
    experiment: Literal["A", "B", "C", "D", "E"]
    manifest: str
    lock: str
    split: Literal["development", "validation", "test"] = "development"


class StudyPlan(StrictModel):
    version: Literal["study-v1"] = "study-v1"
    title: str = Field(min_length=1, max_length=160)
    hypothesis: str = Field(min_length=1, max_length=4000)
    pending: list[str]
    variants: list[Variant] = Field(min_length=1, max_length=64)


def study_snapshot(plan_path: Path) -> dict[str, object]:
    plan = StudyPlan.model_validate_json(plan_path.read_text())
    if len({v.id for v in plan.variants}) != len(plan.variants):
        raise BenchmarkError("Duplicate variant ID")
    base = plan_path.resolve().parent
    variants = {}
    for variant in plan.variants:
        manifest, lock = (base / variant.manifest).resolve(), (base / variant.lock).resolve()
        verify_lock(manifest, lock)
        variants[variant.id] = {"manifest_sha256": digest(manifest), "lock_sha256": digest(lock)}
    return {
        "version": "study-lock-v1",
        "plan_sha256": digest(plan_path),
        "code": code_state(),
        "variants": variants,
    }


def freeze_study(plan: Path, lock: Path) -> None:
    value = study_snapshot(plan)
    with lock.open("x") as handle:
        handle.write(json.dumps(value, indent=2) + "\n")


def _code_identity(value: dict[str, Any]) -> dict[str, Any]:
    cloned: dict[str, Any] = json.loads(json.dumps(value))
    code = cloned.get("code")
    if isinstance(code, dict):
        code.pop("dirty", None)
    return cloned


def run_study(plan_path: Path, lock: Path, output: Path) -> BenchmarkReview:
    frozen = json.loads(lock.read_text())
    current = study_snapshot(plan_path)
    if _code_identity(frozen) != _code_identity(current):
        raise BenchmarkError("Study plan, inputs or code changed after freeze")
    plan = StudyPlan.model_validate_json(plan_path.read_text())
    output.mkdir(parents=True, exist_ok=False)
    runs = []
    try:
        for variant in plan.variants:
            directory = output / variant.id
            run_benchmark(
                plan_path.parent / variant.manifest,
                plan_path.parent / variant.lock,
                directory,
                split=variant.split,
            )
            runs.append(read_run(directory / "benchmark-v1.json", variant.id, variant.experiment))
        review = BenchmarkReview(
            title=plan.title,
            hypothesis=plan.hypothesis,
            runs=runs,
            pending=plan.pending,
            limitations=[
                "Synthetic results are infrastructure tests, not physiological accuracy.",
                "Errors are conditional on accepted pairs; "
                "coverage and exclusions must accompany them.",
                "Repeated windows are not independent; "
                "comparisons require compatible cohorts/support.",
                "Browser inspection does not independently verify source data or declared access.",
            ],
        )
        export_review(review, output / "review")
        (output / "study-lock.json").write_text(json.dumps(frozen, indent=2) + "\n")
        return review
    except Exception:
        shutil.rmtree(output)
        raise


def create_demo(output: Path) -> Path:
    """Same artificial cohort, three window lengths; never simulate anatomical ROI evidence."""
    from benchmarks.manifest import freeze
    from benchmarks.runners.synthetic import create_demo as create_inputs

    output.mkdir(parents=True, exist_ok=False)
    source = create_inputs(output / "inputs", subjects=3, duration_s=31)
    data = json.loads(source.read_text())
    variants = []
    for length in [10, 20, 30]:
        variant = json.loads(json.dumps(data))
        variant["signal"]["window_s"] = length
        path = source.parent / f"window-{length}.json"
        path.write_text(json.dumps(variant, indent=2) + "\n")
        lock = path.with_suffix(".lock.json")
        freeze(path, lock)
        variants.append(
            {
                "id": f"window-{length}",
                "experiment": "C",
                "manifest": str(path.relative_to(output)),
                "lock": str(lock.relative_to(output)),
                "split": "development",
            }
        )
    plan = StudyPlan(
        title="Demonstração artificial — janelas 10/20/30 s",
        hypothesis=(
            "Verificar a execução e inspeção de diferentes janelas na mesma "
            "coorte artificial; não concluir precisão fisiológica."
        ),
        pending=[
            "Experimentos A–E em dataset autorizado e relatório científico final pendentes.",
            "ROIs anatômicas, vídeo degradado e movimento real não foram avaliados.",
        ],
        variants=[Variant.model_validate(v) for v in variants],
    )
    path = output / "study.json"
    path.write_text(plan.model_dump_json(indent=2) + "\n")
    freeze_study(path, output / "study-lock.json")
    run_study(path, output / "study-lock.json", output / "results")
    return output / "results/review/benchmark-review-v1.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo")
    demo.add_argument("--output", type=Path, required=True)
    frozen = commands.add_parser("freeze")
    frozen.add_argument("plan", type=Path)
    frozen.add_argument("--lock", type=Path, required=True)
    run = commands.add_parser("run")
    run.add_argument("plan", type=Path)
    run.add_argument("--lock", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "demo":
        print(create_demo(args.output))
    elif args.command == "freeze":
        freeze_study(args.plan, args.lock)
    else:
        run_study(args.plan, args.lock, args.output)


if __name__ == "__main__":
    main()
