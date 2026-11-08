"use client";
import { memo } from "react";
import { Chart } from "./chart";
import type { RgbPoint, RppgPoint, SpectrumPoint } from "./api";
import type { EstimateResult } from "../../../../packages/rppg_types/generated/EstimateResult";
export const SignalCharts = memo(function SignalCharts({
  rppg,
  spectrum,
  rgb,
  estimates,
}: {
  rppg: RppgPoint[];
  spectrum: SpectrumPoint[];
  rgb: RgbPoint[];
  estimates: EstimateResult[];
}) {
  return (
    <div className="charts-grid">
      <Chart
        title="Sinal rPPG"
        points={rppg.map((p) => ({
          x: p.timestamp_s,
          y: p.value ?? null,
        }))}
        xLabel="Tempo da sessão (s)"
        yLabel="Amplitude (u.a.)"
      />
      <Chart
        title="Espectro de potência"
        points={spectrum.map((p) => ({
          x: p.frequency_hz,
          y: p.power ?? null,
        }))}
        xLabel="Frequência (Hz)"
        yLabel="PSD (u.a.²/Hz)"
        color="#7484c2"
      />
      <Chart
        title="RGB médio da ROI"
        points={rgb.map((p) => ({
          x: p.timestamp_s,
          y: p.g ?? null,
        }))}
        extra={[
          {
            label: "R",
            color: "#b75e68",
            points: rgb.map((p) => ({
              x: p.timestamp_s,
              y: p.r ?? null,
            })),
          },
          {
            label: "B",
            color: "#7484c2",
            points: rgb.map((p) => ({
              x: p.timestamp_s,
              y: p.b ?? null,
            })),
          },
        ]}
        xLabel="Tempo da sessão (s)"
        yLabel="RGB médio (0–255)"
      />
      <Chart
        title="BPM ao longo do tempo"
        points={estimates.map((item) => ({
          x: item.window.end_s,
          y: item.bpm,
        }))}
        xLabel="Fim da janela (s)"
        yLabel="BPM estimado"
      />
    </div>
  );
});
