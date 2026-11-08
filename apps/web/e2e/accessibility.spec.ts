import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
for (const route of ["video", "live", "benchmark"]) {
  test(`acessibilidade inicial e cabeçalhos: ${route}`, async ({ page }) => {
    const response = await page.goto(`/${route}`);
    expect(response?.headers()["x-content-type-options"]).toBe("nosniff");
    expect(response?.headers()["permissions-policy"]).toContain(
      "microphone=()",
    );
    await expect(page.locator(".sidebar .mono")).toContainText("v1.0.0");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(
      results.violations.map((v) => ({
        id: v.id,
        impact: v.impact,
        nodes: v.nodes.map((n) => ({
          target: n.target,
          summary: n.failureSummary,
        })),
      })),
    ).toEqual([]);
  });
}
