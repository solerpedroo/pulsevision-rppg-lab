/// <reference lib="webworker" />
import { FaceLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";
import { DisplayGuard } from "./display";
import { RingBuffer } from "./buffer";
import { analyze, Continuity } from "./dsp";
import { Extractor, ROIS } from "./roi";
import type { Analysis, Polygon, WorkerInput, WorkerOutput } from "./types";
import type { Method, Roi } from "../video/api";
const scope = self as unknown as DedicatedWorkerGlobalScope;
const send = (message: WorkerOutput) => scope.postMessage(message);
let detector: FaceLandmarker | null = null,
  method: Method = "GREEN",
  roi: Roi = "combined",
  lastAnalysis: Analysis | null = null,
  lastEnd = -Infinity,
  lastTimestamp = -Infinity,
  first: number | null = null,
  count = 0;
const buffers = Object.fromEntries(
    ROIS.map((name) => [name, new RingBuffer()]),
  ) as Record<Roi, RingBuffer>,
  extractor = new Extractor(),
  continuity = new Continuity();
const display = new DisplayGuard();
const canvas = new OffscreenCanvas(320, 240),
  context = canvas.getContext("2d", { willReadFrequently: true })!;
async function init(origin: string) {
  const root = new URL("/mediapipe/", origin).href;
  const model = await fetch(root + "face_landmarker.task", {
    cache: "no-store",
  });
  if (!model.ok) throw new Error("runtime_assets_missing");
  const buffer = await model.arrayBuffer();
  const digest = [
    ...new Uint8Array(await crypto.subtle.digest("SHA-256", buffer)),
  ]
    .map((v) => v.toString(16).padStart(2, "0"))
    .join("");
  if (
    digest !==
    "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
  )
    throw new Error("model_checksum_mismatch");
  detector = await FaceLandmarker.createFromOptions(
    await FilesetResolver.forVisionTasks(root + "wasm"),
    {
      baseOptions: {
        modelAssetBuffer: new Uint8Array(buffer),
        delegate: "CPU",
      },
      runningMode: "VIDEO",
      numFaces: 2,
      outputFaceBlendshapes: false,
      outputFacialTransformationMatrixes: false,
      minFaceDetectionConfidence: 0.5,
      minFacePresenceConfidence: 0.5,
      minTrackingConfidence: 0.5,
    },
  );
  send({ type: "ready" });
}
scope.onmessage = (event: MessageEvent<WorkerInput>) => {
  const message = event.data;
  if (message.type === "init") {
    method = message.method;
    roi = message.roi;
    void init(message.origin).catch((error) => {
      console.error(
        error instanceof Error ? error.message : "detector_init_failed",
      );
      send({
        type: "error",
        message:
          "Não foi possível carregar o detector local. Execute npm run live:assets e confira o suporte a WebGL/WASM em worker.",
      });
    });
    return;
  }
  const bitmap = message.bitmap;
  try {
    if (!detector) throw new Error("detector_not_ready");
    const timestamp = message.timestamp_s;
    if (
      !Number.isFinite(timestamp) ||
      timestamp < 0 ||
      timestamp <= lastTimestamp
    )
      throw new Error("invalid_timestamps");
    lastTimestamp = timestamp;
    const started = performance.now();
    if (first === null) first = timestamp;
    const relative = timestamp - first;
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    context.drawImage(bitmap, 0, 0);
    const result = detector.detectForVideo(canvas, timestamp * 1000),
      faces = result.faceLandmarks.map(
        (face) => face.map((p) => [p.x, p.y]) as Polygon,
      ),
      extracted = extractor.extract(
        context.getImageData(0, 0, canvas.width, canvas.height).data,
        canvas.width,
        canvas.height,
        faces,
        relative,
      );
    for (const name of ROIS) buffers[name].push(extracted.values[name]);
    const sample = extracted.values[roi];
    count++;
    const end = Math.floor(relative + 1e-9);
    if (end >= 20 && end > lastEnd) {
      lastEnd = end;
      lastAnalysis = continuity.apply(
        analyze(buffers[roi].window(end - 20, end), method, roi, end - 20, end),
      );
    }
    const displayReasons = display.apply(lastAnalysis, sample);
    const rows = buffers[roi].snapshot(),
      recent = rows.filter((s) => s.timestamp_s >= relative - 5),
      fps =
        recent.length > 1
          ? (recent.length - 1) / (relative - recent[0].timestamp_s)
          : 0;
    send({
      type: "frame",
      timestamp_s: relative,
      sample,
      polygons: extracted.polygons,
      analysis: lastAnalysis,
      display_reasons: displayReasons,
      count,
      analyzed_fps: fps,
      processing_ms: performance.now() - started,
    });
  } catch {
    send({
      type: "error",
      message:
        "Falha no processamento local ou nos timestamps. A câmera será desligada.",
    });
  } finally {
    bitmap.close();
  }
};
