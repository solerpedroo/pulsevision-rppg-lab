import { defineConfig } from "@playwright/test";
import path from "node:path";
const root = path.resolve(__dirname, "../..");
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  use: { baseURL: "http://localhost:3000", trace: "retain-on-failure" },
  outputDir: "../../artifacts/wave8-browser",
  webServer: [
    {
      command:
        "uv run uvicorn services.api.app.main:app --host 127.0.0.1 --port 8000 --workers 1",
      cwd: root,
      url: "http://127.0.0.1:8000/api/v1/health",
      env: { PULSEVISION_STORAGE: path.join(root, "artifacts/wave8-e2e-api") },
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -w apps/web",
      cwd: root,
      url: "http://localhost:3000/video",
      reuseExistingServer: false,
    },
  ],
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
