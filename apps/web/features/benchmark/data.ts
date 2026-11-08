import Ajv from "ajv";
import schema from "../../../../packages/rppg_types/schemas/BenchmarkReview.json";
import type {
  BenchmarkReview,
  ReviewRun,
  ReviewWindow,
} from "../../../../packages/rppg_types/generated/BenchmarkReview";
export type { BenchmarkReview, ReviewRun, ReviewWindow };
const validate = new Ajv({
  allErrors: true,
  strict: false,
}).compile<BenchmarkReview>(schema);
export const MAX_BYTES = 20 * 1024 * 1024;
const key = (...parts: unknown[]) => JSON.stringify(parts);
export function parseReview(text: string): BenchmarkReview {
  let input: unknown;
  try {
    input = JSON.parse(text);
  } catch {
    throw new Error("JSON inválido.");
  }
  if (!validate(input))
    throw new Error(
      "Arquivo incompatível com benchmark-review-v1. Converta os relatórios offline pelo CLI de revisão.",
    );
  if (new Set(input.runs.map((r) => r.run_id)).size !== input.runs.length)
    throw new Error("IDs de execução duplicados.");
  if (new Set(input.runs.map((r) => r.result_kind)).size !== 1)
    throw new Error(
      "Não misture demonstração artificial com avaliação de dataset.",
    );
  if (input.runs.reduce((n, r) => n + r.windows.length, 0) > 100000)
    throw new Error("Limite de 100 mil janelas excedido.");
  for (const run of input.runs) {
    if (
      (run.dataset === "synthetic") !==
        (run.result_kind === "synthetic_demonstration") ||
      (run.dataset === "synthetic" && run.split === "test")
    )
      throw new Error("Dataset e natureza da avaliação são incompatíveis.");
    const sessions = new Set(
      run.sessions.map((s) => key(s.participant_id, s.session_id, s.condition)),
    );
    if (sessions.size !== run.sessions.length)
      throw new Error("Sessão declarada duplicada.");
    const windows = new Set<string>();
    for (const row of [...run.windows, ...run.failures])
      if (!sessions.has(key(row.participant_id, row.session_id, row.condition)))
        throw new Error("Sessão sem declaração de origem.");
    for (const w of run.windows) {
      const id = key(
        w.participant_id,
        w.session_id,
        w.method,
        w.start_s,
        w.end_s,
      );
      if (windows.has(id)) throw new Error("Janela duplicada.");
      windows.add(id);
      if (w.start_s >= w.end_s || (w.bpm === null && !w.reasons.length))
        throw new Error("Janela ou abstenção inconsistente.");
      if (
        w.eligible &&
        (w.reference_bpm === null ||
          w.exclusion_reason !== null ||
          w.reference_start_s === null ||
          w.reference_end_s === null ||
          !(
            w.start_s <= w.reference_start_s &&
            w.reference_start_s < w.reference_end_s &&
            w.reference_end_s <= w.end_s
          ))
      )
        throw new Error("Referência ou elegibilidade inconsistente.");
      if (!w.eligible && !w.exclusion_reason)
        throw new Error("Exclusão sem motivo.");
    }
  }
  return input;
}
export interface Filters {
  run: string;
  method: string;
  roi: string;
  condition: string;
  participant: string;
  window: string;
}
export const EMPTY_FILTERS: Filters = {
  run: "",
  method: "",
  roi: "",
  condition: "",
  participant: "",
  window: "",
};
export type Dimension =
  "method" | "participant" | "roi" | "condition" | "window";
export interface Group {
  label: string;
  run_id: string;
  method: string;
  participants: number;
  without_pairs: number;
  eligible: number;
  accepted: number;
  excluded: number;
  failures: number;
  coverage: number | null;
  macro_coverage: number | null;
  mae: number | null;
  rmse: number | null;
  medae: number | null;
  bias: number | null;
  reasons: Record<string, number>;
  exclusions: Record<string, number>;
}
const avg = (values: number[]) =>
  values.reduce((a, b) => a + b, 0) / values.length;
