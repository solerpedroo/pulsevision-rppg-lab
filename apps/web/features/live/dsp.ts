import cfg from "./generated-config.json";
import type { Method, Roi } from "../video/api";
import type { Analysis, RGB, Sample } from "./types";
export const FS = cfg.fs;
const q = cfg.quality;
export const mean = (x: number[]) => x.reduce((a, b) => a + b, 0) / x.length;
export const std = (x: number[]) => {
  const m = mean(x);
  return Math.sqrt(mean(x.map((v) => (v - m) ** 2)));
};
const fail = (reason: string): never => {
  throw new Error(reason);
};
export function detrend(x: number[]) {
  const center = (x.length - 1) / 2,
    m = mean(x);
  let a = 0,
    b = 0;
  for (let i = 0; i < x.length; i++) {
    a += (i - center) * (x[i] - m);
    b += (i - center) ** 2;
  }
  return x.map((v, i) => v - m - (a / Math.max(b, 1)) * (i - center));
}
export function green(rgb: RGB[]) {
  const g = rgb.map((c) => c[1]),
    m = mean(g);
  if (m <= 0) fail("constant_signal");
  const y = detrend(g.map((v) => v / m - 1));
  if (std(y) < 1e-6) fail("constant_signal");
  return y;
}
function sosFilter(x: number[], initial: number) {
  let y = [...x];
  for (let j = 0; j < cfg.sos.length; j++) {
    const [b0, b1, b2, , a1, a2] = cfg.sos[j];
    let z0 = cfg.zi[j][0] * initial,
      z1 = cfg.zi[j][1] * initial;
    y = y.map((v) => {
      const out = b0 * v + z0;
      z0 = b1 * v - a1 * out + z1;
      z1 = b2 * v - a2 * out;
      return out;
    });
  }
  return y;
}
export function bandpass(x: number[]) {
  const edge = 27;
  if (x.length <= edge) fail("filter_window_too_short");
  const left = x
      .slice(1, edge + 1)
      .reverse()
      .map((v) => 2 * x[0] - v),
    right = x
      .slice(-edge - 1, -1)
      .reverse()
      .map((v) => 2 * x.at(-1)! - v);
  const extended = [...left, ...x, ...right];
  const forward = sosFilter(extended, extended[0]).reverse();
  return sosFilter(forward, forward[0]).reverse().slice(edge, -edge);
}
export function extract(rgb: RGB[], method: Method) {
  if (
    !rgb.length ||
    rgb.some((c) => c.some((v) => !Number.isFinite(v) || v <= 0))
  )
    fail("invalid_method_rgb");
  if (method === "GREEN") return { values: bandpass(green(rgb)), trim: 30 };
  const length = 48,
    out = Array(rgb.length).fill(0) as number[];
  if (rgb.length < length * 2) fail("projection_window_too_short");
  for (
    let start = 0;
    start + length <= rgb.length;
    start += method === "POS" ? 1 : length / 2
  ) {
    const segment = rgb.slice(start, start + length),
      m = [0, 1, 2].map((k) => mean(segment.map((c) => c[k])));
    let pulse: number[];
    if (method === "POS") {
      const c = segment.map((v) => v.map((w, k) => w / (m[k] + 1e-9))),
        s1 = c.map((v) => v[1] - v[2]),
        s2 = c.map((v) => -2 * v[0] + v[1] + v[2]),
        den = std(s2);
      if (den <= 1e-9) fail("degenerate_pos_projection");
      const ratio = std(s1) / (den + 1e-9),
        h = s1.map((v, i) => v + ratio * s2[i]),
        avg = mean(h);
      pulse = h.map((v) => v - avg);
    } else {
      const c = segment.map((v) => v.map((w, k) => w / m[k])),
        x = bandpass(c.map((v) => 3 * v[0] - 2 * v[1])),
        y = bandpass(c.map((v) => 1.5 * v[0] + v[1] - 1.5 * v[2]));
      if (std(y) <= 1e-9) fail("degenerate_chrom_projection");
      const ratio = std(x) / std(y);
      pulse = x.map(
        (v, i) =>
          (v - ratio * y[i]) *
          (0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (length - 1))),
      );
    }
    pulse.forEach((v, i) => (out[start + i] += v));
  }
  if (std(out.slice(length, -length)) < 1e-6) fail("constant_signal");
  return { values: method === "POS" ? bandpass(out) : out, trim: length };
}
export function spectrum(values: number[]) {
  const n = Math.min(values.length, 600);
  if (n < 8) fail("insufficient_spectral_resolution");
  const window = Array.from(
      { length: n },
      (_, i) => 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / n),
    ),
    scale = FS * window.reduce((s, v) => s + v * v, 0),
    power = Array(Math.floor(n / 2) + 1).fill(0) as number[];
  let count = 0;
  for (
    let start = 0;
    start + n <= values.length;
    start += n - Math.floor(n / 2)
  ) {
    count++;
    for (let k = 0; k < power.length; k++) {
      let re = 0,
        im = 0;
      for (let j = 0; j < n; j++) {
        const value = values[start + j] * window[j],
          angle = (2 * Math.PI * k * j) / n;
        re += value * Math.cos(angle);
        im -= value * Math.sin(angle);
      }
      power[k] +=
        ((re * re + im * im) / scale) *
        (k === 0 || (n % 2 === 0 && k === n / 2) ? 1 : 2);
    }
  }
  return {
    frequencies: power.map((_, k) => (k * FS) / n),
    power: power.map((v) => v / count),
  };
}
export function peak(f: number[], p: number[]) {
  const band = f
    .map((v, i) => (v >= 0.7 && v <= 3 ? i : -1))
    .filter((i) => i >= 0);
  if (
    band.length < 3 ||
    p.some((v) => !Number.isFinite(v)) ||
    band.reduce((s, i) => s + p[i], 0) <= 0
  )
    fail("insufficient_spectral_energy");
  const k = band.reduce((a, b) => (p[b] > p[a] ? b : a)),
    spacing = f[1] - f[0];
  if (k === band[0] || k === band.at(-1)) fail("peak_at_band_edge");
  const sum = band.reduce((s, i) => s + p[i], 0),
    concentration =
      band
        .filter((i) => Math.abs(f[i] - f[k]) <= spacing * 1.01)
        .reduce((s, i) => s + p[i], 0) / sum,
    competitor = Math.max(
      0,
      ...band
        .filter((i) => Math.abs(f[i] - f[k]) > spacing * 2.01)
        .map((i) => p[i] / p[k]),
    );
  if (concentration < 0.45) fail("diffuse_spectrum");
  if (competitor > 0.5) fail("ambiguous_peaks");
  return { bpm: f[k] * 60, concentration, spacing };
}
export function uniform(rows: Sample[]) {
  let j = 0;
  const start = rows[0].timestamp_s,
    n = Math.floor((rows.at(-1)!.timestamp_s - start) * FS + 1e-8) + 1;
  return Array.from({ length: n }, (_, i) => {
    const t = start + i / FS;
    while (j + 1 < rows.length && rows[j + 1].timestamp_s < t) j++;
    const a = rows[j],
      b = rows[Math.min(j + 1, rows.length - 1)],
      fraction =
        b.timestamp_s === a.timestamp_s
          ? 0
          : (t - a.timestamp_s) / (b.timestamp_s - a.timestamp_s);
    return {
      t,
      rgb: a.rgb!.map((v, k) => v + fraction * (b.rgb![k] - v)) as RGB,
    };
  });
}
export function analyze(
  rows: Sample[],
  method: Method,
  roi: Roi,
  start: number,
  end: number,
): Analysis {
  const result: Analysis = {
    bpm: null,
    reasons: [],
    method,
    roi,
    start_s: start,
    end_s: end,
    effective_fps: 0,
    timestamps: [],
    signal: [],
    frequencies: [],
    power: [],
    metrics: {},
    version: "live-v1",
  };
  try {
    if (rows.length < 3) fail("insufficient_data");
    const times = rows.map((s) => s.timestamp_s);
    if (
      times.some(
        (v, i) =>
          !Number.isFinite(v) ||
          v < start - 1e-9 ||
          v >= end ||
          (i > 0 && v <= times[i - 1]),
      )
    )
      fail("invalid_timestamps");
    const intervals = times.slice(1).map((v, i) => v - times[i]),
      sorted = [...intervals].sort((a, b) => a - b),
      mid = Math.floor(sorted.length / 2),
      median =
        sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    result.effective_fps = (rows.length - 1) / (times.at(-1)! - times[0]);
    const bad = [...new Set(rows.flatMap((s) => s.reasons))];
    if (bad.length) {
      result.reasons = bad;
      return result;
    }
    if (
      rows.some(
        (s) =>
          !s.rgb || s.rgb.some((v) => !Number.isFinite(v) || v < 0 || v > 255),
      )
    )
      fail("invalid_roi_samples");
    if (1 / median < 12) fail("insufficient_nyquist");
    if (Math.max(...intervals) > Math.min(0.15, 2.5 * median))
      fail("temporal_gap");
    if (
      end - start < 20 - 1e-8 ||
      times[0] - start > 1.5 * median ||
      end - times.at(-1)! > 1.5 * median
    )
      fail("window_too_short");
    const cv = std(intervals) / mean(intervals),
      coverage = Math.min(1, (rows.length * median) / (end - start));
    result.metrics.interval_cv = cv;
    result.metrics.temporal_coverage = coverage;
    if (cv > q.max_interval_cv) fail("irregular_sampling");
    if (coverage < q.min_temporal_coverage) fail("low_temporal_coverage");
    const brightness = rows.map((s) => s.brightness ?? mean(s.rgb!));
    if (
      std(brightness) / Math.max(mean(brightness), 1e-9) >
      q.max_illumination_cv
    )
      fail("illumination_instability");
    if (
      brightness
        .slice(1)
        .some(
          (v, i) =>
            Math.abs(v - brightness[i]) / Math.max(brightness[i], 1) >
            q.max_brightness_step,
        )
    )
      fail("illumination_change");
    const grid = uniform(rows),
      rgb = grid.map((s) => s.rgb),
      raw = spectrum(green(rgb)),
      total = raw.power.slice(1).reduce((s, v) => s + v, 0),
      band = raw.power.reduce(
        (s, v, i) =>
          s + (raw.frequencies[i] >= 0.7 && raw.frequencies[i] <= 3 ? v : 0),
        0,
      );
    result.metrics.band_energy_fraction = total > 0 ? band / total : 0;
    const extracted = extract(rgb, method);
    result.timestamps = grid
      .slice(extracted.trim, -extracted.trim)
      .map((s) => s.t);
    result.signal = extracted.values.slice(extracted.trim, -extracted.trim);
    const psd = spectrum(result.signal);
    result.frequencies = psd.frequencies;
    result.power = psd.power;
    const candidate = peak(result.frequencies, result.power);
    if (result.metrics.band_energy_fraction < q.min_band_energy_fraction)
      fail("low_band_energy");
    result.metrics.frequency_bin_hz = candidate.spacing;
    result.metrics.peak_fraction = candidate.concentration;
    result.bpm = candidate.bpm;
  } catch (error) {
    result.reasons = [
      error instanceof Error ? error.message : "processing_failed",
    ];
  }
  return result;
}
export class Continuity {
  private baseline: number | null = null;
  private pending: number | null = null;
  private count = 0;
  private recovering = false;
  private last: number | null = null;
  apply(input: Analysis) {
    const r = { ...input, reasons: [...input.reasons] };
    if (this.last !== null && r.end_s - this.last > q.max_history_gap_s) {
      this.baseline = this.pending = null;
      this.count = 0;
      this.recovering = true;
    }
    this.last = r.end_s;
    if (r.bpm === null) {
      this.baseline = this.pending = null;
      this.count = 0;
      this.recovering = true;
      return r;
    }
    const changed =
      this.baseline !== null &&
      Math.abs(r.bpm - this.baseline) > q.max_bpm_jump;
    if (changed || this.recovering) {
      this.count =
        this.pending !== null &&
        Math.abs(r.bpm - this.pending) <= q.confirmation_tolerance_bpm
          ? this.count + 1
          : 1;
      this.pending = r.bpm;
      if (this.count < q.confirmation_windows) {
        r.bpm = null;
        r.reasons = [
          changed ? "unstable_between_windows" : "recovering_signal",
        ];
        return r;
      }
    }
    this.baseline = r.bpm;
    this.pending = null;
    this.count = 0;
    this.recovering = false;
    return r;
  }
}
