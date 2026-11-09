"use client";
import { useEffect, useState, type RefObject } from "react";
import { Video } from "lucide-react";
import { regionAt, type Region, type Roi } from "./api";

// Per-frame overlay state stays here so scientific charts do not render at video FPS.
export function VideoPreview({
  video,
  url,
  aspect,
  regions,
  roi,
  onMetadata,
  onError,
  onTime,
}: {
  video: RefObject<HTMLVideoElement | null>;
  url: string;
  aspect: number;
  regions: Region[];
  roi: Roi | undefined;
  onMetadata: () => void;
  onError: () => void;
  onTime: (time: number) => void;
}) {
  const [frameTime, setFrameTime] = useState(0);
  useEffect(() => {
    const element = video.current;
    if (!url || !element || !element.requestVideoFrameCallback) return;
    let handle: number;
    const update: VideoFrameRequestCallback = (_, metadata) => {
      setFrameTime(metadata.mediaTime);
      handle = element.requestVideoFrameCallback(update);
    };
    handle = element.requestVideoFrameCallback(update);
    return () => element.cancelVideoFrameCallback(handle);
  }, [url, video]);
  const overlay = regionAt(regions, frameTime);
  return (
    <div className="preview" style={{ aspectRatio: aspect }}>
      {url ? (
        <>
          <video
            ref={video}
            src={url}
            controls
            preload="metadata"
            onLoadedMetadata={onMetadata}
            onError={onError}
            onTimeUpdate={(e) => {
              onTime(e.currentTarget.currentTime);
              if (!e.currentTarget.requestVideoFrameCallback)
                setFrameTime(e.currentTarget.currentTime);
            }}
            onSeeked={(e) => {
              setFrameTime(e.currentTarget.currentTime);
              onTime(e.currentTarget.currentTime);
            }}
            aria-label="Preview local do vídeo"
          />
          {overlay && (
            <svg
              className="roi-overlay"
              viewBox="0 0 1 1"
              preserveAspectRatio="none"
              role="img"
              aria-label="Regiões detectadas neste instante"
            >
              {Object.entries(overlay.regions)
                .filter(([name]) => roi === "combined" || name === roi)
                .map(([name, polygon]) => {
                  const rings =
                    polygon.length && Array.isArray(polygon[0][0])
                      ? (polygon as number[][][])
                      : [polygon as number[][]];
                  const d = rings
                    .map(
                      (ring) =>
                        `M ${ring.map((pair) => pair.join(",")).join(" L ")} Z`,
                    )
                    .join(" ");
                  return (
                    <path
                      key={name}
                      d={d}
                      fill="rgba(177,245,114,.18)"
                      stroke="#bcf775"
                      strokeWidth=".003"
                      fillRule="evenodd"
                    />
                  );
                })}
            </svg>
          )}
        </>
      ) : (
        <div className="preview-empty">
          <div className="preview-grid" />
          <Video size={36} />
          <strong>Seu vídeo, em foco.</strong>
          <p>O preview é local. A análise começa só após sua confirmação.</p>
        </div>
      )}
    </div>
  );
}
