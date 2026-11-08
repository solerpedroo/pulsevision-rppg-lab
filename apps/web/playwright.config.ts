import { defineConfig } from "@playwright/test";
import path from "node:path";
const root = path.resolve(__dirname, "../..");
const apiPort = process.env.PULSEVISION_API_PORT ?? "8000";
const apiUrl = `http://127.0.0.1:${apiPort}`;
const webPort = process.env.PULSEVISION_WEB_PORT ?? "3000";
const webUrl = `http://localhost:${webPort}`;
export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  use: { baseURL: webUrl, trace: "retain-on-failure" },
  outputDir: "../../artifacts/wave8-browser",
  webServer: [
    {
      command: `uv run uvicorn services.api.app.main:app --host 127.0.0.1 --port ${apiPort} --workers 1`,
      cwd: root,
      url: `${apiUrl}/api/v1/health`,
      env: {
        PULSEVISION_STORAGE: path.join(root, "artifacts/wave8-e2e-api"),
        PULSEVISION_WEB_ORIGINS: `${webUrl},http://127.0.0.1:${webPort}`,
      },
      reuseExistingServer: false,
    },
    {
      command: `npm run dev -w apps/web -- --port ${webPort}`,
      cwd: root,
      url: `${webUrl}/video`,
      env: { NEXT_PUBLIC_PULSEVISION_API_URL: apiUrl },
      reuseExistingServer: false,
    },
  ],
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
        permissions: ["camera"],
        launchOptions: {
          args: [
            "--use-fake-device-for-media-stream",
            "--use-fake-ui-for-media-stream",
            `--use-file-for-fake-video-capture=${path.join(root, "artifacts/wave9-camera.y4m")}`,
            "--use-gl=angle",
            "--use-angle=swiftshader",
            "--enable-unsafe-swiftshader",
          ],
        },
      },
    },
  ],
});
