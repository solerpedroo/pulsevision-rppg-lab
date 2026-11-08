// mediaTime may be quantized. A 1 ms scheduling tolerance avoids dropping a
// nominal 30 Hz frame merely because its measured interval is 33.332 ms.
export function shouldCapture(
  timestamp: number,
  last: number,
  inflight: boolean,
) {
  return (
    !inflight &&
    Number.isFinite(timestamp) &&
    timestamp >= 0 &&
    timestamp - last >= 1 / 30 - 0.001 &&
    Math.floor(timestamp * 1000) > Math.floor(last * 1000)
  );
}
