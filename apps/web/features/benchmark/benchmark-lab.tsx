"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  Activity,
  Video,
  Radio,
  FlaskConical,
  ShieldCheck,
  UploadCloud,
  Download,
  Trash2,
  Info,
} from "lucide-react";
import { roiLabels, explain } from "../video/api";
import { MetricBars } from "./metric-bars";
import {
  EMPTY_FILTERS,
  MAX_BYTES,
  parseReview,
  groups,
  exportCsv,
  type BenchmarkReview,
  type Filters,
  type Dimension,
} from "./data";
export function BenchmarkLab() {
  const [review, setReview] = useState<BenchmarkReview | null>(null),
    [filters, setFilters] = useState<Filters>(EMPTY_FILTERS),
    [dimension, setDimension] = useState<Dimension>("method"),
    [metric, setMetric] = useState<"mae" | "rmse" | "medae" | "bias">("mae"),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [page, setPage] = useState(0),
    [filename, setFilename] = useState("");
  const input = useRef<HTMLInputElement>(null),
    generation = useRef(0);
  useEffect(
    () => () => {
      generation.current++;
    },
    [],
  );
  const rows = useMemo(
    () => (review ? groups(review, filters, dimension) : []),
    [review, filters, dimension],
  );
  const options = useMemo(
    () => ({
      runs: review?.runs.map((r) => r.run_id) ?? [],
      rois: [...new Set(review?.runs.map((r) => r.roi) ?? [])],
      windows: [...new Set(review?.runs.map((r) => r.window_s) ?? [])].sort(
        (a, b) => a - b,
      ),
      conditions: [
        ...new Set(
          review?.runs.flatMap((r) => r.sessions.map((s) => s.condition)) ?? [],
        ),
      ].sort(),
      participants: [
        ...new Set(
          review?.runs.flatMap((r) =>
            r.sessions.map((s) => s.participant_id),
          ) ?? [],
        ),
      ].sort(),
    }),
    [review],
  );
  const current = rows.slice(page * 18, (page + 1) * 18),
    selectedRuns =
      review?.runs.filter(
        (r) =>
          (!filters.run || r.run_id === filters.run) &&
          (!filters.roi || r.roi === filters.roi) &&
          (!filters.window || String(r.window_s) === filters.window),
      ) ?? [];
  async function load(file: File | undefined) {
    if (!file) return;
    const token = ++generation.current;
    setError("");
    if (
      !file.name.toLowerCase().endsWith(".json") ||
      file.size === 0 ||
      file.size > MAX_BYTES
    ) {
      setError("Selecione um JSON não vazio de até 20 MiB.");
      setBusy(false);
      return;
    }
    setBusy(true);
    try {
      const parsed = parseReview(await file.text());
      if (token !== generation.current) return;
      setReview(parsed);
      setFilters(EMPTY_FILTERS);
      setPage(0);
      setFilename(file.name);
    } catch (e) {
      if (token === generation.current)
        setError(
          e instanceof Error ? e.message : "Não foi possível ler o relatório.",
        );
    } finally {
      if (token === generation.current) setBusy(false);
    }
  }
  function clear() {
    generation.current++;
    setReview(null);
    setBusy(false);
    setError("");
    setFilters(EMPTY_FILTERS);
    setPage(0);
    setFilename("");
    if (input.current) input.current.value = "";
  }
  function filter(field: keyof Filters, value: string) {
    setFilters((prev) => ({ ...prev, [field]: value }));
    setPage(0);
  }
  function download(kind: "csv" | "json") {
    if (!review) return;
    const contents =
        kind === "csv" ? exportCsv(rows) : JSON.stringify(review, null, 2),
      url = URL.createObjectURL(
        new Blob([contents], {
          type: kind === "csv" ? "text/csv;charset=utf-8" : "application/json",
        }),
      ),
      a = document.createElement("a");
    a.href = url;
    a.download =
      kind === "csv"
        ? "pulsevision-benchmark-recorte.csv"
        : "pulsevision-benchmark-review.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const artificial = review?.runs[0].result_kind === "synthetic_demonstration";
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
          <Link className="nav-item" href="/live">
            <Radio size={18} />
            Live Lab<span>02</span>
          </Link>
          <Link
            className="nav-item selected"
            href="/benchmark"
            aria-current="page"
          >
            <FlaskConical size={18} />
            Benchmark<span>03</span>
          </Link>
        </nav>
        <div className="sidebar-bottom">
          <ShieldCheck size={21} />
          <strong>Resultados com origem.</strong>
          <p>
            Inspeção de arquivos locais. Sem upload, ajuste de protocolo ou
            execução de experimento nesta tela.
          </p>
          <span className="mono">BENCHMARK REVIEW · V1</span>
        </div>
      </aside>
      <div className="lab-main">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace / <strong>Benchmark Lab</strong>
          </div>
          <div className="connection">
            <ShieldCheck size={14} />
            ARQUIVO LOCAL
          </div>
        </header>
        <main id="workspace">
          <div className="page-heading">
            <div>
              <p className="eyebrow">03 / EXPERIMENTOS RASTREÁVEIS</p>
              <h1>
                Benchmark Lab<span>.</span>
              </h1>
              <p>Compare resultados. Preserve o contexto.</p>
            </div>
            <span className="experimental">
              <FlaskConical size={15} />
              USO EXPERIMENTAL
            </span>
          </div>
          <section className="card bench-import">
            <div>
              <h2>Abra uma revisão offline</h2>
              <p>
                JSON benchmark-review-v1 · até 20 MiB. O arquivo permanece nesta
                aba.
              </p>
            </div>
            <label className="button secondary bench-file">
              <UploadCloud size={16} />
              {busy ? "Lendo…" : "Selecionar relatório"}
              <input
                ref={input}
                type="file"
                accept=".json,application/json"
                aria-label="Selecionar relatório de benchmark"
                onChange={(e) => void load(e.target.files?.[0])}
              />
            </label>
            {review && (
              <button className="button danger" onClick={clear}>
                <Trash2 size={14} />
                Descartar revisão
              </button>
            )}
          </section>
          {error && (
            <div role="alert" className="alert">
              <Info size={18} />
              {error}
            </div>
          )}
          {!review ? (
            <section className="card empty-state bench-empty">
              <FlaskConical size={36} />
              <h2>Nenhum resultado importado.</h2>
              <p>
                Gere uma revisão a partir dos relatórios do runner. Uma
                demonstração artificial está disponível pelo CLI; não é
                avaliação em pessoas.
              </p>
              <code>
                uv run python -m benchmarks.study demo --output
                artifacts/study-demo
              </code>
              <p>
                Abra results/review/benchmark-review-v1.json da pasta gerada.
                Não há métricas preenchidas automaticamente.
              </p>
            </section>
          ) : (
            <>
              <div
                className={"bench-notice " + (artificial ? "artificial" : "")}
                role="status"
              >
                <FlaskConical size={20} />
                <div>
                  <strong>
                    {artificial
                      ? "DEMONSTRAÇÃO ARTIFICIAL — sem precisão fisiológica"
                      : "AVALIAÇÃO DE DATASET DECLARADA — sem validação clínica"}
                  </strong>
                  <p>
                    {filename} · {review.title}. A aba valida estrutura e
                    consistência; não verifica acesso, autenticidade dos dados
                    ou hashes contra os arquivos originais.
                  </p>
                </div>
              </div>
              <section
                className="card bench-filters"
                aria-label="Filtros de benchmark"
              >
                <label>
                  Execução
                  <select
                    aria-label="Execução"
                    value={filters.run}
                    onChange={(e) => filter("run", e.target.value)}
                  >
                    <option value="">Todas as execuções</option>
                    {options.runs.map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Método
                  <select
                    aria-label="Método"
                    value={filters.method}
                    onChange={(e) => filter("method", e.target.value)}
                  >
                    <option value="">Todos os métodos</option>
                    {["GREEN", "CHROM", "POS"].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </label>
                <label>
                  ROI
                  <select
                    aria-label="ROI"
                    value={filters.roi}
                    onChange={(e) => filter("roi", e.target.value)}
                  >
                    <option value="">Todas as regiões</option>
                    {options.rois.map((v) => (
                      <option value={v} key={v}>
                        {roiLabels[v]}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Cenário
                  <select
                    aria-label="Cenário"
                    value={filters.condition}
                    onChange={(e) => filter("condition", e.target.value)}
                  >
                    <option value="">Todos os cenários</option>
                    {options.conditions.map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Participante
                  <select
                    aria-label="Participante"
                    value={filters.participant}
                    onChange={(e) => filter("participant", e.target.value)}
                  >
                    <option value="">Todos os participantes</option>
                    {options.participants.map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Janela
                  <select
                    aria-label="Janela"
                    value={filters.window}
                    onChange={(e) => filter("window", e.target.value)}
                  >
                    <option value="">Todas as janelas</option>
                    {options.windows.map((v) => (
                      <option value={v} key={v}>
                        {v} s
                      </option>
                    ))}
                  </select>
                </label>
              </section>
              <section className="results card">
                <div className="card-heading">
                  <div>
                    <p className="eyebrow">ERROS E ABSTENÇÃO JUNTOS</p>
                    <h2>Comparações no recorte</h2>
                  </div>
                  <div className="export-actions">
                    <button
                      className="button secondary"
                      onClick={() => download("csv")}
                      disabled={!rows.length}
                    >
                      <Download size={14} />
                      Resumo CSV
                    </button>
                    <button
                      className="button secondary"
                      onClick={() => download("json")}
                    >
                      <Download size={14} />
                      JSON completo
                    </button>
                  </div>
                </div>
                <p className="preview-note">
                  Erro macro = média com peso igual por participante com pares
                  aceitos. Não é média agrupada de todas as janelas. Cobertura
                  usa todas as janelas elegíveis. Não conclua superioridade sem
                  conferir coortes, suporte temporal e exclusões.
                </p>
                <div className="bench-controls">
                  <label>
                    Agrupar por
                    <select
                      aria-label="Agrupar por"
                      value={dimension}
                      onChange={(e) => {
                        setDimension(e.target.value as Dimension);
                        setPage(0);
                      }}
                    >
                      <option value="method">Método</option>
                      <option value="participant">Participante</option>
                      <option value="roi">ROI</option>
                      <option value="condition">Cenário</option>
                      <option value="window">Janela</option>
                    </select>
                  </label>
                  <label>
                    Métrica de erro
                    <select
                      aria-label="Métrica de erro"
                      value={metric}
                      onChange={(e) =>
                        setMetric(e.target.value as typeof metric)
                      }
                    >
                      <option value="mae">MAE</option>
                      <option value="rmse">RMSE</option>
                      <option value="medae">MedAE</option>
                      <option value="bias">Bias (estimado − referência)</option>
                    </select>
                  </label>
                  <button
                    className="text-button"
                    onClick={() => {
                      setFilters(EMPTY_FILTERS);
                      setPage(0);
                    }}
                  >
                    Limpar filtros
                  </button>
                </div>
                <div className="charts-grid">
                  <MetricBars
                    groups={current}
                    metric={metric}
                    title={`${metric.toUpperCase()} macro por grupo`}
                    unit="BPM"
                  />
                  <MetricBars
                    groups={current}
                    metric="coverage"
                    title="Cobertura por grupo"
                    unit="Fração de janelas elegíveis"
                  />
                </div>
                <div className="bench-pagination">
                  <span>
                    {rows.length
                      ? `${page * 18 + 1}–${Math.min((page + 1) * 18, rows.length)} de ${rows.length} grupos`
                      : "Nenhum grupo neste recorte"}
                  </span>
                  <button
                    className="button secondary"
                    disabled={page === 0}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Anterior
                  </button>
                  <button
                    className="button secondary"
                    disabled={(page + 1) * 18 >= rows.length}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Próxima
                  </button>
                </div>
                <div className="bench-table">
                  <table>
                    <caption>
                      Erros condicionais e cobertura do recorte ·{" "}
                      {artificial ? "dados artificiais" : "origem declarada"}
                    </caption>
                    <thead>
                      <tr>
                        {[
                          "Grupo",
                          "Participantes",
                          "Sem pares",
                          "MAE (BPM)",
                          "RMSE (BPM)",
                          "Bias (BPM)",
                          "Aceitas / elegíveis",
                          "Cobertura",
                          "Excluídas",
                          "Falhas de sessão",
                        ].map((v) => (
                          <th key={v} scope="col">
                            {v}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {current.map((g) => (
                        <tr key={g.label}>
                          <th scope="row">{g.label}</th>
                          <td>{g.participants}</td>
                          <td>{g.without_pairs}</td>
                          <td>{g.mae?.toFixed(3) ?? "—"}</td>
                          <td>{g.rmse?.toFixed(3) ?? "—"}</td>
                          <td>{g.bias?.toFixed(3) ?? "—"}</td>
                          <td>
                            {g.accepted} / {g.eligible}
                          </td>
                          <td>
                            {g.coverage === null
                              ? "—"
                              : `${(g.coverage * 100).toFixed(1)}%`}
                          </td>
                          <td>{g.excluded}</td>
                          <td>{g.failures}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <details className="bench-details">
                  <summary>Motivos de abstenção e exclusão</summary>
                  {current.map((g) => (
                    <div key={g.label}>
                      <strong>{g.label}</strong>
                      <p>
                        Abstenções:{" "}
                        {Object.entries(g.reasons)
                          .map(
                            ([reason, count]) => `${explain(reason)}: ${count}`,
                          )
                          .join(" · ") || "Nenhuma nas janelas elegíveis"}
                      </p>
                      <p>
                        Exclusões:{" "}
                        {Object.entries(g.exclusions)
                          .map(
                            ([reason, count]) => `${explain(reason)}: ${count}`,
                          )
                          .join(" · ") || "Nenhuma janela excluída"}
                      </p>
                    </div>
                  ))}
                </details>
              </section>
              <section className="card bench-provenance">
                <div className="card-heading">
                  <h2>Hipótese, origem e limites</h2>
                  <span className="mono">
                    {selectedRuns.length} execuções no recorte
                  </span>
                </div>
                <p>{review.hypothesis}</p>
                <h3>Pendências declaradas</h3>
                <ul>
                  {review.pending.map((text, i) => (
                    <li key={i}>{text}</li>
                  ))}
                </ul>
                <h3>Limitações</h3>
                <ul>
                  {review.limitations.map((text, i) => (
                    <li key={i}>{text}</li>
                  ))}
                </ul>
                {selectedRuns.map((run) => (
                  <details key={run.run_id} className="bench-details">
                    <summary>
                      {run.run_id} · {run.dataset} · {run.window_s} s ·{" "}
                      {roiLabels[run.roi]}
                    </summary>
                    <p>
                      Fonte: {run.source_report} · split {run.split} · protocolo{" "}
                      {run.protocol_version} · experimento {run.experiment}
                    </p>
                    <p className="mono">
                      Relatório SHA256: {run.report_sha256}
                    </p>
                    <p className="mono">
                      Manifesto SHA256: {run.manifest_sha256}
                    </p>
                    <p>
                      Seed: {run.seed}; bootstrap original:{" "}
                      {run.bootstrap_samples}. O recorte da UI não recalcula
                      intervalos de confiança.
                    </p>
                    <h3>Falhas de sessão da execução completa</h3>
                    <ul>
                      {run.failures.map((f, i) => (
                        <li key={i}>
                          {f.participant_id} / {f.session_id}: {f.reason}
                        </li>
                      ))}
                    </ul>
                    <h3>Limitações da execução</h3>
                    <ul>
                      {run.limitations.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                    <pre>
                      {JSON.stringify(
                        {
                          configuration: run.configuration,
                          provenance: run.provenance,
                        },
                        null,
                        2,
                      )}
                    </pre>
                  </details>
                ))}
              </section>
            </>
          )}
          <footer className="lab-footer">
            <span>
              <ShieldCheck size={14} />
              Estimativa experimental; não é dispositivo médico.
            </span>
            <span>Offline · sem upload ou ajuste de parâmetros</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
