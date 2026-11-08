import type { EstimateResult } from "../../../../packages/rppg_types/generated/EstimateResult";
export type Method = "GREEN" | "CHROM" | "POS";
export type Roi = "combined" | "forehead" | "left_cheek" | "right_cheek";
export interface Job {
  id: string;
  status:
    "queued" | "processing" | "completed" | "failed" | "cancelled" | "expired";
  method: Method;
  roi: Roi;
  progress: number;
  error: string | null;
  expires_at: number;
}
export interface Policy {
  max_upload_bytes: number;
  max_duration_s: number;
  max_pixels: number;
  max_fps: number;
  retention_s: number;
}
export interface Page {
  total: number;
  items: EstimateResult[];
  summary: {
    accepted_windows: number;
    eligible_windows: number;
    coverage: number | null;
  };
}
export interface Region {
  timestamp_s: number;
  regions: Record<string, number[][]>;
}
export interface RppgPoint {
  timestamp_s: number;
  value: number | null;
}
export interface SpectrumPoint {
  frequency_hz: number;
  power: number | null;
}
export interface RgbPoint {
  timestamp_s: number;
  r: number | null;
  g: number | null;
  b: number | null;
}
type SignalMap = { rppg: RppgPoint; spectrum: SpectrumPoint; rgb: RgbPoint };
export interface SignalPage<T> {
  total: number;
  points: T[];
}
export const roiLabels: Record<Roi, string> = {
  combined: "Regiões combinadas",
  forehead: "Testa",
  left_cheek: "Bochecha esquerda",
  right_cheek: "Bochecha direita",
};
export const statuses: Record<Job["status"], string> = {
  queued: "Na fila",
  processing: "Processando",
  completed: "Concluído",
  failed: "Falha na análise",
  cancelled: "Cancelado",
  expired: "Expirado",
};
export const reasons: Record<string, string> = {
  unknown_quality_flag: "Indicador de qualidade não reconhecido",
  invalid_geometry: "Geometria da região inválida",
  insufficient_pixels: "Poucos pixels válidos",
  low_valid_fraction: "Área útil insuficiente",
  insufficient_nyquist: "Cadência insuficiente para a banda",
  low_temporal_coverage: "Cobertura temporal insuficiente",
  nonfinite_rgb: "RGB inválido",
  rgb_out_of_range: "RGB fora da escala",
  filter_window_too_short: "Janela curta para filtrar",
  nonfinite_filtered_signal: "Sinal filtrado inválido",
  insufficient_interior: "Trecho útil insuficiente",
  insufficient_projection_support: "Amostras insuficientes para projeção",
  projection_window_too_short: "Janela curta para projeção",
  invalid_channel_mean: "Média de canal inválida",
  invalid_method_rgb: "RGB inadequado ao método",
  degenerate_chrom_projection: "Projeção CHROM degenerada",
  degenerate_pos_projection: "Projeção POS degenerada",
  insufficient_spectral_resolution: "Resolução espectral insuficiente",
  insufficient_spectral_energy: "Energia espectral insuficiente",
  peak_at_band_edge: "Pico no limite da banda",
  stale_estimate: "Estimativa vencida",
  video_limits_exceeded: "Vídeo excede os limites de processamento",
  unsupported_video: "Vídeo não suportado",
  processing_failed: "Falha ao processar o vídeo",
  job_timeout: "Tempo limite de processamento atingido",
  storage_limit: "Limite de armazenamento atingido",
  worker_terminated: "Processamento interrompido",
  worker_start_failed: "Não foi possível iniciar o processamento",
  supervisor_error: "Falha no supervisor de processamento",
  service_interrupted: "Serviço interrompido",
  retention_expired: "Prazo de retenção encerrado",

  no_face: "Face não encontrada",
  multiple_faces: "Múltiplas faces",
  insufficient_data: "Dados insuficientes",
  window_too_short: "Vídeo curto para a janela",
  constant_signal: "Sinal constante",
  invalid_roi_samples: "Região sem sinal válido",
  excessive_motion: "Movimento elevado",
  recovering_signal: "Aguardando confirmação",
  unstable_between_windows: "Estimativa instável",
  illumination_instability: "Iluminação instável",
  illumination_change: "Variação de iluminação",
  saturated_roi: "Saturação elevada",
  dark_roi: "Região escura",
  temporal_gap: "Lacuna temporal",
  low_band_energy: "Energia insuficiente na banda",
  diffuse_spectrum: "Espectro difuso",
  ambiguous_peaks: "Picos concorrentes",
  partial_roi: "Composição da região alterada",
  tracking_interrupted: "Tracking interrompido",
  irregular_sampling: "Amostragem irregular",
};
export function explain(code: string) {
  return reasons[code] ?? code.replaceAll("_", " ");
}
export function apiBase(value: string) {
  const url = new URL(value);
  if (
    !["127.0.0.1", "localhost", "[::1]"].includes(url.hostname) ||
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password
  )
    throw new Error("Use um endereço local sem credenciais na URL.");
  return url.origin + "/api/v1";
}
export function validateFile(file: File, policy: Policy) {
  if (!/\.(mp4|mov|webm|avi)$/i.test(file.name))
    return "Selecione MP4, MOV, WebM ou AVI.";
  if (file.size === 0) return "O arquivo está vazio.";
  if (file.size > policy.max_upload_bytes)
    return "O arquivo excede o limite de tamanho.";
  return null;
}
export function mime(file: File) {
  return /\.webm$/i.test(file.name)
    ? "video/webm"
    : /\.mov$/i.test(file.name)
      ? "video/quicktime"
      : /\.avi$/i.test(file.name)
        ? "video/x-msvideo"
        : "video/mp4";
}
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(`${status}: ${message}`);
    this.name = "ApiError";
  }
}
export async function removeJob(
  base: string,
  key: string,
  id: string,
  signal?: AbortSignal,
) {
  try {
    await call(base, key, `/videos/jobs/${id}`, { method: "DELETE", signal });
  } catch (error) {
    if (!(error instanceof ApiError) || ![404, 410].includes(error.status))
      throw error;
  }
}
export async function call<T>(
  base: string,
  key: string,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(base + path, {
    ...init,
    cache: "no-store",
    headers: { ...(key ? { "X-API-Key": key } : {}), ...init.headers },
  });
  if (!response.ok) {
    let message = "";
    try {
      const body = await response.json();
      message =
        typeof body.detail === "string" ? body.detail : "Parâmetros inválidos.";
    } catch {
      message = "Resposta indisponível.";
    }
    throw new ApiError(response.status, message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export async function allEstimates(
  base: string,
  key: string,
  id: string,
  signal: AbortSignal,
) {
  let items: EstimateResult[] = [];
  let page: Page;
  do {
    page = await call<Page>(
      base,
      key,
      `/videos/jobs/${id}/results?offset=${items.length}&limit=500`,
      { signal },
    );
    items = items.concat(page.items);
    if (!page.items.length && items.length < page.total)
      throw new Error("Paginação de resultados interrompida.");
  } while (items.length < page.total);
  return { ...page, items };
}
export async function allRegions(
  base: string,
  key: string,
  id: string,
  signal: AbortSignal,
) {
  let points: Region[] = [];
  let page: SignalPage<Region>;
  do {
    page = await call<SignalPage<Region>>(
      base,
      key,
      `/videos/jobs/${id}/signals?series=roi&offset=${points.length}&limit=1000`,
      { signal },
    );
    points = points.concat(page.points);
    if (!page.points.length && points.length < page.total)
      throw new Error("Paginação de regiões interrompida.");
  } while (points.length < page.total);
  return points;
}
export function regionAt(points: Region[], seconds: number) {
  let low = 0,
    high = points.length - 1,
    index = -1;
  while (low <= high) {
    const middle = (low + high) >> 1;
    if (points[middle].timestamp_s <= seconds) {
      index = middle;
      low = middle + 1;
    } else high = middle - 1;
  }
  return index >= 0 && seconds - points[index].timestamp_s <= 0.25
    ? points[index]
    : null;
}

export async function allSignal<S extends keyof SignalMap>(
  base: string,
  key: string,
  id: string,
  series: S,
  window: number,
  signal: AbortSignal,
) {
  let points: SignalMap[S][] = [];
  let page: SignalPage<SignalMap[S]>;
  do {
    page = await call<SignalPage<SignalMap[S]>>(
      base,
      key,
      `/videos/jobs/${id}/signals?series=${series}&window=${window}&offset=${points.length}&limit=1000`,
      { signal },
    );
    points = points.concat(page.points);
    if (!page.points.length && points.length < page.total)
      throw new Error("Paginação do sinal interrompida.");
  } while (points.length < page.total);
  return points;
}
