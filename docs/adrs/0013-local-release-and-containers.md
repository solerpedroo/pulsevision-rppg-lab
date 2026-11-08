# ADR 0013 — local v1.0.0 preparation and isolated execution

Status: accepted · 2026-11-08 · PV-1101–PV-1109.

## Context

Engineering waves are available, but no authorized physiological dataset is local.
The final planned wave concerns polish, reproducible local setup and presentation.
The user requested the next wave, without authorizing publication or human capture.

## Decision

Prepare version 1.0.0 consistently in Python/npm/API/UI and a local release dossier.
Version identifies engineering behavior, not demonstrated human accuracy. Preserve
scientific work from waves 6/10 as pending. Do not create a remote release, deploy,
tag, push or contact anyone as part of this preparation.

Share the three Labs' navigation and experimental version notice. Preserve null
chart gaps while scaling small nonzero signals honestly. Check initial pages using
axe in Chromium, plus existing integration/lifecycle tests; automated checks do
not establish complete accessibility or real-device support.

Offer optional web/API Compose with a single supervised worker inside API. Bind
host ports to loopback, require a generated private key, use non-root read-only
containers and a dedicated jobs volume. Bind only a staged checksum-verified model
copy. No home, project tree, device, socket or dataset mount. Model staging keeps
the original mode/label unchanged. Explicit loopback origin/port configuration
supports occupied development ports without permissive CORS.

Use a scoped minimatch override to fix the audited development dependency without
changing Next's major version. Keep lockfiles and audit evidence. Coverage reports
include branches and identify subprocess instrumentation gaps, rather than adding
mirrored tests or claiming every native worker line was measured.

Record only an automated page with artificial study results, not a desktop or
physical camera. Screenshots contain only project UI and original synthetic data.

## Consequences

Builds require network access for locked dependencies/base images. Images contain
no weights; explicit model setup is needed. API keys are visible to the local
container owner and must not be shared via inspect/config output. Image tags remain
mutable; no registry push/signing/SBOM provenance is asserted. Compose shutdown
retains jobs until explicit volume removal. Scientific conclusions and remote
publication remain separate unfinished work.
