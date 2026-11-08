import type { Method, Roi } from "../video/api";
export type RGB = [number, number, number];
export type Polygon = [number, number][];
export interface Sample {
  timestamp_s: number;
  rgb: RGB | null;
  reasons: string[];
  brightness: number | null;
  valid_fraction: number;
  valid_pixels: number;
  dark_fraction: number;
  saturated_fraction: number;
  motion: number;
}
export interface Analysis {
  bpm: number | null;
  reasons: string[];
  method: Method;
  roi: Roi;
  start_s: number;
  end_s: number;
  effective_fps: number;
  timestamps: number[];
  signal: number[];
  frequencies: number[];
  power: number[];
  metrics: Record<string, number>;
  version: "live-v1";
}
export type Phase =
  | "stopped"
  | "permission"
  | "detector"
  | "warmup"
  | "result"
  | "abstention"
  | "error";
export interface FrameReport {
  type: "frame";
  timestamp_s: number;
  sample: Sample;
  polygons: Partial<Record<Roi, Polygon>>;
  analysis: Analysis | null;
  display_reasons: string[];
  count: number;
  analyzed_fps: number;
  processing_ms: number;
}
export type WorkerOutput =
  { type: "ready" } | { type: "error"; message: string } | FrameReport;
export type WorkerInput =
  | { type: "init"; origin: string; method: Method; roi: Roi }
  | { type: "frame"; bitmap: ImageBitmap; timestamp_s: number };
