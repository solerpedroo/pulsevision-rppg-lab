"use client";
import { useId } from "react";
import type { Group } from "./data";
const colors: Record<string, string> = {
  GREEN: "#268b81",
  CHROM: "#7985bd",
  POS: "#b18a51",
};
export function MetricBars({
  groups,
  metric,
  title,
  unit,
}: {
  groups: Group[];
  metric: "mae" | "rmse" | "medae" | "bias" | "coverage";
  title: string;
  unit: string;
}) {
  const id = useId(),
    values = groups
      .map((g) => g[metric])
      .filter((v): v is number => v !== null),
    lo = Math.min(0, ...values),
    hi = Math.max(metric === "coverage" ? 1 : 0.01, ...values),
    span = hi - lo || 1,
    x = (v: number) => 220 + ((v - lo) / span) * 340,
    height = 55 + groups.length * 32;
  return (
    <section className="chart-card">
      <div className="card-heading">
        <h3>{title}</h3>
        <span className="mono">{unit}</span>
      </div>
      {!groups.length ? (
        <p className="empty-state">Nenhum grupo neste recorte.</p>
      ) : (
        <div className="bench-plot">
          <svg viewBox={`0 0 620 ${height}`} role="img" aria-labelledby={id}>
            <title id={id}>
              {title}. Eixo horizontal: {unit}. Grupos no eixo vertical. Valores
              ausentes são indisponíveis.
            </title>
            {[lo, (lo + hi) / 2, hi].map((v, i) => (
              <g key={i}>
                <line
                  x1={x(v)}
                  x2={x(v)}
                  y1="10"
                  y2={height - 25}
                  stroke="#e2e8eb"
                />
                <text x={x(v)} y={height - 8} textAnchor="middle">
                  {v.toFixed(2)}
                </text>
              </g>
            ))}
            {groups.map((g, i) => {
              const value = g[metric],
                y = 20 + i * 32;
              return (
                <g key={g.label}>
                  <title>
                    {g.label}:{" "}
                    {value === null
                      ? "indisponível"
                      : value.toFixed(3) + " " + unit}
                  </title>
                  <text x="210" y={y + 5} textAnchor="end">
                    {g.label.length > 34 ? g.label.slice(0, 31) + "…" : g.label}
                  </text>
                  {value === null ? (
                    <text x={x(0) + 8} y={y + 5}>
                      —
                    </text>
                  ) : (
                    <>
                      <rect
                        x={Math.min(x(0), x(value))}
                        y={y - 7}
                        width={Math.abs(x(value) - x(0))}
                        height="15"
                        rx="2"
                        fill={colors[g.method]}
                      />
                      <circle
                        cx={x(value)}
                        cy={y + 0.5}
                        r="2.5"
                        fill="#233e43"
                      />
                      <text x={x(value) + 5} y={y + 5}>
                        {value.toFixed(2)}
                      </text>
                    </>
                  )}
                </g>
              );
            })}
          </svg>
        </div>
      )}
    </section>
  );
}
