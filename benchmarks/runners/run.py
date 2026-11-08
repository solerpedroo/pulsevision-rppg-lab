"""Freeze/run a declared benchmark. Never downloads datasets or infers synchronization."""

import argparse
import csv
import json
import platform
import shutil
import sys
import tempfile
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np
from rppg_core.acquisition.errors import VideoError
from rppg_core.estimation.pipeline import analyze_trace
from rppg_core.face.detector import FaceError
from rppg_core.roi.extract_rgb import export_csv
from rppg_core.signals.analyze_rgb import load_trace_csv
from rppg_core.signals.config import SignalConfig
from rppg_core.signals.temporal import (
    FloatArray,
    SignalInputError,
    SignalQualityError,
    uniform_trace,
)
from rppg_types.models import Method

from benchmarks.adapters.reference import (
    ReferenceError,
    read_hr_csv,
    read_pure_reference,
    read_ubfc_reference,
)
from benchmarks.analysis.aggregate import summarize
from benchmarks.manifest import (
    BenchmarkError,
    digest,
    freeze,
    load_manifest,
    resolve,
    verify_lock,
)

METHODS: tuple[Method, ...] = ("GREEN", "CHROM", "POS")


def reference_support(
    timestamps: FloatArray,
    start_s: float,
    end_s: float,
    config: SignalConfig,
) -> tuple[float, float]:
    """Derive common spectral support from timing ONLY, independently of method acceptance."""
    selected = timestamps[(timestamps >= start_s - 1e-9) & (timestamps < end_s - 1e-9)]
    if len(selected) > 1:
        try:
            grid = uniform_trace(
                selected,
                np.zeros((len(selected), 3)),
                max_gap_s=config.max_gap_s,
                max_interval_ratio=config.max_interval_ratio,
            )
            trim = int(np.ceil(config.edge_trim_s * grid.fs - 1e-9))
            if trim > 0 and 2 * trim < len(grid.timestamps_s):
                return (
                    float(grid.timestamps_s[trim]),
                    float(grid.timestamps_s[-trim - 1] + 1 / grid.fs),
                )
        except SignalQualityError:
            pass
    # No usable acquisition support: keep a predeclared reference interval and abstention.
    return start_s + config.edge_trim_s, end_s - config.edge_trim_s


