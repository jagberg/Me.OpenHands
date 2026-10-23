# Me.OpenHands

Decisions: `docs/adr/` and `CHANGELOG.md` - read before proposing architecture changes. Recorded alternatives (Devin,
Factory, n8n, Windmill, custom orchestrator, OpenHands CLI) were rejected for stated reasons; don't re-suggest them
without new information.

- Main code: `factory/` (thin shell around the OpenHands agent, ADR 0005). `blueprint/` (Temporal) and `pipeline/` are earlier prototypes.
- Direction (ADR 0005, accepted 2026-10-21): the process lives in prompts (`AGENTS.md` + `.agents/skills`) inside the
  OpenHands SDK, local model `qwen3.8:27b` at 32k. Don't extend the coded stage order in `blueprint/`. Evidence:
  `bakeoff/README.md`. Run OpenHands inside Docker (no host sandbox); keep reasoning on; validate skill YAML.
- Changing `blueprint/workflow.py` shape: use `workflow.patched()` or a new workflow type, or in-flight runs fail replay (ADR 0003).
- Human gates and decision tests are plain code on purpose; don't move them into agent prompts (ADR 0002).
- Porting to a work repo: `docs/work-repo-setup.md`.
- Never commit `runs/` (local run state, workspaces) or API keys/tokens.
