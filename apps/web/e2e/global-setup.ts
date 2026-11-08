import { execFileSync } from "node:child_process";
import path from "node:path";
import { mkdtempSync } from "node:fs";
export default function setup() {
  const root = path.resolve(__dirname, "../../..");
  execFileSync("uv", ["run", "python", "scripts/generate_camera_fixture.py"], {
    cwd: root,
  });
  execFileSync("node", ["scripts/prepare_live_assets.mjs"], { cwd: root });
  const directory = path.join(
    mkdtempSync(path.join(root, "artifacts/wave10-e2e-")),
    "study",
  );
  execFileSync(
    "uv",
    ["run", "python", "-m", "benchmarks.study", "demo", "--output", directory],
    { cwd: root },
  );
  process.env.PULSEVISION_BENCHMARK_FIXTURE = path.join(
    directory,
    "results/review/benchmark-review-v1.json",
  );
}
