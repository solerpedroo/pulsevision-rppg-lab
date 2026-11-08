from collections import Counter
from typing import Any

import numpy as np
from rppg_core.metrics.errors import paired_metrics

METHODS = ("GREEN", "CHROM", "POS")
ERRORS = ("mae", "rmse", "medae", "bias")


def summarize(
    rows: list[dict[str, Any]],
    *,
    seed: int,
    bootstrap_samples: int,
    participant_ids: list[str] | None = None,
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for method in METHODS:
        selected = [row for row in rows if row["method"] == method]
        participants: dict[str, Any] = {}
        for participant in sorted(
            set(participant_ids or []) | {row["participant_id"] for row in selected}
        ):
            group = [row for row in selected if row["participant_id"] == participant]
            eligible = [row for row in group if row["eligible"]]
            accepted = [row for row in eligible if row["bpm"] is not None]
            metrics = paired_metrics(
                np.array([row["bpm"] for row in accepted], dtype=float),
                np.array([row["reference_bpm"] for row in accepted], dtype=float),
            )
            participants[participant] = {
                **metrics,
                "eligible_windows": len(eligible),
                "accepted_windows": len(accepted),
                "abstained_windows": len(eligible) - len(accepted),
                "excluded_windows": len(group) - len(eligible),
                "coverage": len(accepted) / len(eligible) if eligible else None,
                "mean_estimated_bpm": float(np.mean([x["bpm"] for x in accepted]))
                if accepted
                else None,
                "mean_reference_bpm": float(np.mean([x["reference_bpm"] for x in accepted]))
                if accepted
                else None,
            }
        evaluable = [value for value in participants.values() if value["n"] > 0]
        macro = {
            key: float(np.mean([p[key] for p in evaluable])) if evaluable else None
            for key in ERRORS
        }
        ci = None
        if len(evaluable) >= 3:
            values = np.array([[p[key] for key in ERRORS] for p in evaluable])
            indices = np.random.default_rng(seed).integers(
                len(values), size=(bootstrap_samples, len(values))
            )
            draws = values[indices].mean(axis=1)
            bounds = np.percentile(draws, [2.5, 97.5], axis=0)
            ci = {key: bounds[:, index].tolist() for index, key in enumerate(ERRORS)}
        eligible = [row for row in selected if row["eligible"]]
        accepted = [row for row in eligible if row["bpm"] is not None]
        coverage_subjects = [
            p["coverage"] for p in participants.values() if p["coverage"] is not None
        ]
        output[method] = {
            "participants": participants,
            "macro_errors": macro,
            "aggregation": "equal_weight_mean_of_participant_error_metrics",
            "eligible_windows": len(eligible),
            "accepted_windows": len(accepted),
            "abstained_windows": len(eligible) - len(accepted),
            "excluded_windows": len(selected) - len(eligible),
            "window_coverage": len(accepted) / len(eligible) if eligible else None,
            "participant_macro_coverage": float(np.mean(coverage_subjects))
            if coverage_subjects
            else None,
            "reason_counts": dict(
                Counter(
                    reason
                    for row in eligible
                    if row["bpm"] is None
                    for reason in set(row["reasons"])
                )
            ),
            "exclusion_counts": dict(
                Counter(row["exclusion_reason"] for row in selected if not row["eligible"])
            ),
            "bootstrap_subject_ci95": ci,
            "bootstrap_samples": bootstrap_samples,
            "bootstrap_unit": "participant",
            "seed": seed,
            "ci_unavailable_reason": "fewer_than_three_evaluable_participants"
            if ci is None
            else None,
            "evaluable_participants": len(evaluable),
            "declared_participants": len(participants),
            "participants_with_eligible_windows": len(coverage_subjects),
            "participants_without_error_pairs": [
                key for key, p in participants.items() if not p["n"]
            ],
            "participant_mean_agreement": paired_metrics(
                np.array([p["mean_estimated_bpm"] for p in evaluable], dtype=float),
                np.array([p["mean_reference_bpm"] for p in evaluable], dtype=float),
            ),
        }
    return output
