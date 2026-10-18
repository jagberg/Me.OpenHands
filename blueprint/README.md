# Ignite blueprint on Temporal (local prototype)

A Stripe-style blueprint: fixed nodes, some deterministic (`*`), some agentic (OpenHands), with human gates.

```
ticket -> setup* -> ignite-brief -> decision-gate -> [HUMAN answers] -> ignite-plan -> ignite-build
       -> tests* + decision-tests* (reject back to build, max 3) -> engineering / security / qa reviews
       -> validate* -> open PR* -> ai-code-review -> [HUMAN merges/closes PR] -> done
```

| Piece | Where |
|---|---|
| Temporal server + Web UI (lifecycle, history, retries) | Docker, http://localhost:8233 |
| Worker (runs the nodes; agents via OpenHands SDK) | host: `.venv/bin/python worker.py` (or `docker compose --profile worker up -d --build` with `GH_TOKEN` in `.env`) |
| Metrics + human-in-the-loop dashboard | `../dashboard`, http://localhost:8765 (`.venv/bin/python ../dashboard/server.py`) |
| Skills (dummy ignite/eng/sec/qa prompts) | `skills/*.md` |

## Run
```bash
docker compose up -d temporal
uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python worker.py &                    # needs Ollama + your git/gh login
.venv/bin/python ../dashboard/server.py &       # dashboard on :8765
.venv/bin/python start.py ../trials/TICKET.md   # or "+ New run" in the dashboard
```

## Human in the loop
- **Decision gate** after the brief: one narrow LLM call lists decisions as JSON; each becomes a BLOCKING question. The workflow
  parks (no compute) until answered in the dashboard, which sends a Temporal **signal**.
- Agents may also ask any time by writing `.ignite/QUESTION.md` (`BLOCKING:` parks, `ASK:` continues on its assumption).
- Every answered decision must be pinned by a test in `test_decisions.py`; a deterministic check rejects the build otherwise.
- Final gate: a human merges or closes the PR; the workflow polls and finishes.

## Swapping the model (Bedrock)
`LLM_MODEL=bedrock/<model-id> LLM_BASE_URL= AWS_REGION=... ` with AWS creds from env/role. Nothing else changes.

## Changing the workflow safely
Running workflows replay their history against new code. Guard shape changes with `workflow.patched("<name>")`
(see `decision-gate`, `decision-tests` in workflow.py). Without it, in-flight runs fail with a nondeterminism error.

## Known limits (prototype)
- Local qwen3:14b is the weak link: thin plans, ignores instructions (it skipped the decision until the test check forced it).
- 60s PR polling; use a GitHub webhook -> signal for long-lived PRs. No auth on the dashboard (binds 127.0.0.1).
