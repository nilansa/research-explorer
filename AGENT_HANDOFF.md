# Agent handoff

- Static public interface: `index.html`, `styles.css`, `app.mjs`.
- Curated public metadata: `data/problem-index.json`; A/M source context: `data/curdkv.json`.
- `engine.mjs` remains intact and powers only the optional collapsed legacy variant section.
- Browser retrieval is lexical metadata ranking only. Source records and match terms are unreviewed; records are not full-text verified and do not establish novelty or semantic similarity.
- Claude Science is not connected from the public page. The page only copies/exports a task.
- Local benchmark commands are in `agent/research_taste.py`. Keep evidence, prepared prompts, profiles, and outputs in private caller-selected storage outside this repository. Run both arms with the same model, evidence, constraints, and budget. Independent grading must remain blind and ratings blank until judged.
- The harness uses the ConfHub loopback search API only, safe HTTPS source links, bounded input/result text, and no credentials in output. It must not fall back to Claude Code when the Claude Science profile is unavailable.
