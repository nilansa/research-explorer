# Agent handoff

- Entry: `index.html`; data: `data/curdkv.json`; pure engine: `engine.mjs`; UI: `app.mjs`.
- Keep source claims on cited papers distinct from hypotheses and untested combinations.
- Never show fabricated scores or imply live literature review. The numerical fit is a structural heuristic only.
- Case imports are untrusted, capped at 1 MiB, validate HTTP(S) URLs, and are rendered without HTML injection.
- Static only: no Claude API, literature API, telemetry, or remote dependencies.
- Packet schemas and evidence limits are in README.md.