const median = (values: number[]) => {
  const ordered = [...values].sort((a, b) => a - b),
    mid = Math.floor(ordered.length / 2);
  return ordered.length % 2
    ? ordered[mid]
    : (ordered[mid - 1] + ordered[mid]) / 2;
};
export function groups(
  review: BenchmarkReview,
  filters: Filters,
  dimension: Dimension,
): Group[] {
  const output: Group[] = [];
  for (const run of review.runs) {
    if (
      (filters.run && run.run_id !== filters.run) ||
      (filters.roi && run.roi !== filters.roi) ||
      (filters.window && String(run.window_s) !== filters.window)
    )
      continue;
    const sessions = run.sessions.filter(
      (s) =>
        (!filters.condition || s.condition === filters.condition) &&
        (!filters.participant || s.participant_id === filters.participant),
    );
    const keys =
      dimension === "participant"
        ? [...new Set(sessions.map((s) => s.participant_id))]
        : dimension === "condition"
          ? [...new Set(sessions.map((s) => s.condition))]
          : [
              dimension === "roi"
                ? run.roi
                : dimension === "window"
                  ? `${run.window_s} s`
                  : "",
            ];
    for (const dim of keys)
      for (const method of ["GREEN", "CHROM", "POS"]) {
        if (filters.method && filters.method !== method) continue;
        const declared = sessions.filter(
          (s) =>
            (dimension !== "participant" || s.participant_id === dim) &&
            (dimension !== "condition" || s.condition === dim),
        );
        if (!declared.length) continue;
        const sessionKeys = new Set(
            declared.map((s) =>
              key(s.participant_id, s.session_id, s.condition),
            ),
          ),
          selected = run.windows.filter(
            (w) =>
              w.method === method &&
              sessionKeys.has(key(w.participant_id, w.session_id, w.condition)),
          ),
          eligible = selected.filter((w) => w.eligible),
          accepted = eligible.filter((w) => w.bpm !== null),
          ids = [...new Set(declared.map((s) => s.participant_id))];
        const subjectMetrics = ids.map((id) => {
          const source = eligible.filter((w) => w.participant_id === id),
            pairs = source.filter((w) => w.bpm !== null),
            errors = pairs.map((w) => w.bpm! - w.reference_bpm!);
          return {
            n: errors.length,
            coverage: source.length ? pairs.length / source.length : null,
            mae: errors.length ? avg(errors.map(Math.abs)) : null,
            rmse: errors.length
              ? Math.sqrt(avg(errors.map((e) => e * e)))
              : null,
            medae: errors.length ? median(errors.map(Math.abs)) : null,
            bias: errors.length ? avg(errors) : null,
          };
        });
        const evaluated = subjectMetrics.filter((s) => s.n),
          reasons: Record<string, number> = Object.create(null),
          exclusions: Record<string, number> = Object.create(null);
        for (const w of eligible.filter((w) => w.bpm === null))
          for (const reason of new Set(w.reasons))
            reasons[reason] = (reasons[reason] ?? 0) + 1;
        for (const w of selected.filter((w) => !w.eligible))
          exclusions[w.exclusion_reason!] =
            (exclusions[w.exclusion_reason!] ?? 0) + 1;
        const macro = (metric: "mae" | "rmse" | "medae" | "bias") =>
            evaluated.length ? avg(evaluated.map((s) => s[metric]!)) : null,
          covs = subjectMetrics.flatMap((s) =>
            s.coverage === null ? [] : [s.coverage],
          );
        output.push({
          label: [run.run_id, method, dim].filter(Boolean).join(" · "),
          run_id: run.run_id,
          method,
          participants: ids.length,
          without_pairs: ids.length - evaluated.length,
          eligible: eligible.length,
          accepted: accepted.length,
          excluded: selected.length - eligible.length,
          failures: run.failures.filter((s) =>
            sessionKeys.has(key(s.participant_id, s.session_id, s.condition)),
          ).length,
          coverage: eligible.length ? accepted.length / eligible.length : null,
          macro_coverage: covs.length ? avg(covs) : null,
          mae: macro("mae"),
          rmse: macro("rmse"),
          medae: macro("medae"),
          bias: macro("bias"),
          reasons,
          exclusions,
        });
      }
  }
  return output;
}
export function csvCell(value: string | number | null) {
  if (value === null) return '""';
  const text =
    typeof value === "string" && /^[=+\-@\t\r]/.test(value)
      ? "'" + value
      : String(value);
  return '"' + text.replaceAll('"', '""') + '"';
}
export function exportCsv(rows: Group[]) {
  const columns: [string, keyof Group][] = [
    ["grupo", "label"],
    ["MAE_macro_BPM", "mae"],
    ["RMSE_macro_BPM", "rmse"],
    ["MedAE_macro_BPM", "medae"],
    ["bias_macro_BPM", "bias"],
    ["cobertura_janelas", "coverage"],
    ["cobertura_macro_participantes", "macro_coverage"],
    ["aceitas", "accepted"],
    ["elegiveis", "eligible"],
    ["excluidas", "excluded"],
    ["falhas_sessao", "failures"],
    ["participantes_sem_pares", "without_pairs"],
  ];
  return (
    [
      columns.map((c) => c[0]).join(","),
      ...rows.map((row) =>
        columns
          .map(([, field]) => csvCell(row[field] as string | number | null))
          .join(","),
      ),
    ].join("\n") + "\n"
  );
}
