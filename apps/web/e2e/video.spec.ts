import { test, expect } from "@playwright/test";
import { execFileSync } from "node:child_process";
import path from "node:path";
const root = path.resolve(__dirname, "../../..");
test.beforeAll(() => {
  execFileSync("uv", ["run", "python", "scripts/generate_browser_fixture.py"], {
    cwd: root,
  });
});
test("upload real, abstenção, revisão, exportação, recálculo e exclusão", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/video");
  await expect(page.getByText("API conectada", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Iniciar análise" }),
  ).toBeDisabled();
  await page
    .getByLabel("Selecionar vídeo")
    .setInputFiles(path.join(root, "artifacts/wave8-fixture.mp4"));
  await page.getByRole("checkbox").check();
  await expect(
    page.getByRole("button", { name: "Iniciar análise" }),
  ).toBeEnabled();
  await page.getByLabel("Método rPPG").selectOption("POS");
  await page.getByLabel("Região de interesse").selectOption("forehead");
  const submitted = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().includes("/videos/jobs?"),
  );
  const firstPoll = page.waitForRequest(
    (r) =>
      r.method() === "GET" &&
      /videos\/jobs\/[^/]+$/.test(new URL(r.url()).pathname),
  );
  await page.getByRole("button", { name: "Iniciar análise" }).click();
  expect((await submitted).status()).toBe(202);
  const job = {
    id: new URL((await firstPoll).url()).pathname.split("/").at(-1),
  };
  await expect(
    page.getByText("Análise disponível", { exact: true }),
  ).toBeVisible({ timeout: 45000 });
  await expect(page.getByLabel("Janela de análise")).toBeVisible();
  await expect(
    page.getByText("Sinal insuficiente para estimar", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Regiões detectadas neste instante"),
  ).toHaveCount(1);
  await expect(page.locator(".roi-overlay polygon")).toHaveCount(0);
  const results = await (
    await request.get(
      `http://127.0.0.1:8000/api/v1/videos/jobs/${job.id}/results`,
    )
  ).json();
  expect(results.items[0].bpm).toBeNull();
  expect(results.items[0].roi).toBe("forehead");
  await page.getByRole("slider").fill("1");
  await expect
    .poll(() =>
      page
        .locator("video")
        .evaluate((v) => (v as HTMLVideoElement).currentTime),
    )
    .toBeCloseTo(1, 1);
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "JSON", exact: true }).click();
  const exported = await download;
  expect(exported.suggestedFilename()).toBe("pulsevision-pos.json");
  await exported.saveAs(path.join(root, "artifacts/wave8-export.json"));
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: path.join(root, "artifacts/wave8-desktop.png"),
    fullPage: true,
  });
  await page.getByLabel("Método rPPG").selectOption("CHROM");
  const recalculated = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().includes("/videos/jobs?"),
  );
  const nextPoll = page.waitForRequest(
    (r) =>
      r.method() === "GET" &&
      /videos\/jobs\/[^/]+$/.test(new URL(r.url()).pathname),
  );
  await page
    .getByRole("button", { name: "Reanalisar com nova configuração" })
    .click();
  expect((await recalculated).status()).toBe(202);
  const next = {
    id: new URL((await nextPoll).url()).pathname.split("/").at(-1),
  };
  expect(next.id).not.toBe(job.id);
  expect(
    (
      await request.get(`http://127.0.0.1:8000/api/v1/videos/jobs/${job.id}`)
    ).status(),
  ).toBe(404);
  await expect(
    page.getByText("Análise disponível", { exact: true }),
  ).toBeVisible({ timeout: 45000 });
  await expect(page.getByLabel("Janela de análise")).toBeVisible();
  await page.getByRole("button", { name: "Excluir sessão" }).click();
  await expect(page.getByLabel("Janela de análise")).toHaveCount(0);
  await expect(page.locator("video")).toHaveCount(0);
  await expect(page.getByRole("checkbox")).not.toBeChecked();
  expect(
    (
      await request.get(`http://127.0.0.1:8000/api/v1/videos/jobs/${next.id}`)
    ).status(),
  ).toBe(404);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: path.join(root, "artifacts/wave8-mobile.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});
test("validação de arquivo e recuperação da conexão", async ({ page }) => {
  await page.goto("/video");
  await expect(page.getByText("API conectada", { exact: true })).toBeVisible();
  await page.getByLabel("Selecionar vídeo").setInputFiles({
    name: "invalid.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("invalid"),
  });
  await expect(page.locator(".alert[role=alert]")).toContainText(
    "Selecione MP4",
  );
  await page.getByRole("button", { name: "Fechar mensagem" }).click();
  await page.getByText("Conexão com o laboratório", { exact: true }).click();
  await page.getByLabel("Endereço da API").fill("https://example.org");
  await page.getByRole("button", { name: "Conectar", exact: true }).click();
  await expect(page.locator(".alert[role=alert]")).toContainText(
    "Use um endereço local",
  );
  await page.route("**/api/v1/policy", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "service_unavailable" }),
    }),
  );
  await page.getByLabel("Endereço da API").fill("http://127.0.0.1:8000");
  await page.getByRole("button", { name: "Conectar", exact: true }).click();
  await expect(
    page.getByText("API indisponível", { exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Selecionar vídeo")).toBeDisabled();
  await page.unroute("**/api/v1/policy");
  await page.getByRole("button", { name: "Conectar", exact: true }).click();
  await expect(page.getByText("API conectada", { exact: true })).toBeVisible();
});

test("cancelamento e falha têm estados explícitos (API simulada)", async ({
  page,
}) => {
  let failed = false;
  const job = {
    id: "synthetic-ui-job",
    status: "processing",
    method: "GREEN",
    roi: "combined",
    progress: 0.25,
    error: null,
    expires_at: Date.now() / 1000 + 86400,
  };
  await page.route("**/api/v1/videos/jobs**", async (route) => {
    const request = route.request(),
      pathname = new URL(request.url()).pathname;
    const headers = { "access-control-allow-origin": "http://localhost:3000" };
    if (request.method() === "DELETE")
      return route.fulfill({ status: 204, headers });
    if (pathname.endsWith("/cancel"))
      return route.fulfill({
        status: 200,
        headers,
        json: { ...job, status: "cancelled" },
      });
    return route.fulfill({
      status: request.method() === "POST" ? 202 : 200,
      headers,
      json: failed
        ? { ...job, status: "failed", error: "video_limits_exceeded" }
        : job,
    });
  });
  await page.goto("/");
  await expect(page).toHaveURL(/\/video$/);
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Ir ao laboratório" }),
  ).toBeFocused();
  await expect(page.getByText("API conectada", { exact: true })).toBeVisible();
  await page
    .getByLabel("Selecionar vídeo")
    .setInputFiles(path.join(root, "artifacts/wave8-fixture.mp4"));
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Iniciar análise" }).click();
  await expect(page.getByRole("progressbar")).toBeVisible();
  await page.getByRole("button", { name: "Cancelar", exact: true }).click();
  await expect(page.locator(".pill")).toHaveText("Cancelado");
  await expect(page.getByRole("progressbar")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "JSON", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Excluir sessão" }).click();
  failed = true;
  await page
    .getByLabel("Selecionar vídeo")
    .setInputFiles(path.join(root, "artifacts/wave8-fixture.mp4"));
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Iniciar análise" }).click();
  await expect(page.locator(".pill")).toHaveText("Falha na análise");
  await expect(
    page.getByText("Vídeo excede os limites de processamento", { exact: true }),
  ).toBeVisible();
});
