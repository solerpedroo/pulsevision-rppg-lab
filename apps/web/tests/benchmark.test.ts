// Original artificial contract cases. These are not benchmark findings or human measurements.
import { expect, it } from "vitest";
import {
  EMPTY_FILTERS,
  parseReview,
  groups,
  exportCsv,
  type BenchmarkReview,
} from "../features/benchmark/data";
function fixture() {
  const row = (id: string, bpm: number | null, start = 0, eligible = true) => ({
    participant_id: id,
    session_id: "fixture",
    condition: "artificial",
    method: "GREEN",
    start_s: start,
    end_s: start + 20,
    reference_start_s: eligible ? start + 2 : null,
    reference_end_s: eligible ? start + 18 : null,
    eligible,
    exclusion_reason: eligible ? null : "reference_gap",
    bpm,
    reference_bpm: eligible ? 70 : null,
    reasons: bpm === null ? ["no_face"] : [],
  });
  return {
    schema_version: "benchmark-review-v1",
    title: "CONTRACT TEST ONLY",
    hypothesis: "All values are artificial arithmetic cases.",
    pending: ["Not physiological validation"],
    limitations: ["Artificial contract fixture"],
    runs: [
      {
        run_id: "fixture",
        experiment: "import",
        dataset: "synthetic",
        result_kind: "synthetic_demonstration",
        dataset_version: "contract-fixture",
        protocol_version: "test-only",
        split: "development",
        roi: "combined",
        window_s: 20,
        seed: 42,
        bootstrap_samples: 100,
        source_report: "contract-only.json",
        report_sha256: "a".repeat(64),
        manifest_sha256: "b".repeat(64),
        provenance: { kind: "unit-test-placeholder-hashes" },
        configuration: {},
        limitations: ["All values are artificial contract cases."],
        sessions: ["a", "b", "c", "d"].map((participant_id) => ({
          participant_id,
          session_id: "fixture",
          condition: "artificial",
        })),
        failures: [
          {
            participant_id: "d",
            session_id: "fixture",
            condition: "artificial",
            reason: "unverified_alignment",
          },
        ],
        windows: [
          row("a", 71),
          row("a", 73, 1),
          row("b", 80),
          row("c", null),
          row("a", null, 2, false),
        ],
      },
    ],
  };
}
it("erros macro dão peso igual aos participantes e mantêm abstenções/exclusões", () => {
  const review = parseReview(JSON.stringify(fixture())),
    result = groups(review, EMPTY_FILTERS, "method")[0];
  expect(result.mae).toBe(6);
  expect(result.bias).toBe(6);
  expect(result.rmse).toBeCloseTo((Math.sqrt(5) + 10) / 2);
  expect(result.coverage).toBe(0.75);
  expect(result.eligible).toBe(4);
  expect(result.accepted).toBe(3);
  expect(result.excluded).toBe(1);
  expect(result.failures).toBe(1);
  expect(result.without_pairs).toBe(2);
});
it("recorte por participante conserva grupo sem pares e zero cobertura", () => {
  const review = parseReview(JSON.stringify(fixture())),
    selected = groups(
      review,
      { ...EMPTY_FILTERS, participant: "c" },
      "participant",
    );
  expect(selected[0].mae).toBeNull();
  expect(selected[0].coverage).toBe(0);
  expect(selected[0].reasons.no_face).toBe(1);
  const failed = groups(
    review,
    { ...EMPTY_FILTERS, participant: "d" },
    "method",
  )[0];
  expect(failed.eligible).toBe(0);
  expect(failed.coverage).toBeNull();
  expect(failed.failures).toBe(1);
  expect(
    groups(review, { ...EMPTY_FILTERS, condition: "absent" }, "condition"),
  ).toEqual([]);
});
it("recusa arquivos malformados, métricas sem referência e falsos testes sintéticos", () => {
  expect(() => parseReview("not json")).toThrow("JSON inválido");
  expect(() => parseReview("{}")).toThrow("incompatível");
  const data = fixture();
  data.runs[0].split = "test";
  expect(() => parseReview(JSON.stringify(data))).toThrow("natureza");
  data.runs[0].split = "development";
  data.runs[0].windows[0].reference_bpm = null;
  expect(() => parseReview(JSON.stringify(data))).toThrow("Referência");
});
it("recusa duplicações e mistura artificial/real", () => {
  const data = fixture();
  data.runs.push({ ...data.runs[0] });
  expect(() => parseReview(JSON.stringify(data))).toThrow("duplicados");
  data.runs[1].run_id = "other";
  data.runs[1].dataset = "UBFC-rPPG";
  data.runs[1].result_kind = "dataset_evaluation";
  expect(() => parseReview(JSON.stringify(data))).toThrow("misture");
});
it("CSV preserva ausência e impede fórmula em rótulos importados", () => {
  const rows = groups(
    parseReview(JSON.stringify(fixture())) as BenchmarkReview,
    EMPTY_FILTERS,
    "method",
  );
  rows[0].label = "=untrusted";
  const csv = exportCsv(rows);
  expect(csv).toContain('"\'=untrusted"');
  expect(csv).toContain("MAE_macro_BPM");
  expect(exportCsv([{ ...rows[0], mae: null }])).toContain('""');
});
