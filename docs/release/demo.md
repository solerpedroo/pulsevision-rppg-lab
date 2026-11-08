# Face-free synthetic demo

PV-1108 · recorded locally on 2026-11-08.

```bash
npm run build
npx playwright install chromium ffmpeg
npm run demo
```

The script generates a new artificial three-participant study with the actual
Python runner, starts its own production Next.js process on loopback port 3200,
records only its Chromium page, imports the labeled JSON, filters 20 s/POS,
groups by participant and discards the review. It closes its own browser/server.
Set `PULSEVISION_DEMO_PORT` if necessary; occupied ports are refused.
It never records the desktop, requests a physical camera or sends a report to API.
Playback pauses are deliberate presentation timing, not performance measurements.

Local output: `artifacts/wave11-demo-ixj07i/`, with a WebM, screenshot,
`recording.json`, generated study and server log. These artifacts are ignored by
Git. The README's benchmark screenshot is from that production recording;
its video screenshot is from the automated face-free upload scenario.
No faces, human pulse measurements or privately supplied material are depicted.
This is a demonstration of filtering/provenance, not physiological accuracy.
