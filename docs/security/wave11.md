# Local security review — wave 11

PV-1103 · 2026-11-08. A scoped engineering review, not a penetration-test certification.

## Dependencies

The initial npm audit reported eight moderate entries in the minimatch development
chain. [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249)
identifies the affected range and fix 11.0.1. A scoped override under
`@typescript-eslint/typescript-estree` resolves that path without downgrading Next.
The lock records the resolution; lint/type/test/build validate compatibility.
Final npm and Python audit results are recorded in state.md. pip-audit checks
published distributions; it skips the local project package and does not assess
our source code. A zero count applies to the databases/time queried, not future safety.

## Upload boundary reviewed

The API accepts supported raw binary video bodies with MIME/signature agreement,
streamed size/deadline checks, bounded queue and request/upload rates. Native
decoding/DSP runs in a supervised subprocess with time/CPU/resource limits. Storage
uses generated identifiers, private paths, terminal original deletion, TTL cleanup
and explicit deletion. Results are paginated. Unsupported/truncated media and
invalid IDs/parameters are covered by regression tests. No user filename becomes
a storage path or shell command. Routes do not decode video on the event loop.

Trusted hosts, explicit loopback origins and optional native API key guard the
local boundary; containers require the key because bridge peers are not loopback.
Unauthorized/origin/rate-limit responses now carry no-store/nosniff too. Keys must
never enter logs, public env variables or version control. Web responses restrict
framing, object embedding, microphone and geolocation. CSP is deliberately limited:
`object-src`, `base-uri`, `frame-ancestors`; it is not a strict script policy because
runtime schema compilation/WASM need a separate compatibility design.

## Remaining risks and scope

Native codecs and landmark libraries process untrusted bytes. Resource limits and
containers reduce impact; neither proves immunity to native parser vulnerabilities.
Local authentication does not make this an internet service. No accounts, TLS
termination, multi-tenant isolation, malware scanner or remote deployment is claimed.
Browser imports validate schema/relationships, not truth or authenticity of reports.
Downloaded exports outlive deletion of server/worker state. The local machine and
container owner can inspect secrets/data. Mutable base tags require fresh audits.
Do not expose ports beyond loopback or mount private directories into containers.
