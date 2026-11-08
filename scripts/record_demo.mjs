// Record only this app's synthetic benchmark page; no desktop or physical camera.
import { chromium } from "@playwright/test";
import { execFileSync, spawn } from "node:child_process";
import {
  mkdirSync,
  mkdtempSync,
  openSync,
  closeSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const port = Number(process.env.PULSEVISION_DEMO_PORT ?? 3200);
if (!Number.isInteger(port) || port < 1024 || port > 65535)
  throw Error("Invalid local demo port");
const url = `http://127.0.0.1:${port}`;
try {
  await fetch(url, { signal: AbortSignal.timeout(1500) });
  throw Error(`Demo port ${port} is occupied; choose PULSEVISION_DEMO_PORT`);
} catch (error) {
  if (!error.cause || error.cause.code !== "ECONNREFUSED") throw error;
}
mkdirSync(path.join(root, "artifacts"), { recursive: true });
const output = mkdtempSync(path.join(root, "artifacts/wave11-demo-"));
execFileSync(
  "uv",
  [
    "run",
    "python",
    "-m",
    "benchmarks.study",
    "demo",
    "--output",
    path.join(output, "study"),
  ],
  { cwd: root, stdio: "inherit" },
);
const descriptor = openSync(path.join(output, "server.log"), "w", 0o600);
const server = spawn(
  "npm",
  [
    "run",
    "start",
    "-w",
    "apps/web",
    "--",
    "--hostname",
    "127.0.0.1",
    "--port",
    String(port),
  ],
  {
    cwd: root,
    detached: true,
    stdio: ["ignore", descriptor, descriptor],
    env: { ...process.env, NEXT_TELEMETRY_DISABLED: "1" },
  },
);
closeSync(descriptor);
let browser;
try {
  let ready = false;
  for (let attempt = 0; attempt < 120; attempt++) {
    if (server.exitCode !== null)
      throw Error("Demo server exited; inspect its local log");
    try {
      ready = (
        await fetch(`${url}/benchmark`, { signal: AbortSignal.timeout(1500) })
      ).ok;
    } catch {
      /* starting */
    }
    if (ready) break;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  if (!ready) throw Error("Demo server did not become ready");
  browser = await chromium.launch({
    args: ["--use-fake-device-for-media-stream"],
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    recordVideo: { dir: output, size: { width: 1440, height: 1000 } },
  });
  const page = await context.newPage();
  await page.goto(`${url}/benchmark`);
  await page
    .getByRole("heading", { name: "Nenhum resultado importado." })
    .waitFor();
  await page.waitForTimeout(1500);
  const fixture = path.join(
    output,
    "study/results/review/benchmark-review-v1.json",
  );
  await page
    .getByLabel("Selecionar relatório de benchmark")
    .setInputFiles(fixture);
  await page
    .getByText("DEMONSTRAÇÃO ARTIFICIAL — sem precisão fisiológica", {
      exact: true,
    })
    .waitFor();
  await page.waitForTimeout(2500);
  await page.getByLabel("Janela", { exact: true }).selectOption("20");
  await page.waitForTimeout(2000);
  await page.getByLabel("Método", { exact: true }).selectOption("POS");
  await page.waitForTimeout(2000);
  await page.getByLabel("Agrupar por").selectOption("participant");
  await page.waitForTimeout(2500);
  await page.screenshot({
    path: path.join(output, "synthetic-demo.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Descartar revisão" }).click();
  await page.waitForTimeout(1500);
  const video = page.video();
  await context.close();
  writeFileSync(
    path.join(output, "recording.json"),
    JSON.stringify(
      {
        created_at: new Date().toISOString(),
        kind: "artificial_benchmark_browser_recording",
        physical_camera: false,
        desktop_capture: false,
        physiological_validation: false,
        fixture,
        video: await video.path(),
      },
      null,
      2,
    ) + "\n",
  );
  console.log(`Synthetic demo saved locally: ${output}`);
} finally {
  await browser?.close();
  try {
    process.kill(-server.pid, "SIGTERM");
  } catch {
    /* already stopped */
  }
}
