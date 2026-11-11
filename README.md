# Research Explorer

Vanilla JavaScript static research-space explorer for GitHub Pages project paths. It uses only relative local assets and has no runtime API. Open `index.html` through a local static server (ES modules and fetch do not work reliably from `file://`).

## Run

```sh
python3 -m http.server 8000
```

Open `http://localhost:8000/`. On GitHub Pages, publish this directory as the repository root for `/research-explorer/`.

## Case schema

`data/curdkv.json` contains `id`, `current` (`name`, `url`, optional `venue`, `claims`, `evidence`), `a[]`, `m[]` (`id`, `name`, `summary`, `url`, optional `role`, `evidence`), and `caveats[]`. Imported JSON is limited to 1 MiB. Item URLs must be HTTP(S); rendering uses DOM text nodes and external links use `noopener noreferrer`. CSP allows scripts/styles/connections only from self. A new case applies for the current page session and can be exported as JSON.

## Boundaries and handoff

The source links support individual paper descriptions only. They do not establish causal lineage or validate a proposed pairing. All combinations carry `UNTESTED`; compatibility scores are structural heuristics and are not scientific scores. Compute costs are unknown until hardware, model, and workload are chosen. This site performs no live literature scan and has no Claude API. The review prompt requests novelty, mathematical, engineering, compute, and evidence review. A future imported review can be shown as a user supplied artifact; it must never be represented as an independent verification by this static app.

Candidate packet schema: `research-explorer-candidate/1`, with candidate path, explicit untested status, structural fit, assumptions, unknown compute estimate, and source boundary. Packet collection schema: `research-explorer-packet/1`. Local shortlist IDs are stored in localStorage; they are not sent anywhere. Tree depth is 16 pairings, 48 one-transformation branches, and 144 two-transformation branches.

## Checks

```sh
node --test tests/engine.test.mjs
node --check engine.mjs
node --check app.mjs
```
