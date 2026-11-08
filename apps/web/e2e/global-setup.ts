import { execFileSync } from "node:child_process";
import path from "node:path";
export default function setup() {
  const root = path.resolve(__dirname, "../../..");
  execFileSync("uv", ["run", "python", "scripts/generate_camera_fixture.py"], {
    cwd: root,
  });
  execFileSync("node", ["scripts/prepare_live_assets.mjs"], { cwd: root });
}
