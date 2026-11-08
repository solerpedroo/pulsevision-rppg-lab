"use client";
import { useId } from "react";
type XY = { x: number; y: number | null };
type Series = { label: string; color: string; points: XY[] };
export function Chart({
  title,
  points,
  xLabel,
  yLabel,
  color = "#268b81",
  extra = [],
}: {
  title: string;
  points: XY[];
  xLabel: string;
  yLabel: string;
  color?: string;
  extra?: Series[];
}) {
  const id = useId(),
    series: Series[] = [
      { label: extra.length ? "G" : title, color, points },
      ...extra,
    ];
  const all = series.flatMap((s) => s.points),
    finite = all.filter(
      (p) => p.y !== null && Number.isFinite(p.y) && Number.isFinite(p.x),
    );
  const xmin = all.length ? Math.min(...all.map((p) => p.x)) : 0,
    xmax = all.length ? Math.max(...all.map((p) => p.x)) : 1;
  const ymin = finite.length ? Math.min(...finite.map((p) => p.y!)) : 0,
    ymax = finite.length ? Math.max(...finite.map((p) => p.y!)) : 1;
  const pad = Math.max((ymax - ymin) * 0.12, 0.01),
    ylo = ymin - pad,
    yhi = ymax + pad;
  const x = (v: number) =>
      52 + ((v - xmin) / Math.max(xmax - xmin, 0.001)) * 540,
    y = (v: number) => 148 - ((v - ylo) / (yhi - ylo)) * 120;
  function path(data: XY[]) {
    let result = "",
      connected = false;
    for (const p of data) {
      if (p.y === null || !Number.isFinite(p.y) || !Number.isFinite(p.x)) {
        connected = false;
        continue;
      }
      result += `${connected ? "L" : "M"}${x(p.x).toFixed(2)},${y(p.y).toFixed(2)} `;
      connected = true;
    }
    return result;
  }
  return (
    <section className="chart-card">
      <div className="card-heading">
        <h3>{title}</h3>
        <span className="mono">{yLabel}</span>
      </div>
      {extra.length > 0 && (
        <p className="chart-legend">
          {series.map((s) => (
            <span key={s.label} style={{ color: s.color }}>
              ● {s.label}{" "}
            </span>
          ))}
        </p>
      )}
      {!finite.length ? (
        <div className="chart-empty">Sem dados válidos nesta janela</div>
      ) : (
        <svg role="img" aria-labelledby={id} viewBox="0 0 620 192">
          <title id={id}>
            {title}. Eixo horizontal: {xLabel}. Eixo vertical: {yLabel}. Lacunas
            representam ausência de estimativa.
          </title>
          {[0, 0.5, 1].map((t) => (
            <g key={t}>
              <line
                x1="52"
                x2="592"
                y1={28 + t * 120}
                y2={28 + t * 120}
                stroke="#e8edef"
              />
              <text x="44" y={32 + t * 120} textAnchor="end">
                {(yhi - t * (yhi - ylo)).toFixed(2)}
              </text>
            </g>
          ))}
          {series.map((s) => (
            <g key={s.label}>
              <path
                d={path(s.points)}
                stroke={s.color}
                strokeWidth="2"
                fill="none"
              />
              {s.points
                .filter(
                  (p, i) =>
                    p.y !== null &&
                    Number.isFinite(p.y) &&
                    (s.points[i - 1]?.y == null || s.points[i + 1]?.y == null),
                )
                .map((p, i) => (
                  <circle
                    key={i}
                    cx={x(p.x)}
                    cy={y(p.y!)}
                    r="2.5"
                    fill={s.color}
                  />
                ))}
            </g>
          ))}
          <text x="52" y="169">
            {xmin.toFixed(1)}
          </text>
          <text x="592" y="169" textAnchor="end">
            {xmax.toFixed(1)}
          </text>
          <text x="322" y="187" textAnchor="middle">
            {xLabel}
          </text>
        </svg>
      )}
    </section>
  );
}
