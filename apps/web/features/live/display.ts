import cfg from "./generated-config.json";
import type { Analysis, Sample } from "./types";
// Display rejection must not rewrite the provenance of a previously completed window.
export class DisplayGuard {
  private end: number | null = null;
  private reasons: string[] = [];
  apply(analysis: Analysis | null, sample: Sample) {
    if (analysis && analysis.end_s !== this.end) {
      this.end = analysis.end_s;
      this.reasons = [];
    }
    if (sample.reasons.length) this.reasons = [...sample.reasons];
    return [...this.reasons];
  }
}

export function freshnessDelayMs(analysis: Analysis, sourceTime: number) {
  return Math.max(
    0,
    (cfg.quality.max_estimate_age_s - (sourceTime - analysis.end_s)) * 1000,
  );
}
