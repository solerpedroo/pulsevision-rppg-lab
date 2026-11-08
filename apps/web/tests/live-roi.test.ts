import { expect, it } from "vitest";
import cfg from "../features/live/generated-config.json";
import { Extractor } from "../features/live/roi";
import type { Polygon } from "../features/live/types";
function landmarks(): Polygon {
  const points: Polygon = Array.from({ length: 478 }, () => [0.5, 0.5]);
  Object.values(cfg.regions).forEach((indices, i) => {
    const center = [
      [0.5, 0.2],
      [0.7, 0.55],
      [0.3, 0.55],
    ][i];
    indices.forEach(
      (index, j) =>
        (points[index] = [
          center[0] + 0.09 * Math.cos((2 * Math.PI * j) / indices.length),
          center[1] + 0.05 * Math.sin((2 * Math.PI * j) / indices.length),
        ]),
    );
  });
  cfg.exclusions.forEach((indices, i) => {
    const center = [
      [0.35, 0.38],
      [0.65, 0.38],
      [0.5, 0.75],
      [0.35, 0.31],
      [0.65, 0.31],
    ][i];
    indices.forEach(
      (index, j) =>
        (points[index] = [
          center[0] + 0.025 * Math.cos((2 * Math.PI * j) / indices.length),
          center[1] + 0.015 * Math.sin((2 * Math.PI * j) / indices.length),
        ]),
    );
  });
  return points;
}
const pixels = (rgb: number[]) => {
  const p = new Uint8ClampedArray(320 * 256 * 4);
  for (let i = 0; i < p.length; i += 4) p.set([...rgb, 255], i);
  return p;
};
it("extrai RGB sem inverter canais, conserva anatomia e rejeita perda de face", () => {
  const extract = new Extractor(),
    points = landmarks(),
    image = pixels([160, 90, 60]);
  expect(
    extract.extract(image, 320, 256, [points], 0).values.combined.rgb,
  ).toBeNull();
  const result = extract.extract(image, 320, 256, [points], 0.04);
  expect(result.values.combined.rgb).toEqual([160, 90, 60]);
  expect(result.values.forehead.valid_pixels).toBeGreaterThan(30);
  expect(result.polygons.left_cheek!.every((p) => p[0] > 0.5)).toBe(true);
  expect(result.polygons.right_cheek!.every((p) => p[0] < 0.5)).toBe(true);
  expect(extract.extract(image, 320, 256, [], 0.08).polygons).toEqual({});
  expect(
    extract.extract(image, 320, 256, [points, points], 0.12).values.forehead
      .reasons,
  ).toContain("multiple_faces");
});
it("escuro, saturação, movimento e geometria inválida não produzem RGB", () => {
  const points = landmarks(),
    extract = new Extractor(),
    image = pixels([160, 90, 60]);
  extract.extract(image, 320, 256, [points], 0);
  expect(
    extract.extract(pixels([0, 0, 0]), 320, 256, [points], 0.04).values.combined
      .rgb,
  ).toBeNull();
  expect(
    extract.extract(pixels([255, 255, 255]), 320, 256, [points], 0.08).values
      .forehead.reasons,
  ).toContain("saturated_roi");
  const moved = points.map((p) => [p[0] + 0.15, p[1]]) as Polygon;
  expect(
    extract.extract(image, 320, 256, [moved], 0.12).values.forehead.reasons,
  ).toContain("excessive_motion");
  points[10] = [NaN, 0.5];
  expect(extract.extract(image, 320, 256, [points], 0.16).polygons).toEqual({});
});
