import { test, expect } from "@playwright/test";
import path from "node:path";
const root = path.resolve(__dirname, "../../..");
test("relatório real do runner artificial → filtros → gráficos → export → descarte", async ({
  page,
  context,
}) => {
  const requests: { url: string; method: string }[] = [],
    errors: string[] = [];
  context.on("request", (r) =>
    requests.push({ url: r.url(), method: r.method() }),
  );
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/benchmark");
  await expect(
    page.getByRole("heading", { name: "Nenhum resultado importado." }),
  ).toBeVisible();
  await expect(page.locator("table")).toHaveCount(0);
  await page
    .getByLabel("Selecionar relatório de benchmark")
    .setInputFiles(process.env.PULSEVISION_BENCHMARK_FIXTURE!);
  await expect(
    page.getByText("DEMONSTRAÇÃO ARTIFICIAL — sem precisão fisiológica", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(9);
  await page.getByLabel("Janela", { exact: true }).selectOption("20");
  await expect(page.locator("tbody tr")).toHaveCount(3);
  await page.getByLabel("Método", { exact: true }).selectOption("POS");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await expect(
    page.getByRole("img", { name: /Cobertura por grupo/ }),
  ).toBeVisible();
  await page.getByLabel("Agrupar por").selectOption("participant");
  await expect(page.locator("tbody tr")).toHaveCount(3);
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Resumo CSV" }).click();
  expect((await download).suggestedFilename()).toBe(
    "pulsevision-benchmark-recorte.csv",
  );
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: path.join(root, "artifacts/wave10-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: path.join(root, "artifacts/wave10-mobile.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Descartar revisão" }).click();
  await expect(page.locator("table")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Nenhum resultado importado." }),
  ).toBeVisible();
  expect(requests.filter((r) => r.method !== "GET")).toEqual([]);
  expect(
    requests.filter((r) => new URL(r.url).pathname.startsWith("/api/")),
  ).toEqual([]);
  expect(errors).toEqual([]);
});
test("importação inválida é recusada sem preencher resultados", async ({
  page,
}) => {
  await page.goto("/benchmark");
  await page.getByLabel("Selecionar relatório de benchmark").setInputFiles({
    name: "invalid.json",
    mimeType: "application/json",
    buffer: Buffer.from('{"schema_version":"unknown"}'),
  });
  await expect(page.locator(".alert")).toContainText("incompatível");
  await expect(page.locator("table")).toHaveCount(0);
});
