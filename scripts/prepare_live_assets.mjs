// Explicit local staging only. No network or model redistribution.
import { createHash } from "node:crypto";
import { readFile, mkdir, copyFile, readdir } from "node:fs/promises";
import path from "node:path";
const root = path.resolve(import.meta.dirname, ".."),
  target = path.join(root, "apps/web/public/mediapipe");
const model = path.join(root, "models/face_landmarker.task");
const hash = createHash("sha256")
  .update(await readFile(model))
  .digest("hex");
if (hash !== "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff")
  throw new Error("Local model checksum mismatch");
await mkdir(path.join(target, "wasm"), { recursive: true });
const wasm = path.join(root, "node_modules/@mediapipe/tasks-vision/wasm");
for (const name of await readdir(wasm))
  await copyFile(path.join(wasm, name), path.join(target, "wasm", name));
await copyFile(model, path.join(target, "face_landmarker.task"));
console.log(
  "Verified local model and staged matching MediaPipe WASM assets. No network requests.",
);
