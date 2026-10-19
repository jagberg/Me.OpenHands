# Me.OpenHands

Decisions: `docs/adr/` and `CHANGELOG.md` - read before proposing architecture changes. Recorded alternatives (Devin,
Factory, n8n, Windmill, custom orchestrator, OpenHands CLI) were rejected for stated reasons; don't re-suggest them
without new information.

- Main code: `blueprint/` (Temporal workflow + OpenHands SDK). `pipeline/` is superseded.
- Direction under review: ADR 0005 (proposed) moves the process into prompts inside an agent harness; harness not
  chosen. Bake-off evidence in `bakeoff/README.md`. Don't extend the coded stage order without checking ADR 0005.
- Changing `blueprint/workflow.py` shape: use `workflow.patched()` or a new workflow type, or in-flight runs fail replay (ADR 0003).
- Human gates and decision tests are plain code on purpose; don't move them into agent prompts (ADR 0002).
- Porting to a work repo: `docs/work-repo-setup.md`.
- Never commit `runs/` (local run state, workspaces) or API keys/tokens.
