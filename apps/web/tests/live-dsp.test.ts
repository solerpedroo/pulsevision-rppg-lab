import { expect, it } from "vitest";
import fixture from "../../../tests/fixtures/live-dsp.json";
import { analyze, bandpass, Continuity } from "../features/live/dsp";
import { shouldCapture } from "../features/live/cadence";
import { DisplayGuard, freshnessDelayMs } from "../features/live/display";
import { RingBuffer } from "../features/live/buffer";
import type { Sample, RGB } from "../features/live/types";
import type { Method } from "../features/video/api";
const sample = (
  t: number,
  rgb: RGB | null = [160, 90, 60],
  reasons: string[] = [],
): Sample => ({
  timestamp_s: t,
  rgb,
  reasons,
  brightness: rgb ? rgb.reduce((a, b) => a + b, 0) / 3 : null,
  valid_fraction: 1,
  valid_pixels: 100,
  dark_fraction: 0,
  saturated_fraction: 0,
  motion: 0,
});
for (const c of fixture.cases)
  for (const method of ["GREEN", "POS", "CHROM"] as Method[]) {
    it(`regressão Python/TS ${method} ${c.frequency_hz} Hz (artificial)`, () => {
      const rows = c.timestamps.map((t, i) => sample(t, c.rgb[i] as RGB)),
        result = analyze(rows, method, "combined", 0, 20),
        expected = c.expected[method];
      expect(result.reasons).toEqual(expected.reasons);
      expect(result.bpm).toBeCloseTo(expected.bpm!, 9);
      for (const key of [
        "signal",
        "power",
        "frequencies",
        "timestamps",
      ] as const) {
        expect(result[key]).toHaveLength(expected[key].length);
        expect(
          Math.max(
            ...result[key].map((v, i) => Math.abs(v - expected[key][i])),
          ),
        ).toBeLessThan(1e-9);
      }
    });
  }
it("rejeita constante, janela curta, face ausente e gaps sem carry-forward", () => {
  const rows = fixture.cases[1].timestamps.map((t, i) =>
    sample(t, fixture.cases[1].rgb[i] as RGB),
  );
  expect(
    analyze(
      rows.map((s) => sample(s.timestamp_s)),
      "GREEN",
      "combined",
      0,
      20,
    ).reasons,
  ).toContain("constant_signal");
  expect(
    analyze(rows.slice(0, 200), "GREEN", "combined", 0, 20).bpm,
  ).toBeNull();
  expect(
    analyze(
      rows.map((s, i) =>
        i === 100 ? sample(s.timestamp_s, null, ["no_face"]) : s,
      ),
      "POS",
      "combined",
      0,
      20,
    ).reasons,
  ).toContain("no_face");
  expect(
    analyze(
      rows.filter((_, i) => i < 100 || i > 120),
      "GREEN",
      "combined",
      0,
      20,
    ).reasons,
  ).toContain("temporal_gap");
  const valid = analyze(rows, "GREEN", "combined", 0, 20),
    history = new Continuity();
  expect(history.apply(valid).bpm).not.toBeNull();
  history.apply({ ...valid, bpm: null, end_s: 21, reasons: ["no_face"] });
  expect(history.apply({ ...valid, end_s: 22 }).bpm).toBeNull();
  expect(history.apply({ ...valid, end_s: 23 }).bpm).not.toBeNull();
});
it("buffer limitado mantém null e rejeita tempo duplicado", () => {
  const buffer = new RingBuffer(3);
  for (let i = 0; i < 5; i++)
    buffer.push(sample(i, i === 3 ? null : [160, 90, 60]));
  expect(buffer.snapshot().map((s) => s.timestamp_s)).toEqual([2, 3, 4]);
  expect(buffer.snapshot()[1].rgb).toBeNull();
  expect(() => buffer.push(sample(4))).toThrow("invalid_timestamps");
  buffer.clear();
  expect(buffer.snapshot()).toEqual([]);
  expect(() => bandpass([1, 2])).toThrow("filter_window_too_short");
});

it("rejeição atual bloqueia display sem alterar a janela histórica", () => {
  const rows = fixture.cases[1].timestamps.map((t, i) =>
    sample(t, fixture.cases[1].rgb[i] as RGB),
  );
  const analysis = analyze(rows, "GREEN", "combined", 0, 20),
    guard = new DisplayGuard();
  expect(analysis.bpm).not.toBeNull();
  expect(freshnessDelayMs(analysis, 22)).toBe(1000);
  expect(freshnessDelayMs(analysis, 24)).toBe(0);
  expect(guard.apply(analysis, sample(20))).toEqual([]);
  expect(guard.apply(analysis, sample(20.1, null, ["no_face"]))).toEqual([
    "no_face",
  ]);
  expect(guard.apply(analysis, sample(20.2))).toEqual(["no_face"]);
  expect(analysis.bpm).not.toBeNull();
  expect(analysis.reasons).toEqual([]);
  expect(guard.apply({ ...analysis, end_s: 21 }, sample(21))).toEqual([]);
});

it("cadência aceita quantização sem duplicar timestamps ou enfileirar frames", () => {
  expect(shouldCapture(0.033332, 0, false)).toBe(true);
  expect(shouldCapture(0.066667, 0.033332, false)).toBe(true);
  expect(shouldCapture(0.01, 0, false)).toBe(false);
  expect(shouldCapture(0.034, 0.0335, false)).toBe(false);
  expect(shouldCapture(1, 0, true)).toBe(false);
  expect(shouldCapture(NaN, 0, false)).toBe(false);
});
