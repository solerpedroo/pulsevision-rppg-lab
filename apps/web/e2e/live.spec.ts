import { test, expect } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";
const root = path.resolve(__dirname, "../../..");
test.afterEach(async ({ page }, info) => {
  if (info.status !== info.expectedStatus) {
    console.log(
      "LIVE FAILURE",
      await page.locator(".pill").allTextContents(),
      await page.locator(".alert").allTextContents(),
    );
    await info.attach("ui-state", {
      body: await page.locator("body").innerText(),
      contentType: "text/plain",
    });
  }
});
test("webcam artificial: worker real, abstenção, rede sem frames, export e Stop", async ({
  page,
  context,
}) => {
  test.setTimeout(90000);
  const requests: { url: string; method: string }[] = [],
    errors: string[] = [];
  context.on("request", (request) =>
    requests.push({ url: request.url(), method: request.method() }),
  );
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/live");
  await expect(
    page.getByRole("button", { name: "Iniciar câmera" }),
  ).toBeEnabled();
  expect(
    await page
      .locator("video")
      .evaluate((v) => (v as HTMLVideoElement).srcObject),
  ).toBeNull();
  await page.getByRole("button", { name: "Iniciar câmera" }).click();
  await page.waitForFunction(
    () =>
      document.querySelector(".alert") ||
      document
        .querySelector(".status-strip")
        ?.textContent?.includes("Face não encontrada"),
    null,
    { timeout: 35000 },
  );
  await expect(page.locator(".alert")).toHaveCount(0);
  await expect
    .poll(() => page.locator(".preview-footer .mono").textContent(), {
      timeout: 35000,
    })
    .toMatch(/2[0-9]\.\d s/);
  await expect(page.locator(".metric").first().locator("strong")).toHaveText(
    "—",
  );
  await page.evaluate(() => {
    const tracks = (
      (document.querySelector("video") as HTMLVideoElement)
        .srcObject as MediaStream
    ).getTracks();
    (window as unknown as { testTracks: MediaStreamTrack[] }).testTracks =
      tracks;
  });
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Exportar séries JSON" }).click();
  const download = await downloadPromise;
  const exported = path.join(root, "artifacts/wave9-export.json");
  await download.saveAs(exported);
  const data = JSON.parse(await fs.readFile(exported, "utf8"));
  expect(data.rows.length).toBeGreaterThan(100);
  expect(data.rows.length).toBeLessThanOrEqual(900);
  expect(data.rows.every((s: { rgb: unknown }) => s.rgb === null)).toBe(true);
  expect(data.analyses.length).toBeGreaterThan(0);
  expect(data.analyses.every((a: { bpm: unknown }) => a.bpm === null)).toBe(
    true,
  );
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: path.join(root, "artifacts/wave9-desktop.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Stop · desligar e descartar" })
    .click();
  await expect(page.locator(".pill")).toHaveText("Câmera desligada");
  expect(
    await page
      .locator("video")
      .evaluate((v) => (v as HTMLVideoElement).srcObject),
  ).toBeNull();
  expect(
    await page.evaluate(() =>
      (
        window as unknown as { testTracks: MediaStreamTrack[] }
      ).testTracks.every((t) => t.readyState === "ended"),
    ),
  ).toBe(true);
  await expect(
    page.getByRole("button", { name: "Exportar séries JSON" }),
  ).toBeDisabled();
  expect(
    requests.filter((r) => ["POST", "PUT", "PATCH"].includes(r.method)),
  ).toEqual([]);
  expect(
    requests.filter((r) => new URL(r.url).pathname.startsWith("/api/")),
  ).toEqual([]);
  expect(
    requests.filter((r) => !r.url.startsWith("http://localhost:3000/")),
  ).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: path.join(root, "artifacts/wave9-mobile.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});
test("permissão negada permite tentar novamente", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
      configurable: true,
      value: () =>
        Promise.reject(new DOMException("Denied", "NotAllowedError")),
    });
  });
  await page.goto("/live");
  await page.getByRole("button", { name: "Iniciar câmera" }).click();
  await expect(page.locator(".alert[role=alert]")).toContainText(
    "Permissão de câmera negada",
  );
  await expect(
    page.getByRole("button", { name: "Iniciar câmera" }),
  ).toBeEnabled();
});
test("perda de foco, troca de câmera, dispositivo encerrado e saída liberam captura", async ({
  page,
}) => {
  test.setTimeout(90000);
  await page.goto("/live");
  async function start() {
    await page.getByRole("button", { name: "Iniciar câmera" }).click();
    await expect(page.locator(".status-strip")).toContainText(
      "Face não encontrada",
      { timeout: 35000 },
    );
  }
  await start();
  await page.evaluate(() => window.dispatchEvent(new Event("blur")));
  await expect(page.locator(".pill")).toHaveText("Câmera desligada");
  await start();
  await page.getByLabel("Câmera", { exact: true }).selectOption({ index: 1 });
  await expect(page.locator(".pill")).toHaveText("Câmera desligada");
  await start();
  await page.evaluate(() => {
    const stream = (document.querySelector("video") as HTMLVideoElement)
      .srcObject as MediaStream;
    stream.getVideoTracks()[0].dispatchEvent(new Event("ended"));
  });
  await expect(page.locator(".alert[role=alert]")).toContainText(
    "desconectada",
  );
  await start();
  await page.evaluate(() => {
    Object.defineProperty(document, "hidden", {
      configurable: true,
      get: () => true,
    });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await expect(page.locator(".pill")).toHaveText("Câmera desligada");
  await page.evaluate(() => Reflect.deleteProperty(document, "hidden"));
  await start();
  await page.evaluate(() => {
    (window as unknown as { unmountTracks: MediaStreamTrack[] }).unmountTracks =
      (
        (document.querySelector("video") as HTMLVideoElement)
          .srcObject as MediaStream
      ).getTracks();
  });
  await page.getByRole("link", { name: "Video Lab 01", exact: true }).click();
  await expect(page).toHaveURL(/\/video$/);
  expect(
    await page.evaluate(() =>
      (
        window as unknown as { unmountTracks: MediaStreamTrack[] }
      ).unmountTracks.every((t) => t.readyState === "ended"),
    ),
  ).toBe(true);
  await page.goBack();
  await expect(page.locator(".pill")).toHaveText("Câmera desligada");
  await start();
  await page.reload();
  await expect(page.locator(".pill")).toHaveText("Câmera desligada");
});

test("Stop durante permissão pendente libera stream que chega depois", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const original = navigator.mediaDevices.getUserMedia.bind(
      navigator.mediaDevices,
    );
    Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
      value: async (constraints: MediaStreamConstraints) => {
        const stream = await original(constraints);
        (window as unknown as { lateTracks: MediaStreamTrack[] }).lateTracks =
          stream.getTracks();
        return new Promise<MediaStream>((resolve) => {
          (
            window as unknown as { releasePermission: () => void }
          ).releasePermission = () => resolve(stream);
        });
      },
    });
  });
  await page.goto("/live");
  await page.getByRole("button", { name: "Iniciar câmera" }).click();
  await page.waitForFunction(() => "releasePermission" in window);
  await page
    .getByRole("button", { name: "Stop · desligar e descartar" })
    .click();
  await page.evaluate(() =>
    (
      window as unknown as { releasePermission: () => void }
    ).releasePermission(),
  );
  await expect
    .poll(() =>
      page.evaluate(() =>
        (
          window as unknown as { lateTracks: MediaStreamTrack[] }
        ).lateTracks.every((t) => t.readyState === "ended"),
      ),
    )
    .toBe(true);
  await expect(page.locator(".pill")).toHaveText("Câmera desligada");
  expect(
    await page
      .locator("video")
      .evaluate((v) => (v as HTMLVideoElement).srcObject),
  ).toBeNull();
});
