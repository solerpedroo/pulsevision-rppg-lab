"""Convert existing offline reports to a local browser contract and reproducible figures."""

import argparse
import json
from pathlib import Path
from typing import Any

from rppg_types.benchmark import BenchmarkReview, ReviewRun

from benchmarks.analysis.aggregate import summarize
from benchmarks.manifest import digest


def read_run(path: Path, run_id: str, experiment: str = "import") -> ReviewRun:
    raw = json.loads(path.read_text())
    if raw.get("schema_version") != "benchmark-v1":
        raise ValueError("Expected benchmark-v1 report")
    config = raw["manifest_configuration"]
    rows = []
    for row in raw["windows"]:
        left, right = row["reference_start_s"], row["reference_end_s"]
        if not (0 <= left < right <= row["end_s"] and left >= row["start_s"]):
            left = right = None
        rows.append(
            {
                key: row[key]
                for key in (
                    "participant_id",
                    "session_id",
                    "condition",
                    "method",
                    "start_s",
                    "end_s",
                    "eligible",
                    "exclusion_reason",
                    "bpm",
                    "reference_bpm",
                    "reasons",
                )
            }
            | {"reference_start_s": left, "reference_end_s": right}
        )
    seed = raw["summary"]["GREEN"]["seed"]
    bootstrap = raw["summary"]["GREEN"]["bootstrap_samples"]
    return ReviewRun.model_validate(
        {
            "run_id": run_id,
            "experiment": experiment,
            "dataset": raw["dataset"],
            "result_kind": raw["result_kind"],
            "dataset_version": raw["dataset_version"],
            "protocol_version": raw["protocol_version"],
            "split": raw["split"],
            "roi": config["roi"],
            "window_s": config["signal"]["window_s"],
            "seed": seed,
            "bootstrap_samples": bootstrap,
            "source_report": path.name,
            "report_sha256": digest(path),
            "manifest_sha256": raw["frozen"]["manifest_sha256"],
            "provenance": {
                "frozen": raw["frozen"],
                "hardware": raw["hardware"],
                "timings": raw["timings"],
                "alignment": raw["session_alignment"],
            },
            "configuration": config,
            "sessions": [
                {key: s[key] for key in ("participant_id", "session_id", "condition")}
                for s in raw["session_alignment"]
            ],
            "failures": raw["session_failures"],
            "windows": rows,
            "limitations": raw["limitations"],
        }
    )


def summaries(review: BenchmarkReview) -> dict[str, Any]:
    return {
        run.run_id: summarize(
            [w.model_dump() for w in run.windows],
            seed=run.seed,
            bootstrap_samples=run.bootstrap_samples,
            participant_ids=sorted({s.participant_id for s in run.sessions}),
        )
        for run in review.runs
    }


def export_review(review: BenchmarkReview, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    aggregate = summaries(review)
    (output / "benchmark-review-v1.json").write_text(review.model_dump_json(indent=2) + "\n")
    (output / "summary.json").write_text(json.dumps(aggregate, indent=2, allow_nan=False) + "\n")
    artificial = review.runs[0].result_kind == "synthetic_demonstration"
    lines = [
        "# " + review.title,
        "",
        "**DEMONSTRAÇÃO ARTIFICIAL — sem validação fisiológica.**"
        if artificial
        else "**Avaliação experimental — não é validação clínica.**",
        "",
        "## Hipótese",
        "",
        review.hypothesis,
        "",
        "## Método e rastreabilidade",
        "",
        "Erros em pares aceitos; média com peso igual por participante. Cobertura considera",
        "todas as janelas elegíveis. Sessões sem comparação permanecem separadas.",
        "",
    ]
    for run in review.runs:
        lines += [
            f"### {run.run_id}",
            "",
            f"Dataset: {run.dataset}/{run.dataset_version}; "
            f"split: {run.split}; ROI: {run.roi}; janela: {run.window_s:g} s.",
            f"Relatório SHA256: {run.report_sha256}",
            f"Manifesto SHA256: {run.manifest_sha256}",
            f"Seed: {run.seed}; bootstrap por participante: {run.bootstrap_samples}.",
            f"Falhas de sessão: {len(run.failures)}.",
            "",
        ]
        for method, group in aggregate[run.run_id].items():
            lines += [
                f"- {method}: erros macro (BPM): {json.dumps(group['macro_errors'])}; "
                f"cobertura: {group['window_coverage']}; aceitas/elegíveis: "
                f"{group['accepted_windows']}/{group['eligible_windows']}; "
                f"exclusões: {group['excluded_windows']}."
            ]
        lines += ["", "Configuração completa, ambiente, alinhamento e hashes estão no JSON.", ""]
    lines += [
        "## Resultados e interpretação",
        "",
        "As métricas descrevem apenas os pares aceitos nas condições declaradas.",
        "Não selecionar vencedor ignorando cobertura, exclusões, participantes sem pares",
        "ou intervalos de referência diferentes. Janelas sobrepostas não são independentes.",
        "",
        "## Pendências",
        "",
        *["- " + text for text in review.pending],
        "",
        "## Limitações",
        "",
        *["- " + text for text in review.limitations],
        "",
        "## Trabalhos futuros",
        "",
        "Concluir protocolos congelados em datasets autorizados antes de conclusões reais.",
    ]
    (output / "report.md").write_text("\n".join(lines) + "\n")
    save_comparison(review, aggregate, output / "comparison.png")


def save_comparison(review: BenchmarkReview, aggregate: dict[str, Any], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    labels, errors, coverage = [], [], []
    for run in review.runs:
        for method, group in aggregate[run.run_id].items():
            labels.append(f"{run.run_id} / {method}")
            errors.append(group["macro_errors"]["mae"])
            coverage.append(group["window_coverage"])
    fig, axes = plt.subplots(1, 2, figsize=(12, max(4, len(labels) * 0.32)), layout="constrained")
    for ax, values, title, unit in zip(
        axes,
        [errors, coverage],
        ["MAE macro (pares aceitos)", "Cobertura (aceitas/elegíveis)"],
        ["BPM", "Fração"],
        strict=True,
    ):
        positions = np.arange(len(labels))
        for i, value in enumerate(values):
            if value is None:
                ax.text(0, i, "indisponível", va="center")
            else:
                ax.barh(i, value, color="#268b81")
                ax.plot(value, i, "o", color="#173e43", markersize=3)
        ax.set_yticks(positions, labels)
        ax.invert_yaxis()
        ax.set_title(title)
        ax.set_xlabel(unit)
        ax.grid(axis="x", alpha=0.2)
    fig.suptitle(
        "ARTIFICIAL — sem precisão fisiológica"
        if review.runs[0].dataset == "synthetic"
        else "Avaliação experimental — erros condicionais à aceitação"
    )
    fig.savefig(path, dpi=140)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    review = BenchmarkReview(
        title="Revisão de benchmark",
        hypothesis="Inspecionar resultados offline sem alterar o protocolo.",
        runs=[read_run(path, f"run-{index + 1}") for index, path in enumerate(args.reports)],
        pending=[
            "Avaliação real e relatório científico final pendentes "
            "quando não há dataset autorizado."
        ],
        limitations=[
            "Hashes declarados não equivalem a verificação independente dos dados.",
            "Demonstrações artificiais não medem precisão em pessoas.",
        ],
    )
    export_review(review, args.output)


if __name__ == "__main__":
    main()
