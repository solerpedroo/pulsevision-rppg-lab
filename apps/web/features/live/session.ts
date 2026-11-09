import { shouldCapture } from "./cadence";
import config from "./generated-config.json";
import webPackage from "../../package.json";
import { RingBuffer } from "./buffer";
import type {
  Analysis,
  FrameReport,
  Phase,
  WorkerInput,
  WorkerOutput,
} from "./types";
import type { Method, Roi } from "../video/api";
interface Callbacks {
  phase: (phase: Phase, error?: string) => void;
  frame: (report: FrameReport, skipped: number) => void;
  devices: (devices: MediaDeviceInfo[]) => void;
}
export class LiveSession {
  private dead = false;
  private stream: MediaStream | null = null;
  private worker: Worker | null = null;
  private callback: number | null = null;
  private interval: ReturnType<typeof setInterval> | null = null;
  private timeout: ReturnType<typeof setTimeout> | null = null;
  private inflight = false;
  private pendingBitmap: ImageBitmap | null = null;
  private pendingTime: number | null = null;
  private canvas: OffscreenCanvas | null = null;
  private lastSent = -Infinity;
  private lastResponse = 0;
  private skipped = 0;
  private history: Analysis[] = [];
  readonly buffer = new RingBuffer();
  constructor(
    private video: HTMLVideoElement,
    private method: Method,
    private roi: Roi,
    private callbacks: Callbacks,
  ) {}
  async start(device: string) {
    this.callbacks.phase("permission");
    document.addEventListener("visibilitychange", this.visibility);
    try {
      if (
        !window.isSecureContext ||
        !navigator.mediaDevices?.getUserMedia ||
        !window.Worker ||
        !window.OffscreenCanvas ||
        !window.createImageBitmap
      )
        throw new Error(
          "Navegador sem câmera segura, Worker ou OffscreenCanvas. Use um navegador compatível em localhost/HTTPS.",
        );
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          frameRate: { ideal: 30, max: 30 },
          ...(device
            ? { deviceId: { exact: device } }
            : { facingMode: "user" }),
        },
      });
      if (this.dead) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      this.stream = stream;
      for (const track of stream.getTracks())
        track.addEventListener("ended", this.ended);
      this.video.srcObject = stream;
      await this.video.play();
      if (this.dead) return;
      window.addEventListener("pagehide", this.pagehide);
      navigator.mediaDevices.addEventListener(
        "devicechange",
        this.devicechange,
      );
      void this.refreshDevices();
      this.callbacks.phase("detector");
      const worker = new Worker(
        new URL("./processor.worker.ts", import.meta.url),
      );
      this.worker = worker;
      worker.onerror = () =>
        this.fail(
          "O worker de visão falhou. Confira os assets locais e o suporte do navegador.",
        );
      worker.onmessage = (event: MessageEvent<WorkerOutput>) => {
        if (this.dead) return;
        const message = event.data;
        if (message.type === "error") {
          this.fail(message.message);
          return;
        }
        if (message.type === "ready") {
          if (this.timeout) clearTimeout(this.timeout);
          this.lastResponse = performance.now();
          this.callbacks.phase("warmup");
          this.interval = setInterval(() => {
            if (performance.now() - this.lastResponse > 3000)
              this.fail(
                "Captura ou processamento sem resposta há mais de 3 s. Inicie uma nova sessão.",
              );
          }, 500);
          this.schedule();
          return;
        }
        this.inflight = false;
        this.lastResponse = performance.now();
        const queued = this.pendingBitmap;
        const queuedTime = this.pendingTime;
        this.pendingBitmap = null;
        this.pendingTime = null;
        this.buffer.push(message.sample);
        if (
          message.analysis &&
          this.history.at(-1)?.end_s !== message.analysis.end_s
        ) {
          this.history.push(message.analysis);
          if (this.history.length > 30) this.history.shift();
        }
        this.callbacks.frame(message, this.skipped);
        if (queued && queuedTime !== null && !this.dead) {
          this.inflight = true;
          this.lastSent = queuedTime;
          this.send({ type: "frame", bitmap: queued, timestamp_s: queuedTime }, [
            queued,
          ]);
        }
      };
      this.timeout = setTimeout(
        () => this.fail("Tempo limite ao iniciar o detector local."),
        30000,
      );
      this.send({
        type: "init",
        origin: location.origin,
        method: this.method,
        roi: this.roi,
      });
    } catch (error) {
      if (!this.dead) {
        const messages: Record<string, string> = {
          NotAllowedError:
            "Permissão de câmera negada. Você pode tentar novamente.",
          NotFoundError: "Nenhuma câmera disponível.",
          NotReadableError: "Câmera ocupada ou indisponível.",
          NotSupportedError:
            "O navegador não conseguiu abrir a câmera. Confira suporte e dispositivo.",
          OverconstrainedError:
            "A câmera selecionada não atende à configuração solicitada.",
          SecurityError: "O navegador bloqueou o acesso à câmera.",
        };
        this.fail(
          error instanceof DOMException
            ? (messages[error.name] ?? "A captura foi interrompida.")
            : error instanceof Error
              ? error.message
              : "Não foi possível iniciar a câmera.",
        );
      }
    }
  }

  private send(message: WorkerInput, transfer: Transferable[] = []) {
    this.worker?.postMessage(message, transfer);
  }
  private schedule() {
    if (this.dead) return;
    if (this.video.requestVideoFrameCallback)
      this.callback = this.video.requestVideoFrameCallback((_, metadata) => {
        this.schedule();
        this.capture(metadata.mediaTime);
      });
    else
      this.callback = requestAnimationFrame(() => {
        this.schedule();
        this.capture(this.video.currentTime);
      });
  }
  private snapshot(): ImageBitmap | null {
    const width = Math.min(320, this.video.videoWidth),
      height = Math.max(
        1,
        Math.round((width * this.video.videoHeight) / this.video.videoWidth),
      );
    if (!this.canvas || this.canvas.width !== width || this.canvas.height !== height)
      this.canvas = new OffscreenCanvas(width, height);
    const context = this.canvas.getContext("2d");
    if (!context) return null;
    context.drawImage(this.video, 0, 0, width, height);
    return this.canvas.transferToImageBitmap();
  }
  private capture(timestamp: number) {
    if (this.dead) return;
    if (!shouldCapture(timestamp, this.lastSent, false)) {
      this.skipped++;
      return;
    }
    if (!Number.isFinite(timestamp) || timestamp < 0 || !this.video.videoWidth)
      return;
    let bitmap: ImageBitmap | null = null;
    try {
      bitmap = this.snapshot();
    } catch {
      bitmap = null;
    }
    if (!bitmap) {
      if (!this.dead) this.fail("Não foi possível ler um frame da câmera local.");
      return;
    }
    if (this.inflight) {
      this.pendingBitmap?.close();
      this.pendingBitmap = bitmap;
      this.pendingTime = timestamp;
      return;
    }
    this.inflight = true;
    this.lastSent = timestamp;
    this.send({ type: "frame", bitmap, timestamp_s: timestamp }, [bitmap]);
  }
  private ended = () => this.fail("A câmera foi desconectada ou interrompida.");
  private visibility = () => {
    if (document.hidden) this.stop();
  };
  private pagehide = () => this.dispose();
  private devicechange = () => {
    void this.refreshDevices();
  };
  private async refreshDevices() {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      if (this.dead) return;
      this.callbacks.devices(devices.filter((d) => d.kind === "videoinput"));
      const id = this.stream?.getVideoTracks()[0]?.getSettings().deviceId;
      if (
        id &&
        !devices.some((d) => d.kind === "videoinput" && d.deviceId === id)
      )
        this.ended();
    } catch {
      /* Track ended still handles device loss when enumeration is denied. */
    }
  }
  private fail(error: string) {
    if (this.dead) return;
    this.dispose();
    this.callbacks.phase("error", error);
  }
  stop() {
    this.dispose();
    this.callbacks.phase("stopped");
  }
  dispose() {
    this.dead = true;
    if (this.callback !== null) {
      if (this.video.cancelVideoFrameCallback)
        this.video.cancelVideoFrameCallback(this.callback);
      else cancelAnimationFrame(this.callback);
    }
    if (this.interval) clearInterval(this.interval);
    if (this.timeout) clearTimeout(this.timeout);
    document.removeEventListener("visibilitychange", this.visibility);
    window.removeEventListener("pagehide", this.pagehide);
    this.pendingBitmap?.close();
    this.pendingBitmap = null;
    navigator.mediaDevices?.removeEventListener(
      "devicechange",
      this.devicechange,
    );
    this.worker?.terminate();
    this.worker = null;
    for (const track of this.stream?.getTracks() ?? []) {
      track.removeEventListener("ended", this.ended);
      track.stop();
    }
    this.stream = null;
    this.video.pause();
    this.video.srcObject = null;
    this.buffer.clear();
    this.history = [];
  }
  export() {
    return {
      version: "live-v1",
      parameters: config,
      mediapipe_version: webPackage.dependencies["@mediapipe/tasks-vision"],
      model_sha256:
        "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff",
      notice: "Experimental estimate; not a medical device.",
      method: this.method,
      roi: this.roi,
      clock: "video presentation mediaTime, relative to first analyzed frame",
      resample_fs: 30,
      window_s: 20,
      edge_trim_s: this.method === "GREEN" ? 1 : 1.6,
      rows: this.buffer.snapshot(),
      analyses: this.history,
    };
  }
}
