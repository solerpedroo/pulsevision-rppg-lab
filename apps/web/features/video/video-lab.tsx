"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  UploadCloud,
  ShieldCheck,
  Video,
  FlaskConical,
  Radio,
  Settings2,
  Download,
  Trash2,
  Square,
  ChevronRight,
  Info,
} from "lucide-react";
import { SignalCharts } from "./signal-charts";
import { VideoPreview } from "./video-preview";
import {
  allEstimates,
  removeJob,
  allSignal,
  allRegions,
  apiBase,
  call,
  explain,
  mime,
  roiLabels,
  statuses,
  validateFile,
  type Job,
  type Method,
  type Page,
  type RppgPoint,
  type SpectrumPoint,
  type RgbPoint,
  type Policy,
  type Region,
  type Roi,
} from "./api";

export function VideoLab() {
  const [endpoint, setEndpoint] = useState("http://127.0.0.1:8000"),
    [key, setKey] = useState(""),
    [draftKey, setDraftKey] = useState(""),
    [revision, setRevision] = useState(0),
    [base, setBase] = useState("http://127.0.0.1:8000/api/v1");
  const [policy, setPolicy] = useState<Policy | null>(null),
    [connection, setConnection] = useState("Conectando"),
    [file, setFile] = useState<File | null>(null),
    [url, setUrl] = useState(""),
    [duration, setDuration] = useState(0),
    [aspect, setAspect] = useState(16 / 9),
    [consent, setConsent] = useState(false);
  const [method, setMethod] = useState<Method>("GREEN"),
    [roi, setRoi] = useState<Roi>("combined"),
    [job, setJob] = useState<Job | null>(null),
    [page, setPage] = useState<Page | null>(null),
    [regions, setRegions] = useState<Region[]>([]),
    [windowIndex, setWindowIndex] = useState(0),
    [time, setTime] = useState(0),
    [rppg, setRppg] = useState<RppgPoint[]>([]),
    [spectrum, setSpectrum] = useState<SpectrumPoint[]>([]),
    [rgb, setRgb] = useState<RgbPoint[]>([]);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [loadingData, setLoadingData] = useState(false);
  const video = useRef<HTMLVideoElement>(null),
    input = useRef<HTMLInputElement>(null),
    generation = useRef(0),
    action = useRef<AbortController | null>(null);
  const jobId = job?.id,
    jobStatus = job?.status;
  const active = job?.status === "queued" || job?.status === "processing";
  const clearData = useCallback(() => {
    setPage(null);
    setRegions([]);
    setRppg([]);
    setSpectrum([]);
    setRgb([]);
    setWindowIndex(0);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    call<Policy>(base, key, "/policy", { signal: controller.signal })
      .then((p) => {
        setPolicy(p);
        setConnection("API conectada");
      })
      .catch((e) => {
        if (!controller.signal.aborted) {
          setConnection("API indisponível");
          setError(
            e instanceof Error ? e.message : "Não foi possível conectar.",
          );
        }
      });
    return () => controller.abort();
  }, [base, key, revision]);
  useEffect(
    () => () => {
      if (url) URL.revokeObjectURL(url);
    },
    [url],
  );
  useEffect(
    () => () => {
      generation.current++;
      action.current?.abort();
    },
    [],
  );
  useEffect(() => {
    if (!jobId || !["queued", "processing"].includes(jobStatus ?? "")) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const id = jobId;
    async function poll() {
      try {
        const result = await call<Job>(base, key, `/videos/jobs/${id}`, {
          signal: controller.signal,
        });
        if (!controller.signal.aborted) {
          setJob(result);
          setError("");
          if (["queued", "processing"].includes(result.status))
            timer = setTimeout(poll, 1200);
        }
      } catch (e) {
        if (!controller.signal.aborted) {
          setError(
            "Acompanhamento interrompido. Tentando novamente. " +
              (e instanceof Error ? e.message : ""),
          );
          timer = setTimeout(poll, 3000);
        }
      }
    }
    timer = setTimeout(poll, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [jobId, jobStatus, base, key]); // Status changes restart the single polling loop.
  useEffect(() => {
    if (job?.status !== "completed") return;
    const controller = new AbortController();
    Promise.all([
      allEstimates(base, key, job.id, controller.signal),
      allRegions(base, key, job.id, controller.signal),
    ])
      .then(([results, rois]) => {
        if (!controller.signal.aborted) {
          setPage(results);
          setRegions(rois);
        }
      })
      .catch((e) => {
        if (!controller.signal.aborted)
          setError(e instanceof Error ? e.message : "Falha ao ler resultados.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingData(false);
      });
    return () => controller.abort();
  }, [job, base, key]);
  useEffect(() => {
    if (job?.status !== "completed" || !page) return;
    const controller = new AbortController();
    const id = job.id;
    Promise.all([
      allSignal(base, key, id, "rppg", windowIndex, controller.signal),
      allSignal(base, key, id, "spectrum", windowIndex, controller.signal),
      allSignal(base, key, id, "rgb", 0, controller.signal),
    ])
      .then(([a, b, c]) => {
        if (!controller.signal.aborted) {
          setRppg(a);
          setSpectrum(b);
          setRgb(c);
        }
      })
      .catch((e) => {
        if (!controller.signal.aborted)
          setError(e instanceof Error ? e.message : "Falha nos sinais.");
      });
    return () => controller.abort();
  }, [job, windowIndex, page, base, key]);
  useEffect(() => {
    if (!job || job.status !== "completed") return;
    const timer = setTimeout(
      () => {
        setJob({ ...job, status: "expired" });
        setLoadingData(false);
        clearData();
      },
      Math.max(0, job.expires_at * 1000 - Date.now()),
    );
    return () => clearTimeout(timer);
  }, [job, clearData]);
  function select(next: File | undefined) {
    if (!next || !policy || job || busy) return;
    const failure = validateFile(next, policy);
    if (failure) {
      setError(failure);
      return;
    }
    setError("");
    clearData();
    setConsent(false);
    setDuration(0);
    setTime(0);
    setFile(next);
    setUrl(URL.createObjectURL(next));
  }
  function metadata() {
    const element = video.current;
    if (!element || !policy) return;
    const d = element.duration;
    if (!Number.isFinite(d) || d <= 0) {
      setError("Duração inválida ou decoder indisponível no navegador.");
      return;
    }
    if (
      d > policy.max_duration_s ||
      element.videoWidth * element.videoHeight > policy.max_pixels
    ) {
      setError("O vídeo excede os limites de duração ou resolução.");
      setDuration(0);
      return;
    }
    setDuration(d);
    setAspect(element.videoWidth / element.videoHeight);
  }
  async function analyze() {
    if (!file || !policy || !consent || duration <= 0 || active || busy) return;
    const token = ++generation.current;
    const controller = new AbortController();
    action.current = controller;
    setBusy(true);
    setError("");
    setLoadingData(true);
    clearData();
    try {
      if (job) {
        await removeJob(base, key, job.id, controller.signal);
        setJob(null);
      }
      const next = await call<Job>(
        base,
        key,
        `/videos/jobs?method=${method}&roi=${roi}`,
        {
          method: "POST",
          body: file,
          headers: { "Content-Type": mime(file) },
          signal: controller.signal,
        },
      );
      if (token === generation.current) setJob(next);
    } catch (e) {
      if (!controller.signal.aborted)
        setError(e instanceof Error ? e.message : "Upload interrompido.");
    } finally {
      if (token === generation.current) setBusy(false);
    }
  }
  async function remove() {
    if (!job || busy) return;
    setBusy(true);
    setError("");
    try {
      await removeJob(base, key, job.id);
      setFile(null);
      setUrl("");
      setDuration(0);
      setTime(0);
      setConsent(false);
      if (input.current) input.current.value = "";
      setJob(null);
      setLoadingData(false);
      clearData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível excluir.");
    } finally {
      setBusy(false);
    }
  }
  async function cancel() {
    if (!job || busy) return;
    setBusy(true);
    try {
      setJob(
        await call<Job>(base, key, `/videos/jobs/${job.id}/cancel`, {
          method: "POST",
        }),
      );
      clearData();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao cancelar.");
    } finally {
      setBusy(false);
    }
  }
  async function download(format: string) {
    if (!job || busy) return;
    setBusy(true);
    try {
      const response = await fetch(
        base + `/videos/jobs/${job.id}/exports?format=${format}`,
        { headers: key ? { "X-API-Key": key } : {}, cache: "no-store" },
      );
      if (!response.ok) throw new Error("Exportação indisponível ou expirada.");
      const object = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = object;
      link.download = `pulsevision-${job.method.toLowerCase()}.${format}`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(object), 1000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Falha ao exportar.");
    } finally {
      setBusy(false);
    }
  }
  function syncTime(seconds: number) {
    setTime(seconds);
    const current = page?.items[windowIndex]?.window;
    if (current && seconds >= current.start_s && seconds < current.end_s)
      return;
    let index = -1;
    for (let i = (page?.items.length ?? 0) - 1; i >= 0; i--) {
      if (page!.items[i].window.start_s <= seconds + 1e-6) {
        index = i;
        break;
      }
    }
    if (index !== undefined && index >= 0 && index !== windowIndex) {
      setRppg([]);
      setSpectrum([]);
      setWindowIndex(index);
    }
  }
  function seek(seconds: number) {
    if (video.current) video.current.currentTime = seconds;
    syncTime(seconds);
  }
  const selected = page?.items[windowIndex];
  const settingsChanged = !!job && (job.method !== method || job.roi !== roi);
  return (
    <div className="lab-shell">
      <a href="#workspace" className="skip">
        Ir ao laboratório
      </a>
      <aside className="sidebar">
        <a href="/video" className="brand">
          <span className="brand-mark">
            <Activity size={24} />
          </span>
          <span>
            PulseVision<small>rPPG RESEARCH LAB</small>
          </span>
        </a>
        <p className="nav-label">WORKSPACE</p>
        <nav aria-label="Laboratórios">
          <a className="nav-item selected" href="/video">
            <Video size={18} />
            Video Lab<span>01</span>
          </a>
          <button className="nav-item" disabled>
            <Radio size={18} />
            Live Lab<small>Onda 9</small>
          </button>
          <button className="nav-item" disabled>
            <FlaskConical size={18} />
            Benchmark<small>Em breve</small>
          </button>
        </nav>
        <div className="sidebar-bottom">
          <ShieldCheck size={21} />
          <strong>Local por princípio.</strong>
          <p>
            Arquivos escolhidos por você. Resultados experimentais, com
            rastreabilidade.
          </p>
          <span className="mono">CLASSICAL ENGINE · V1</span>
        </div>
      </aside>
      <div className="lab-main">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={14} />
            <strong>Video Lab</strong>
          </div>
          <div className="connection">
            <i className={policy ? "online" : ""} />
            {connection}
          </div>
        </header>
        <main id="workspace">
          <div className="page-heading">
            <div>
              <p className="eyebrow">01 / ANÁLISE OFFLINE</p>
              <h1>
                Video Lab<span>.</span>
              </h1>
              <p>Explore o sinal. Entenda quando estimar.</p>
            </div>
            <span className="experimental">
              <FlaskConical size={15} />
              USO EXPERIMENTAL
            </span>
          </div>
          <details className="settings">
            <summary>
              <Settings2 size={15} />
              Conexão com o laboratório
            </summary>
            <div>
              <label>
                Endereço da API
                <input
                  value={endpoint}
                  onChange={(e) => setEndpoint(e.target.value)}
                  disabled={!!job || busy}
                />
              </label>
              <label>
                Chave da API (opcional, só nesta aba)
                <input
                  type="password"
                  value={draftKey}
                  onChange={(e) => setDraftKey(e.target.value)}
                  disabled={!!job || busy}
                  autoComplete="off"
                />
              </label>
              <button
                className="button secondary"
                disabled={!!job || busy}
                onClick={() => {
                  try {
                    setBase(apiBase(endpoint));
                    setKey(draftKey);
                    setPolicy(null);
                    setConnection("Conectando");
                    setRevision((value) => value + 1);
                    setError("");
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                Conectar
              </button>
            </div>
            <p>
              Destino atual: <strong>{base.replace("/api/v1", "")}</strong>.
              Nenhum envio acontece ao selecionar o arquivo.
            </p>
          </details>
          {error && (
            <div role="alert" className="alert">
              <Info size={18} />
              <span>{error}</span>
              <button aria-label="Fechar mensagem" onClick={() => setError("")}>
                ×
              </button>
            </div>
          )}
          <div className="workspace-grid">
            <section className="session-panel card">
              <div className="card-heading">
                <h2>Sessão de análise</h2>
                <span className="mono">CONFIG / 01</span>
              </div>
              <label
                className={"dropzone " + (file ? "has-file" : "")}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  select(e.dataTransfer.files[0]);
                }}
              >
                <input
                  ref={input}
                  type="file"
                  accept=".mp4,.mov,.webm,.avi"
                  aria-label="Selecionar vídeo"
                  disabled={!policy || !!job || busy}
                  onChange={(e) => select(e.target.files?.[0])}
                />
                <UploadCloud size={30} />
                <strong>{file ? file.name : "Escolha um vídeo"}</strong>
                <span>
                  {file
                    ? `${(file.size / 1048576).toFixed(1)} MB · ${duration ? duration.toFixed(1) + " s" : "Lendo metadados"}`
                    : "Arraste aqui ou clique para selecionar"}
                </span>
                <small>
                  MP4 · MOV · WebM · AVI
                  {policy &&
                    ` / até ${Math.round(policy.max_upload_bytes / 1048576)} MB`}
                </small>
              </label>
              {file && !job && (
                <button
                  className="text-button"
                  onClick={() => {
                    setFile(null);
                    setUrl("");
                    setDuration(0);
                    setConsent(false);
                    setError("");
                    if (input.current) input.current.value = "";
                  }}
                >
                  Trocar arquivo
                </button>
              )}
              <div className="field">
                <label htmlFor="method">Método rPPG</label>
                <select
                  id="method"
                  value={method}
                  disabled={active || busy}
                  onChange={(e) => setMethod(e.target.value as Method)}
                >
                  {["GREEN", "CHROM", "POS"].map((x) => (
                    <option key={x}>{x}</option>
                  ))}
                </select>
                <small>
                  {method === "GREEN"
                    ? "Baseline do canal verde."
                    : method === "CHROM"
                      ? "Projeção de crominância em janelas."
                      : "Projeção ortogonal ao tom de pele."}
                </small>
              </div>
              <div className="field">
                <label htmlFor="roi">Região de interesse</label>
                <select
                  id="roi"
                  value={roi}
                  disabled={active || busy}
                  onChange={(e) => setRoi(e.target.value as Roi)}
                >
                  {Object.entries(roiLabels).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="consent">
                <ShieldCheck size={17} />
                <p>
                  O arquivo será enviado para{" "}
                  <strong>{base.replace("/api/v1", "")}</strong>. Original
                  descartado após o processamento; derivados por até{" "}
                  <strong>
                    {policy ? Math.round(policy.retention_s / 3600) : "—"} h
                  </strong>
                  .
                </p>
              </div>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                  disabled={active || busy}
                />
                Tenho autorização para usar este vídeo e concordo com o envio ao
                backend indicado.
              </label>
              <button
                className="button primary"
                disabled={
                  !file ||
                  !consent ||
                  !policy ||
                  duration <= 0 ||
                  active ||
                  busy
                }
                onClick={analyze}
              >
                {busy
                  ? "Aguarde…"
                  : settingsChanged
                    ? "Reanalisar com nova configuração"
                    : job
                      ? "Executar nova análise"
                      : "Iniciar análise"}
                <ArrowUpRight size={17} />
              </button>
              {job && (
                <div className="job-actions">
                  {active && (
                    <button
                      className="button secondary"
                      onClick={cancel}
                      disabled={busy}
                    >
                      <Square size={13} />
                      Cancelar
                    </button>
                  )}
                  <button
                    className="button danger"
                    onClick={remove}
                    disabled={busy}
                  >
                    <Trash2 size={14} />
                    Excluir sessão
                  </button>
                </div>
              )}
            </section>
            <section className="preview-panel card">
              <div className="card-heading">
                <h2>Vídeo & regiões</h2>
                <span className="pill">
                  {job
                    ? statuses[job.status]
                    : file
                      ? "Vídeo selecionado"
                      : "Aguardando arquivo"}
                </span>
              </div>
              <VideoPreview
                video={video}
                url={url}
                aspect={aspect}
                regions={regions}
                roi={job?.roi}
                onMetadata={metadata}
                onTime={syncTime}
                onError={() => {
                  setDuration(0);
                  setError(
                    "O navegador não conseguiu abrir este codec. Tente MP4 ou WebM compatível.",
                  );
                }}
              />
              <div className="preview-footer">
                <span>
                  <i />
                  {file ? "ARQUIVO LOCAL" : "SEM VÍDEO"}
                </span>
                <span className="mono">
                  {time.toFixed(1)} s
                  {duration ? ` / ${duration.toFixed(1)} s` : ""}
                </span>
              </div>
              <div className="status-strip" aria-live="polite">
                <span>
                  {job
                    ? statuses[job.status]
                    : busy
                      ? "Enviando arquivo…"
                      : "Pronto para uma nova sessão"}
                </span>
                <strong>
                  {active
                    ? `${Math.round((job?.progress ?? 0) * 100)}%`
                    : job?.status === "failed"
                      ? explain(job.error ?? "processing_failed")
                      : job?.status === "completed"
                        ? "Análise disponível"
                        : ""}
                </strong>
              </div>
              {active && (
                <progress
                  aria-label="Progresso do processamento"
                  max="1"
                  value={job?.progress}
                />
              )}
              <p className="preview-note">
                Contornos representam regiões geométricas detectadas no frame,
                não diagnóstico ou identificação. Sem detecção válida, o overlay
                fica vazio.
              </p>
            </section>
          </div>
          <section
            className="metrics-grid"
            aria-label="Resumo da janela selecionada"
          >
            <div className="metric card">
              <span>ESTIMATIVA DA JANELA</span>
              <div>
                <strong>
                  {selected?.bpm != null ? selected.bpm.toFixed(1) : "—"}
                </strong>
                <small>BPM</small>
              </div>
              <p>
                {selected?.bpm != null
                  ? "Estimativa experimental"
                  : selected
                    ? "Sinal insuficiente para estimar"
                    : "Disponível após a análise"}
              </p>
            </div>
            <div className="metric card">
              <span>COBERTURA VÁLIDA</span>
              <div>
                <strong>
                  {page?.summary.coverage != null
                    ? `${(page.summary.coverage * 100).toFixed(0)}%`
                    : "—"}
                </strong>
              </div>
              <p>
                {page
                  ? `${page.summary.accepted_windows} de ${page.summary.eligible_windows} janelas aceitas`
                  : "Disponível após a análise"}
              </p>
            </div>
            <div className="metric card">
              <span>MÉTODO / REGIÃO DO RESULTADO</span>
              <div>
                <strong className="method-value">
                  {job?.method ?? method}
                </strong>
              </div>
              <p>
                {roiLabels[job?.roi ?? roi]}
                {settingsChanged ? " · configuração alterada, reanalise" : ""}
              </p>
            </div>
          </section>
          <section className="results card">
            <div className="card-heading">
              <div>
                <p className="eyebrow">INSPEÇÃO DO SINAL</p>
                <h2>Uma janela de cada vez</h2>
              </div>
              <div className="export-actions">
                {["csv", "json", "png"].map((format) => (
                  <button
                    key={format}
                    className="button secondary"
                    disabled={job?.status !== "completed" || !page || busy}
                    onClick={() => download(format)}
                  >
                    <Download size={14} />
                    {format.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
            {loadingData && job?.status === "completed" ? (
              <p role="status" className="empty-state">
                Carregando resultados e máscaras…
              </p>
            ) : page ? (
              <>
                <label className="window-label">
                  Janela de análise
                  <select
                    aria-label="Janela de análise"
                    value={windowIndex}
                    onChange={(e) => {
                      const index = Number(e.target.value);
                      setRppg([]);
                      setSpectrum([]);
                      setWindowIndex(index);
                      if (video.current)
                        video.current.currentTime =
                          page.items[index].window.start_s;
                    }}
                  >
                    {page.items.map((item, index) => (
                      <option key={index} value={index}>
                        {index + 1} · {item.window.start_s.toFixed(1)}–
                        {item.window.end_s.toFixed(1)} s ·{" "}
                        {item.bpm === null
                          ? "sem estimativa"
                          : item.bpm.toFixed(1) + " BPM"}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="timeline" aria-label="Timeline de estimativas">
                  {page.items.map((item, index) => (
                    <button
                      key={index}
                      className={
                        (item.bpm === null ? "rejected" : "accepted") +
                        (index === windowIndex ? " current" : "")
                      }
                      aria-label={`Ir para janela ${index + 1}, ${item.window.start_s.toFixed(1)} segundos`}
                      aria-pressed={index === windowIndex}
                      title={
                        item.reasons.map(explain).join(", ") ||
                        "Estimativa aceita"
                      }
                      onClick={() => {
                        setRppg([]);
                        setSpectrum([]);
                        setWindowIndex(index);
                        if (video.current)
                          video.current.currentTime = item.window.start_s;
                      }}
                    />
                  ))}
                </div>
                <div className="quality-note" role="status">
                  <Info size={16} />
                  <span>
                    {selected?.reasons.length
                      ? selected.reasons.map(explain).join(" · ")
                      : "Gates instrumentais atendidos. Isso não garante precisão clínica."}{" "}
                    · {selected?.window.start_s.toFixed(1)}–
                    {selected?.window.end_s.toFixed(1)} s
                  </span>
                </div>
                <label className="scrubber">
                  Posição no vídeo · {time.toFixed(1)} s
                  <input
                    type="range"
                    min="0"
                    max={duration || 1}
                    step=".01"
                    value={Math.min(time, duration || 1)}
                    disabled={!file}
                    onChange={(e) => seek(Number(e.target.value))}
                  />
                </label>
                <SignalCharts
                  rppg={rppg}
                  spectrum={spectrum}
                  rgb={rgb}
                  estimates={page.items}
                />
              </>
            ) : (
              <div className="empty-state">
                <Activity size={30} />
                <h3>Os dados contam a próxima parte.</h3>
                <p>
                  Depois de processar um vídeo, inspecione os sinais, o espectro
                  e os motivos de abstenção aqui.
                </p>
              </div>
            )}
          </section>
          <footer className="lab-footer">
            <span>
              <ShieldCheck size={14} />
              Estimativa experimental; não é dispositivo médico.
            </span>
            <span>CPU · GREEN / CHROM / POS</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
