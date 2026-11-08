import { afterEach, describe, expect, it, vi } from "vitest";
import {
  removeJob,
  type Region,
  apiBase,
  validateFile,
  regionAt,
  allSignal,
  allRegions,
  call,
} from "../features/video/api";
const policy = {
  max_upload_bytes: 100,
  max_duration_s: 120,
  max_pixels: 2073600,
  max_fps: 60,
  retention_s: 86400,
};
afterEach(() => vi.unstubAllGlobals());
describe("limites de upload e destino", () => {
  it("rejeita extensão falsa, vazio e excesso de tamanho", () => {
    expect(validateFile(new File(["x"], "fooamp4"), policy)).toContain(
      "Selecione",
    );
    expect(validateFile(new File([], "video.mp4"), policy)).toContain("vazio");
    expect(
      validateFile(new File(["x".repeat(101)], "video.mp4"), policy),
    ).toContain("tamanho");
    expect(validateFile(new File(["x"], "VIDEO.MP4"), policy)).toBeNull();
  });
  it("aceita apenas origens locais sem credenciais", () => {
    expect(apiBase("http://localhost:8000/path")).toBe(
      "http://localhost:8000/api/v1",
    );
    expect(() => apiBase("https://example.org")).toThrow();
    expect(() => apiBase("http://secret@localhost:8000")).toThrow();
  });
});
it("sincroniza geometria por tempo sem reutilizar uma detecção ausente ou antiga", () => {
  const regions: Region[] = [
    {
      timestamp_s: 0,
      regions: {
        forehead: [
          [0, 0],
          [1, 0],
          [1, 1],
        ],
      },
    },
    { timestamp_s: 0.04, regions: {} },
  ];
  expect(regionAt(regions, -1)).toBeNull();
  expect(regionAt(regions, 0.03)).toBe(regions[0]);
  expect(regionAt(regions, 0.05)?.regions).toEqual({});
  expect(regionAt(regions, 1)).toBeNull();
});
it("pagina sinais completos sem truncar a janela de 60 FPS", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValueOnce(
      Response.json({
        total: 1002,
        points: Array.from({ length: 1000 }, (_, i) => ({
          timestamp_s: i / 60,
          value: i,
        })),
      }),
    )
    .mockResolvedValueOnce(
      Response.json({
        total: 1002,
        points: [
          { timestamp_s: 1000 / 60, value: 1000 },
          { timestamp_s: 1001 / 60, value: 1001 },
        ],
      }),
    );
  vi.stubGlobal("fetch", fetcher);
  const points = await allSignal(
    "http://localhost/api/v1",
    "",
    "id",
    "rppg",
    0,
    new AbortController().signal,
  );
  expect(points).toHaveLength(1002);
  expect(fetcher.mock.calls[1][0]).toContain("offset=1000");
});
it("detecta paginação incompleta e propaga erro da API", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(Response.json({ total: 1, points: [] })),
  );
  await expect(
    allRegions("", "", "id", new AbortController().signal),
  ).rejects.toThrow("interrompida");
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        Response.json({ detail: "model_unavailable" }, { status: 503 }),
      ),
  );
  await expect(call("", "", "/policy")).rejects.toThrow(
    "503: model_unavailable",
  );
});

it("descarta sessão já expirada mas preserva erros de acesso", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(Response.json({ detail: "expired" }, { status: 410 })),
  );
  await expect(removeJob("", "", "expired")).resolves.toBeUndefined();
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        Response.json({ detail: "forbidden" }, { status: 403 }),
      ),
  );
  await expect(removeJob("", "", "denied")).rejects.toThrow("403");
});
