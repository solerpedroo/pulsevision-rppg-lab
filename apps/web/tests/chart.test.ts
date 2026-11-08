import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { Chart } from "../features/video/chart";
const labels = {
  title: "Sinal artificial de teste",
  xLabel: "Tempo (s)",
  yLabel: "Amplitude (u.a.)",
};
it("mantém lacunas entre pontos isolados e informa unidades", () => {
  const html = renderToStaticMarkup(
    createElement(Chart, {
      ...labels,
      points: [
        { x: 0, y: 1 },
        { x: 1, y: null },
        { x: 2, y: 2 },
      ],
    }),
  );
  const path = html.match(/<path d="([^"]*)"/)?.[1];
  expect(path?.match(/M/g)).toHaveLength(2);
  expect(path).not.toContain("L");
  expect(html.match(/<circle/g)).toHaveLength(2);
  expect(html).toContain("Tempo (s)");
  expect(html).toContain("Amplitude (u.a.)");
});
it("ausência não cria curva e amplitude constante não divide por zero", () => {
  const empty = renderToStaticMarkup(
    createElement(Chart, { ...labels, points: [{ x: 0, y: null }] }),
  );
  expect(empty).toContain("Sem dados válidos");
  expect(empty).not.toContain("<path");
  const constant = renderToStaticMarkup(
    createElement(Chart, {
      ...labels,
      points: [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
      ],
    }),
  );
  expect(constant).not.toMatch(/NaN|Infinity/);
  expect(constant).toContain("<path");
});
