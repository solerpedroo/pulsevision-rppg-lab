import cfg from "./generated-config.json";
import type { Roi } from "../video/api";
import type { RGB, Polygon, Sample } from "./types";
const q = cfg.quality;
export const ROIS: Roi[] = [
  "forehead",
  "left_cheek",
  "right_cheek",
  "combined",
];
export function inside(x: number, y: number, polygon: Polygon) {
  let hit = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const a = polygon[i],
      b = polygon[j];
    if (
      a[1] > y !== b[1] > y &&
      x < ((b[0] - a[0]) * (y - a[1])) / (b[1] - a[1]) + a[0]
    )
      hit = !hit;
  }
  return hit;
}
function polygon(points: Polygon, indices: number[], shrink: number): Polygon {
  const vertices = indices.map((i) => points[i]);
  if (
    vertices.some(
      (p) => !p || p.some((v) => !Number.isFinite(v) || v < 0 || v > 1),
    )
  )
    throw new Error("invalid_geometry");
  const center = [0, 1].map(
    (k) => vertices.reduce((s, p) => s + p[k], 0) / vertices.length,
  );
  const p = vertices.map(
    (v) =>
      v.map((w, k) => center[k] + shrink * (w - center[k])) as [number, number],
  );
  let area = 0;
  p.forEach((v, i) => {
    const next = p[(i + 1) % p.length];
    area += v[0] * next[1] - v[1] * next[0];
  });
  if (Math.abs(area) < 1e-6) throw new Error("invalid_geometry");
  return p;
}
export class Extractor {
  private previous: Polygon | null = null;
  private previousTime: number | null = null;
  private brightness: Partial<Record<Roi, number>> = {};
  extract(
    pixels: Uint8ClampedArray,
    width: number,
    height: number,
    faces: Polygon[],
    timestamp: number,
  ): { values: Record<Roi, Sample>; polygons: Partial<Record<Roi, Polygon>> } {
    const values = {} as Record<Roi, Sample>,
      polygons: Partial<Record<Roi, Polygon>> = {};
    const empty = (reason: string) => {
      for (const roi of ROIS)
        values[roi] = {
          timestamp_s: timestamp,
          rgb: null,
          reasons: [reason],
          brightness: null,
          valid_fraction: 0,
          valid_pixels: 0,
          dark_fraction: 0,
          saturated_fraction: 0,
          motion: 0,
        };
      this.previous = null;
      this.previousTime = timestamp;
      this.brightness = {};
      return { values, polygons: {} };
    };
    if (faces.length !== 1)
      return empty(faces.length ? "multiple_faces" : "no_face");
    const points = faces[0];
    if (
      points.length !== 478 ||
      points.some((p) => p.length !== 2 || p.some((v) => !Number.isFinite(v)))
    )
      return empty("invalid_geometry");
    let exclusions: Polygon[];
    try {
      exclusions = cfg.exclusions.map((indices) => polygon(points, indices, 1));
      for (const [roi, indices] of Object.entries(cfg.regions))
        polygons[roi as Roi] = polygon(points, indices, 0.85);
    } catch {
      return empty("invalid_geometry");
    }
    const common: string[] = [];
    let motion = 0;
    const bounds = (p: Polygon) =>
      Math.hypot(
        ...[0, 1].map(
          (k) =>
            Math.max(...p.map((v) => v[k])) - Math.min(...p.map((v) => v[k])),
        ),
      );
    if (this.previous) {
      const scale = Math.max(bounds(this.previous), 1e-9);
      motion =
        Math.sqrt(
          points.reduce(
            (s, p, i) =>
              s +
              (p[0] - this.previous![i][0]) ** 2 +
              (p[1] - this.previous![i][1]) ** 2,
            0,
          ) / points.length,
        ) / scale;
      if (motion > q.max_motion || Math.abs(bounds(points) / scale - 1) > 0.2)
        common.push("excessive_motion");
    } else common.push("tracking_interrupted");
    if (this.previousTime !== null && timestamp - this.previousTime > 0.25)
      common.push("tracking_interrupted");
    this.previous = points.map((p) => [...p]);
    this.previousTime = timestamp;
    // Pixel centers, normalized to the analyzed image; no BGR conversion or mirrored input.
    for (const roi of ROIS.filter((r) => r !== "combined")) {
      const shape = polygons[roi]!;
      let area = 0,
        count = 0,
        dark = 0,
        saturated = 0,
        brightness = 0;
      const sums = [0, 0, 0];
      const minX = Math.max(
          0,
          Math.floor(Math.min(...shape.map((p) => p[0])) * width),
        ),
        maxX = Math.min(
          width,
          Math.ceil(Math.max(...shape.map((p) => p[0])) * width),
        ),
        minY = Math.max(
          0,
          Math.floor(Math.min(...shape.map((p) => p[1])) * height),
        ),
        maxY = Math.min(
          height,
          Math.ceil(Math.max(...shape.map((p) => p[1])) * height),
        );
      for (let y = minY; y < maxY; y++)
        for (let x = minX; x < maxX; x++) {
          const nx = (x + 0.5) / width,
            ny = (y + 0.5) / height;
          if (
            !inside(nx, ny, shape) ||
            exclusions.some((p) => inside(nx, ny, p))
          )
            continue;
          area++;
          const offset = (y * width + x) * 4,
            c = [pixels[offset], pixels[offset + 1], pixels[offset + 2]],
            b = (c[0] + c[1] + c[2]) / 3;
          brightness += b;
          const d = b < q.dark_brightness_threshold,
            s = Math.max(...c) >= q.saturated_channel_threshold;
          dark += +d;
          saturated += +s;
          if (!d && !s) {
            count++;
            c.forEach((v, k) => (sums[k] += v));
          }
        }
      const fraction = area ? count / area : 0,
        bright = area ? brightness / area : null,
        reasons = [...common];
      if (count < q.min_pixels) reasons.push("insufficient_pixels");
      if (fraction < q.min_pixel_fraction) reasons.push("low_valid_fraction");
      if (area && dark / area > q.max_dark_fraction) reasons.push("dark_roi");
      if (area && saturated / area > q.max_saturated_fraction)
        reasons.push("saturated_roi");
      const prior = this.brightness[roi];
      if (bright !== null) {
        if (
          prior !== undefined &&
          Math.abs(bright - prior) / Math.max(prior, 1) > q.max_brightness_step
        )
          reasons.push("illumination_change");
        this.brightness[roi] = bright;
      }
      values[roi] = {
        timestamp_s: timestamp,
        rgb: reasons.length ? null : (sums.map((v) => v / count) as RGB),
        reasons,
        brightness: bright,
        valid_fraction: fraction,
        valid_pixels: count,
        dark_fraction: area ? dark / area : 0,
        saturated_fraction: area ? saturated / area : 0,
        motion,
      };
    }
    const parts = ROIS.filter((r) => r !== "combined").map((r) => values[r]),
      weights = parts.reduce((s, p) => s + p.valid_pixels, 0),
      reasons = [...new Set(parts.flatMap((p) => p.reasons))];
    if (parts.some((p) => !p.rgb)) reasons.push("partial_roi");
    values.combined = {
      timestamp_s: timestamp,
      rgb: reasons.length
        ? null
        : ([0, 1, 2].map(
            (k) =>
              parts.reduce((s, p) => s + p.rgb![k] * p.valid_pixels, 0) /
              weights,
          ) as RGB),
      reasons,
      brightness: parts.every((p) => p.brightness !== null)
        ? parts.reduce((s, p) => s + p.brightness!, 0) / 3
        : null,
      valid_fraction: Math.min(...parts.map((p) => p.valid_fraction)),
      valid_pixels: weights,
      dark_fraction: Math.max(...parts.map((p) => p.dark_fraction)),
      saturated_fraction: Math.max(...parts.map((p) => p.saturated_fraction)),
      motion,
    };
    return { values, polygons };
  }
}
