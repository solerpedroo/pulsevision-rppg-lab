"use client";
import { useEffect, useRef, useState, memo } from "react";
import Link from "next/link";
import {
  Activity,
  Radio,
  ShieldCheck,
  Square,
  Download,
  Video,
  FlaskConical,
  Info,
} from "lucide-react";
import { Chart } from "../video/chart";
import { explain, roiLabels, type Method, type Roi } from "../video/api";
import { freshnessDelayMs } from "./display";
import { LiveSession } from "./session";
import type { Analysis, FrameReport, Phase } from "./types";
const phases: Record<Phase, string> = {
  stopped: "Câmera desligada",
  permission: "Aguardando permissão",
  detector: "Iniciando detector local",
  warmup: "Aquecimento",
  result: "Estimativa disponível",
  abstention: "Sem estimativa",
  error: "Câmera desligada após erro",
};
const LiveCharts = memo(function LiveCharts({
  analysis,
}: {
  analysis: Analysis | null;
}) {
  return (
    <div className="charts-grid">
      <Chart
        title="Sinal rPPG da janela"
        points={
          analysis?.signal.map((y, i) => ({ x: analysis.timestamps[i], y })) ??
          []
        }
        xLabel="Tempo da sessão (s)"
        yLabel="Amplitude (u.a.)"
      />
      <Chart
        title="Espectro de potência"
        points={
          analysis?.power.map((y, i) => ({ x: analysis.frequencies[i], y })) ??
          []
        }
        xLabel="Frequência (Hz)"
        yLabel="PSD (u.a.²/Hz)"
        color="#7484c2"
      />
    </div>
  );
});
export function LiveLab() {
  const video = useRef<HTMLVideoElement>(null),
    session = useRef<LiveSession | null>(null),
    expiry = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [phase, setPhase] = useState<Phase>("stopped"),
    [error, setError] = useState(""),
    [devices, setDevices] = useState<MediaDeviceInfo[]>([]),
    [device, setDevice] = useState(""),
    [method, setMethod] = useState<Method>("GREEN"),
    [roi, setRoi] = useState<Roi>("combined"),
    [mirror, setMirror] = useState(true),
    [report, setReport] = useState<FrameReport | null>(null),
    [analysis, setAnalysis] = useState<Analysis | null>(null),
    [skipped, setSkipped] = useState(0),
    [aspect, setAspect] = useState(4 / 3),
    [stale, setStale] = useState(false);
  const active = !["stopped", "error"].includes(phase);
  useEffect(
    () => () => {
      session.current?.dispose();
      if (expiry.current) clearTimeout(expiry.current);
    },
    [],
  );
  function changePhase(next: Phase, message?: string) {
    setPhase(next);
    if (message) setError(message);
    if (next === "stopped" || next === "error") {
      if (expiry.current) clearTimeout(expiry.current);
      setStale(false);
      setReport(null);
      setAnalysis(null);
    }
  }
  function stop() {
    session.current?.stop();
    session.current = null;
    setSkipped(0);
  }
  function start() {
    if (active || !video.current) return;
    session.current?.dispose();
    setError("");
    setReport(null);
    setAnalysis(null);
    setSkipped(0);
    const next = new LiveSession(video.current, method, roi, {
      phase: changePhase,
      devices: setDevices,
      frame: (frame, skips) => {
        setReport(frame);
        setSkipped(skips);
        setStale(false);
        if (expiry.current) clearTimeout(expiry.current);
        if (frame.analysis)
          expiry.current = setTimeout(
            () => {
              setAnalysis(null);
              setStale(true);
              setPhase("abstention");
            },
            freshnessDelayMs(frame.analysis, frame.timestamp_s),
          );
        const fresh =
          frame.analysis && frame.timestamp_s - frame.analysis.end_s <= 3
            ? frame.analysis
            : null;
        setAnalysis((previous) => {
          if (!fresh) return null;
          if (
            previous &&
            previous.end_s === fresh.end_s &&
            previous.bpm === fresh.bpm &&
            previous.reasons.join() === fresh.reasons.join()
          )
            return previous;
          return fresh;
        });
        setPhase(
          frame.display_reasons.length || fresh?.bpm === null
            ? "abstention"
            : fresh?.bpm != null
              ? "result"
              : "warmup",
        );
      },
    });
    session.current = next;
    void next.start(device);
  }
  function download() {
    if (!session.current || !report) return;
    const url = URL.createObjectURL(
        new Blob([JSON.stringify(session.current.export(), null, 2)], {
          type: "application/json",
        }),
      ),
      link = document.createElement("a");
    link.href = url;
    link.download = `pulsevision-live-${method.toLowerCase()}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const reasons = stale
      ? ["stale_estimate"]
      : report?.display_reasons.length
        ? report.display_reasons
        : (analysis?.reasons ?? []),
    polygons = Object.entries(report?.polygons ?? {}).filter(
      ([name]) => roi === "combined" || name === roi,
    );
  return (
    <div className="lab-shell">
      <a href="#workspace" className="skip">
        Ir ao laboratório
      </a>
      <aside className="sidebar">
        <Link href="/video" className="brand">
          <span className="brand-mark">
            <Activity size={24} />
          </span>
          <span>
            PulseVision<small>rPPG RESEARCH LAB</small>
          </span>
        </Link>
        <p className="nav-label">WORKSPACE</p>
        <nav aria-label="Laboratórios">
          <Link className="nav-item" href="/video">
            <Video size={18} />
            Video Lab<span>01</span>
          </Link>
          <Link className="nav-item selected" href="/live" aria-current="page">
            <Radio size={18} />
            Live Lab<span>02</span>
          </Link>
          <a className="nav-item" href="/benchmark">
            <FlaskConical size={18} />
            Benchmark<span>03</span>
          </a>
        </nav>
        <div className="sidebar-bottom">
          <ShieldCheck size={21} />
          <strong>Processamento no navegador.</strong>
          <p>
            Frames não são enviados. Stop libera câmera, worker e séries da
            sessão.
          </p>
          <span className="mono">LIVE ENGINE · V1</span>
        </div>
      </aside>
      <div className="lab-main">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace / <strong>Live Lab</strong>
          </div>
          <div className="connection">
            <ShieldCheck size={14} />
            SOMENTE NESTA ABA
          </div>
        </header>
        <main id="workspace">
          <div className="page-heading">
            <div>
              <p className="eyebrow">02 / ANÁLISE EM JANELA MÓVEL</p>
              <h1>
                Live Lab<span>.</span>
              </h1>
              <p>Observe a captura. Preserve as incertezas.</p>
            </div>
            <span className="experimental">
              <FlaskConical size={15} />
              USO EXPERIMENTAL
            </span>
          </div>
          {error && (
            <div role="alert" className="alert">
              <Info size={18} />
              <span>{error}</span>
            </div>
          )}
          <div className="workspace-grid">
            <section className="session-panel card">
              <div className="card-heading">
                <h2>Sessão ao vivo</h2>
                <span className="mono">CONFIG / 02</span>
              </div>
              <div className="field">
                <label htmlFor="camera">Câmera</label>
                <select
                  id="camera"
                  value={device}
                  onChange={(e) => {
                    if (active) stop();
                    setDevice(e.target.value);
                  }}
                >
                  <option value="">Padrão do dispositivo</option>
                  {devices.map((d, i) => (
                    <option key={d.deviceId || i} value={d.deviceId}>
                      {d.label || `Câmera ${i + 1}`}
                    </option>
                  ))}
                </select>
                <small>
                  Outras câmeras aparecem após a permissão. Trocar desliga a
                  sessão; inicie novamente.
                </small>
              </div>
              <div className="field">
                <label htmlFor="live-method">Método rPPG</label>
                <select
                  id="live-method"
                  value={method}
                  disabled={active}
                  onChange={(e) => setMethod(e.target.value as Method)}
                >
                  {["GREEN", "POS", "CHROM"].map((m) => (
                    <option key={m}>{m}</option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="live-roi">Região de interesse</label>
                <select
                  id="live-roi"
                  value={roi}
                  disabled={active}
                  onChange={(e) => setRoi(e.target.value as Roi)}
                >
                  {Object.entries(roiLabels).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={mirror}
                  onChange={(e) => setMirror(e.target.checked)}
                />
                Espelhar apenas o preview
              </label>
              <div className="consent">
                <ShieldCheck size={17} />
                <p>
                  A câmera só inicia com sua ação. Imagens são processadas nesta
                  aba e não são gravadas nem enviadas. Assets do detector são
                  lidos do servidor local.
                </p>
              </div>
              <button
                className="button primary"
                disabled={active}
                onClick={start}
              >
                <Radio size={17} />
                Iniciar câmera
              </button>
              <button
                className="button secondary"
                disabled={!active}
                onClick={stop}
              >
                <Square size={14} />
                Stop · desligar e descartar
              </button>
              <button
                className="button secondary"
                disabled={!active || !report}
                onClick={download}
              >
                <Download size={14} />
                Exportar séries JSON
              </button>
              <p className="preview-note">
                Exporte antes de parar. Stop, perda de foco/visibilidade, troca
                de câmera e saída da página descartam as séries em memória.
              </p>
            </section>
            <section className="preview-panel card">
              <div className="card-heading">
                <h2>Captura & regiões</h2>
                <span className="pill" role="status">
                  {phases[phase]}
                </span>
              </div>
              <div
                className="preview live-preview"
                style={{ aspectRatio: aspect }}
              >
                <div className={"live-camera " + (mirror ? "mirrored" : "")}>
                  <video
                    ref={video}
                    onLoadedMetadata={(e) =>
                      setAspect(
                        e.currentTarget.videoWidth /
                          e.currentTarget.videoHeight || 4 / 3,
                      )
                    }
                    muted
                    playsInline
                    autoPlay
                    aria-label="Preview da webcam"
                  />
                  {report && (
                    <svg
                      className="roi-overlay"
                      viewBox="0 0 1 1"
                      preserveAspectRatio="none"
                      role="img"
                      aria-label="Regiões detectadas na webcam"
                    >
                      {polygons.map(([name, p]) => (
                        <polygon
                          key={name}
                          points={p!.map((pair) => pair.join(",")).join(" ")}
                          fill="rgba(177,245,114,.18)"
                          stroke="#bcf775"
                          strokeWidth=".003"
                        />
                      ))}
                    </svg>
                  )}
                </div>
                {!active && (
                  <div className="preview-empty">
                    <Radio size={36} />
                    <strong>Sua câmera está desligada.</strong>
                    <p>Controle explícito, do início ao descarte.</p>
                  </div>
                )}
              </div>
              <div className="preview-footer">
                <span>{active ? "CAPTURA LOCAL" : "SEM CAPTURA"}</span>
                <span className="mono">
                  {report?.timestamp_s.toFixed(1) ?? "0.0"} s
                </span>
              </div>
              <div className="status-strip" aria-live="polite">
                <span>
                  {reasons.length
                    ? reasons.map(explain).join(" · ")
                    : active
                      ? "Aguardando janela íntegra de 20 s"
                      : "Pronto para iniciar"}
                </span>
              </div>
              {active && (!analysis || phase === "warmup") && (
                <progress
                  aria-label="Aquecimento da janela"
                  max="20"
                  value={Math.min(20, report?.timestamp_s ?? 0)}
                />
              )}
              <p className="preview-note">
                Overlay indica geometria, não qualidade clínica. O preview é
                espelhado junto com os contornos; a extração RGB permanece sem
                espelho.
              </p>
            </section>
          </div>
          <section className="metrics-grid" aria-label="Métricas ao vivo">
            <div className="metric card">
              <span>ESTIMATIVA EXPERIMENTAL</span>
              <div>
                <strong>
                  {analysis?.bpm != null && !reasons.length
                    ? analysis.bpm.toFixed(1)
                    : "—"}
                </strong>
                <small>BPM</small>
              </div>
              <p>
                {analysis
                  ? `Janela ${analysis.start_s.toFixed(1)}–${analysis.end_s.toFixed(1)} s`
                  : "Aguardando dados válidos"}
              </p>
            </div>
            <div className="metric card">
              <span>CADÊNCIA ANALISADA</span>
              <div>
                <strong>{report ? report.analyzed_fps.toFixed(1) : "—"}</strong>
                <small>FPS</small>
              </div>
              <p>
                {report
                  ? `${report.count} frames analisados · ${skipped} callbacks sem análise`
                  : "Não equivale ao FPS do preview"}
              </p>
            </div>
            <div className="metric card">
              <span>PROCESSAMENTO POR FRAME</span>
              <div>
                <strong>
                  {report ? report.processing_ms.toFixed(0) : "—"}
                </strong>
                <small>ms</small>
              </div>
              <p>
                {analysis
                  ? `Idade na última captura: ${Math.max(0, report!.timestamp_s - analysis.end_s).toFixed(1)} s`
                  : "Detector + RGB + DSP quando agendado"}
              </p>
            </div>
          </section>
          <section className="results card">
            <div className="card-heading">
              <div>
                <p className="eyebrow">JANELA PASSADA / LIVE-V1</p>
                <h2>Sinal, espectro e parâmetros</h2>
              </div>
              <span className="mono">
                {method} / {roiLabels[roi]}
              </span>
            </div>
            <p className="preview-note">
              Janela 20 s · atualização 1 s · grade reamostrada 30 Hz · banda
              0,7–3 Hz · Butterworth ordem 4 em janela passada · corte de bordas{" "}
              {method === "GREEN" ? "1,0" : "1,6"} s. A estimativa resume o
              passado; não mede o instante atual. Limiares heurísticos, sem
              calibração clínica.
            </p>
            <LiveCharts analysis={analysis} />
          </section>
          <footer className="lab-footer">
            <span>
              <ShieldCheck size={14} />
              Estimativa experimental; não é dispositivo médico.
            </span>
            <span>Worker · MediaPipe · processamento local</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
