# Me.OpenHands - agentic SDLC prototype

A local prototype of an "AI software factory": a ticket goes through the ignite stages, engineering/security/QA
reviews and a PR, with humans answering decisions and doing the final review. Built on **Temporal** (workflow, state,
retries, UI) and the **OpenHands SDK** (coding agents), running on a local Ollama model.

Decisions: `docs/adr/` and `CHANGELOG.md` - read before proposing architecture changes.
Setting this up on a work repo: `docs/work-repo-setup.md`.

## Current state (2026-10-18)

```
ticket -> setup* -> ignite-brief -> decision gate* -> [HUMAN answers] -> ignite-plan -> ignite-build
       -> tests* + decision tests* (back to build, max 3) -> engineering / security / QA reviews
       -> validate* -> open PR* -> AI review -> [HUMAN merges or closes] -> done          (* = plain code)
```

| Folder | What | Status |
|---|---|---|
| `blueprint/` | Temporal workflow (v2), activities, worker, skills, Docker compose | main path |
| `dashboard/` | RunView: runs, metrics, Answer buttons, New run (reads Temporal) | in use |
| `docs/adr/` | Why it is built this way | 4 ADRs |
| `docs/visuals/` | v1 vs v2 comparison page, dashboard screenshots | reference |
| `trials/` | Devin/Factory trial pack (ticket, scorecard, vendor request) | not run |
| `pipeline/` | First script-based pipeline | superseded, kept for reference |

Run it: see `blueprint/README.md`. UIs: Temporal http://localhost:8233, RunView http://localhost:8765.

Known limits: local `qwen3:14b` is weak (thin plans, ignores instructions), Jira/Chat intake not built, RunView has no
auth, Bedrock path untested, containerised worker not run end to end.

## Evolution of thinking

1. **2026-10-17** - OpenHands GUI (`openhands serve`) installed per the official docs. Single-user conversation UI, no
   runs dashboard, Automations page errored locally.
2. **2026-10-18** - Script pipeline (`pipeline/`) on Ollama via the OpenHands SDK, PR on `jagberg/Me.Compass`. The CLI
   was dropped because it loads ~100 user/public skills into the prompt and the 14B model went off task.
3. **2026-10-18** - Dashboard restyled after Checkr's ForgeView. Custom orchestrator started, then abandoned in favour
   of a third-party base.
4. **2026-10-18** - Platforms surveyed (OpenHands Enterprise, Coder Agents, Multica, n8n, Windmill, AWS ABCA, Devin,
   Factory). No spend allowed, so Devin/Factory trials were prepared but not run.
5. **2026-10-18** - Temporal blueprint (ADR 0001). Human gates became deterministic after the model skipped and then
   ignored decisions (ADR 0002). v2 cut history from 445 to 99 events and added issue/resolution summaries (ADR 0003).