def run_benchmark(
    manifest_path: Path,
    lock_path: Path,
    output: Path,
    *,
    split: str = "development",
) -> dict[str, Any]:
    frozen = verify_lock(manifest_path, lock_path)
    manifest = load_manifest(manifest_path)
    if split not in manifest.splits:
        raise BenchmarkError("Requested split has no declared participants")
    if manifest.dataset == "synthetic" and split == "test":
        raise BenchmarkError(
            "Synthetic demonstration cannot be declared a final physiological test"
        )
    selected = [x for x in manifest.sessions if x.participant_id in manifest.splits[split]]
    if not selected:
        raise BenchmarkError("No sessions selected; refuse empty benchmark")
    base = manifest_path.resolve().parent
    output.mkdir(parents=True, exist_ok=False)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    timings: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        for session in selected:
            key = {
                "participant_id": session.participant_id,
                "session_id": session.session_id,
                "condition": session.condition,
            }
            if not session.alignment.verified:
                failures.append({**key, "reason": "unverified_alignment"})
                continue
            stage_start = time.perf_counter()
            session_rows: list[dict[str, Any]] = []
            session_timings: list[dict[str, Any]] = []
            temporary: tempfile.TemporaryDirectory[str] | None = None
            reference_path = resolve(base, session.reference)
            try:
                readers = {
                    "ubfc_text": read_ubfc_reference,
                    "pure_json": read_pure_reference,
                    "sensor_hr_csv": read_hr_csv,
                }
                reference = readers[session.reference_format](reference_path).aligned(
                    session.alignment.reference_origin_s, session.alignment.offset_s
                )
                if session.rgb_csv:
                    trace_path = resolve(base, session.rgb_csv)
                else:
                    temporary = tempfile.TemporaryDirectory(dir=output, prefix="trace-")
                    trace_path = Path(temporary.name) / "rgb.csv"
                    export_csv(
                        resolve(base, session.video or ""),
                        resolve(base, manifest.model_path or ""),
                        trace_path,
                    )
                trace = load_trace_csv(trace_path, manifest.roi)
                acquisition_s = time.perf_counter() - stage_start
                if len(trace.timestamps) < 2:
                    raise SignalInputError("insufficient_rgb_trace")
                margin = max(
                    manifest.signal.edge_trim_s,
                    manifest.methods.projection_window_s
                    + 2 * min(manifest.signal.max_gap_s, float(np.diff(trace.timestamps).max())),
                )
                config = replace(manifest.signal, edge_trim_s=margin)
                for method in METHODS:
                    analysis_start = time.perf_counter()
                    analyses = list(
                        analyze_trace(
                            trace.timestamps,
                            trace.rgb,
                            method=method,
                            roi=manifest.roi,
                            valid=trace.valid,
                            evidence=trace.evidence,
                            config=config,
                            method_config=manifest.methods,
                            quality_config=manifest.quality,
                        )
                    )
                    analysis_s = time.perf_counter() - analysis_start
                    session_timings.append(
                        {
                            **key,
                            "method": method,
                            "acquisition_reference_io_s": acquisition_s,
                            "dsp_seconds": analysis_s,
                            "input_samples": len(trace.timestamps),
                            "input_span_s": float(trace.timestamps[-1] - trace.timestamps[0]),
                            "dsp_seconds_per_input_minute": analysis_s
                            * 60
                            / float(trace.timestamps[-1] - trace.timestamps[0]),
                            "dsp_samples_per_second": len(trace.timestamps) / analysis_s
                            if analysis_s
                            else None,
                            "trace_sha256": digest(trace_path),
                            "effective_signal_config": asdict(config),
                        }
                    )
                    for analysis in analyses:
                        estimate = analysis.estimate
                        start, end = estimate.window.start_s, estimate.window.end_s
                        truth = None
                        exclusion = None
                        ref_start, ref_end = reference_support(trace.timestamps, start, end, config)
                        if end - start < config.window_s - 1e-8:
                            exclusion = "incomplete_analysis_window"
                        else:
                            try:
                                truth = reference.window_hr(
                                    ref_start, ref_end, manifest.reference_max_gap_s
                                )
                            except ReferenceError as exc:
                                exclusion = str(exc)
                        session_rows.append(
                            {
                                **key,
                                "method": method,
                                "start_s": start,
                                "end_s": end,
                                "eligible": exclusion is None,
                                "exclusion_reason": exclusion,
                                "reference_start_s": ref_start,
                                "reference_end_s": ref_end,
                                "reference_bpm": truth,
                                "error_bpm": estimate.bpm - truth
                                if exclusion is None
                                and estimate.bpm is not None
                                and truth is not None
                                else None,
                                "bpm": estimate.bpm,
                                "reasons": estimate.reasons,
                                "estimate": estimate.model_dump(mode="json"),
                            }
                        )
                rows.extend(session_rows)
                timings.extend(session_timings)
            except (ReferenceError, SignalInputError, VideoError, FaceError, OSError) as exc:
                failures.append({**key, "reason": str(exc)})
            finally:
                if temporary is not None:
                    temporary.cleanup()
        report: dict[str, Any] = {
            "schema_version": "benchmark-v1",
            "result_kind": "synthetic_demonstration"
            if manifest.dataset == "synthetic"
            else "dataset_evaluation",
            "dataset": manifest.dataset,
            "dataset_version": manifest.dataset_version,
            "protocol_version": manifest.protocol_version,
            "split": split,
            "frozen": frozen,
            "manifest_configuration": {
                "signal": asdict(manifest.signal),
                "methods": asdict(manifest.methods),
                "quality": asdict(manifest.quality),
                "roi": manifest.roi,
                "reference_rule": "time_weighted_sensor_hr_common_spectral_interior",
                "reference_max_gap_s": manifest.reference_max_gap_s,
            },
            "selected_sessions": len(selected),
            "session_alignment": [
                {
                    "participant_id": item.participant_id,
                    "session_id": item.session_id,
                    "condition": item.condition,
                    "reference_format": item.reference_format,
                    "input_mode": "rgb_csv" if item.rgb_csv else "local_video",
                    "verified": item.alignment.verified,
                    "reference_origin_s": item.alignment.reference_origin_s,
                    "offset_s": item.alignment.offset_s,
                    "evidence_sha256": digest(resolve(base, item.alignment.evidence_file))
                    if item.alignment.evidence_file
                    else None,
                }
                for item in selected
            ],
            "session_failures": failures,
            "sessions_without_complete_comparison": len(failures),
            "summary": summarize(
                rows,
                seed=manifest.seed,
                bootstrap_samples=manifest.bootstrap_samples,
                participant_ids=sorted({x.participant_id for x in selected}),
            ),
            "summary_by_condition": {
                condition: summarize(
                    [row for row in rows if row["condition"] == condition],
                    seed=manifest.seed,
                    bootstrap_samples=manifest.bootstrap_samples,
                    participant_ids=sorted(
                        {x.participant_id for x in selected if x.condition == condition}
                    ),
                )
                for condition in sorted({x.condition for x in selected})
            },
            "timings": timings,
            "windows": rows,
            "hardware": {
                "system": platform.system(),
                "machine": platform.machine(),
                "processor": platform.processor() or "unavailable",
            },
            "limitations": [
                "Synthetic results are not physiological accuracy or clinical validation."
                if manifest.dataset == "synthetic"
                else "Dataset terms govern all derived artifacts.",
                "Alignment is externally recorded; never inferred from estimation error.",
                "Sensor-reported HR may be smoothed/lagged; offset must not be optimized on test.",
                "Bland-Altman windows have repeated measures; pooled limits are descriptive only.",
                "Subject bootstrap is conditional on accepted pairs; report coverage and failures.",
            ],
        }
        from benchmarks.analysis.plots import save_plots

        save_plots(
            rows, report["summary"], output / "figures", synthetic=manifest.dataset == "synthetic"
        )
        report["runtime_seconds_before_serialization"] = time.perf_counter() - started
        (output / "benchmark-v1.json").write_text(
            json.dumps(report, indent=2, allow_nan=False) + "\n"
        )
        with (output / "windows.csv").open("w", newline="") as handle:
            fields = [
                "participant_id",
                "session_id",
                "condition",
                "method",
                "start_s",
                "end_s",
                "eligible",
                "exclusion_reason",
                "reference_start_s",
                "reference_end_s",
                "reference_bpm",
                "bpm",
                "error_bpm",
                "reasons",
            ]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        field: json.dumps(row[field]) if field == "reasons" else row[field]
                        for field in fields
                    }
                )
        with (output / "participants.csv").open("w", newline="") as handle:
            fields = [
                "method",
                "participant_id",
                "n",
                "mae",
                "rmse",
                "medae",
                "bias",
                "pearson_r",
                "loa_low",
                "loa_high",
                "eligible_windows",
                "accepted_windows",
                "abstained_windows",
                "excluded_windows",
                "coverage",
            ]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for method, group in report["summary"].items():
                for participant, metrics in group["participants"].items():
                    values = {**metrics, "method": method, "participant_id": participant}
                    writer.writerow({field: values[field] for field in fields})
        write_markdown(report, output / "benchmark-v1.md")
        return report
    except Exception:
        shutil.rmtree(output)
        raise


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Benchmark v1",
        "",
        "**ARTIFICIAL DEMONSTRATION — no physiological accuracy claim.**"
        if report["result_kind"] == "synthetic_demonstration"
        else "Dataset evaluation; experimental use only.",
        "",
        f"Dataset: {report['dataset']} · split: {report['split']}",
        f"Manifest SHA256: {report['frozen']['manifest_sha256']}",
        "",
        f"Selected sessions: {report['selected_sessions']}; "
        f"sessions excluded without known window counts: {len(report['session_failures'])}.",
        "",
    ]
    for method, summary in report["summary"].items():
        lines += [
            f"## {method}",
            "",
            f"Eligible: {summary['eligible_windows']}; accepted: {summary['accepted_windows']}; "
            f"abstained: {summary['abstained_windows']}; "
            f"pre-eligibility window exclusions: {summary['excluded_windows']}.",
            f"Window coverage: {summary['window_coverage']}; "
            f"participant macro coverage: {summary['participant_macro_coverage']}.",
            "Errors (equal-weight mean of evaluable participant metrics): "
            + json.dumps(summary["macro_errors"]),
            "",
            "Participant metrics are in benchmark-v1.json; windows.csv preserves failures.",
            "",
        ]
    lines += ["## Limitations", "", *["- " + line for line in report["limitations"]]]
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze_parser = commands.add_parser("freeze")
    freeze_parser.add_argument("manifest", type=Path)
    freeze_parser.add_argument("--output", required=True, type=Path)
    runner = commands.add_parser("run")
    runner.add_argument("manifest", type=Path)
    runner.add_argument("--lock", required=True, type=Path)
    runner.add_argument("--output", required=True, type=Path)
    runner.add_argument(
        "--split", choices=["development", "validation", "test"], default="development"
    )
    args = parser.parse_args()
    try:
        if args.command == "freeze":
            freeze(args.manifest, args.output)
            print(json.dumps({"status": "configuration_frozen"}))
        else:
            result = run_benchmark(args.manifest, args.lock, args.output, split=args.split)
            print(
                json.dumps(
                    {
                        "result_kind": result["result_kind"],
                        "selected_sessions": result["selected_sessions"],
                        "session_failures": len(result["session_failures"]),
                    }
                )
            )
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
