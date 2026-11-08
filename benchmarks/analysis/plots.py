from pathlib import Path
from typing import Any

import numpy as np
from rppg_core.metrics.errors import paired_metrics


def save_plots(
    rows: list[dict[str, Any]], summary: dict[str, Any], output: Path, *, synthetic: bool
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output.mkdir(parents=True)
    title = "ARTIFICIAL demonstration" if synthetic else "Experimental dataset evaluation"
    for method in ("GREEN", "CHROM", "POS"):
        accepted = [
            r for r in rows if r["method"] == method and r["eligible"] and r["bpm"] is not None
        ]
        figure, axes = plt.subplots(2, 2, figsize=(11, 8), layout="constrained")
        figure.suptitle(title + " — " + method)
        if accepted:
            reference = np.array([r["reference_bpm"] for r in accepted])
            estimate = np.array([r["bpm"] for r in accepted])
            error, mean = estimate - reference, (estimate + reference) / 2
            axes[0, 0].scatter(reference, estimate, s=12)
            low, high = (
                float(min(reference.min(), estimate.min())) - 3,
                float(max(reference.max(), estimate.max())) + 3,
            )
            axes[0, 0].plot([low, high], [low, high], "--", color="gray")
            axes[0, 0].set(
                xlabel="Reference sensor HR (BPM)",
                ylabel="Estimated BPM",
                title="Temporally paired accepted windows",
            )
            axes[0, 1].scatter(mean, error, s=12)
            descriptive = paired_metrics(estimate, reference)
            for name in ("bias", "loa_low", "loa_high"):
                if descriptive[name] is not None:
                    axes[0, 1].axhline(descriptive[name], linestyle="--", label=name)
            axes[0, 1].set(
                xlabel="Mean estimate/reference (BPM)",
                ylabel="Estimate − reference (BPM)",
                title="Bland–Altman: repeated windows, descriptive only",
            )
            axes[0, 1].legend()
            groups = sorted({r["participant_id"] for r in accepted})
            axes[1, 0].boxplot(
                [
                    [
                        r["bpm"] - r["reference_bpm"]
                        for r in accepted
                        if r["participant_id"] == participant
                    ]
                    for participant in groups
                ],
                tick_labels=groups,
            )
            axes[1, 0].set(
                xlabel="Participant", ylabel="Error (BPM)", title="Errors by participant"
            )
        else:
            for axis in axes.flat[:3]:
                axis.text(
                    0.5, 0.5, "No accepted aligned pairs", ha="center", transform=axis.transAxes
                )
                axis.set_xticks([])
                axis.set_yticks([])
        participants = summary[method]["participants"]
        names = list(participants)
        coverage = [
            participants[x]["coverage"] if participants[x]["coverage"] is not None else np.nan
            for x in names
        ]
        axes[1, 1].bar(names, coverage)
        axes[1, 1].set(
            xlabel="Participant",
            ylabel="Accepted / eligible",
            ylim=(0, 1),
            title="Coverage (not accuracy)",
        )
        for axis in axes.flat:
            axis.ticklabel_format(axis="y", style="plain", useOffset=False)
        figure.savefig(output / (method.lower() + ".png"), dpi=140)
        plt.close(figure)
