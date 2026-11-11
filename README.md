# Research Explorer

A spare static interface for finding source-linked research-problem neighbors. The browser ranks the curated local `data/problem-index.json` records lexically (BM25-style term weighting). Results are metadata matches only: they are unreviewed, may have incomplete abstracts, and are not semantic similarity, novelty, or full-text verification. Select records to include them with A-side problem-family and M-side mechanism-family context in an exportable Claude Science task. The site does not connect to Claude Science.

Open through a static server because the page loads local ES modules and JSON:

```sh
python3 -m http.server 8000
```

The optional collapsed method-variant section preserves the legacy 16/48/144 generator and `engine.mjs` behavior. Its structural labels are not scientific quality scores. `data/curdkv.json` remains the source of the A/M lists; each entry links to its public source.

## Local benchmark harness

`agent/research_taste.py` uses Python standard library only (Python 3.9+). Evidence and run outputs must be stored in a caller-chosen private directory outside the repository.

```sh
python3 agent/research_taste.py retrieve --query "KV cache compression attention output" --out /private/scratch/evidence.json --limit 20
python3 agent/research_taste.py prepare --evidence /private/scratch/evidence.json --outdir /private/scratch/prepared --seed 42 --case data/curdkv.json
python3 agent/research_taste.py run --manifest /private/scratch/prepared/manifest.json --arm baseline --profile /path/to/claude-science-profile --out /private/scratch/baseline.raw.json --dry-run
python3 agent/research_taste.py score --manifest /private/scratch/prepared/manifest.json --baseline /private/scratch/baseline.raw.json --structured /private/scratch/structured.raw.json --out /private/scratch/grading.json
```

`retrieve` only contacts the local ConfHub loopback API (`127.0.0.1:18765`), bounds text and result counts, rejects non-HTTPS source links, and stores query provenance. `prepare` writes the same evidence and constraints into both prompts; only direct brainstorming versus A/M dual-neighborhood framing differs. Use the same Claude Science model and budget for both arms. This controlled generation pass deliberately disables browser and file tools, so it can only assess supplied metadata and abstracts; it must mark unverified full-text claims and novelty checks as unresolved. The independent reviewer must examine full texts before assigning research-taste ratings. `run` checks the selected Claude CLI profile's auth state and requires `loggedIn: true`; it does not fall back to Claude Code. It runs with strict MCP config, empty tools, no session persistence, JSON output, and a bounded timeout. Use `--dry-run` to inspect planned settings without invoking Claude. The run command does not send email or execute tools. `score` emits a blinded manual rubric with blank ratings and mechanical counts only; an independent judge fills ratings after literature and theory review.

## Boundaries and checks

The public static site contains curated public source metadata only. No private workspaces, credentials, benchmark prompts, or run outputs belong in this repository. No runtime network API, telemetry, CDN, or added dependency is used by the page. Local benchmark evidence is only persisted in the caller-selected output directory.

```sh
node --test tests/engine.test.mjs
node --check app.mjs
node --check engine.mjs
python3 -m unittest discover -s tests -p 'test_*.py'
```
