# Running the factory on a work laptop, against a work repo

Current guide (2026-10-25, ADR 0005 factory in `factory/`). The earlier Temporal-era checklist is kept at the bottom.

## What you get
Brief in RunView (or the API) -> the OpenHands agent runs the ignite process in Docker on the local model -> it asks you
questions (RunView or Telegram) -> host checks -> a PR on your repo's default branch -> you review and merge.
Nothing leaves the laptop except git pushes to your repo (and Telegram messages, if you enable it).

## Steps
```bash
git clone https://github.com/jagberg/Me.OpenHands.git && cd Me.OpenHands
factory/bootstrap.sh --repo <org>/<repo> [--langfuse]
```
`bootstrap.sh` checks before it acts and can be re-run. It needs: Docker Desktop, Ollama, `gh`, `uv`, git (it tells
you what to `brew install`), about 20 GB free RAM for qwen3.8:27b, `gh auth login` with access to the repo, and the
CompareClub ignite plugin installed in Claude Code. It pulls the agent image, builds the 32k model, makes the venv and
writes two things for you to edit:

| File | Edit |
|---|---|
| `~/.config/factory/target.json` | `test_cmd`: host command that runs the repo's tests (a pre-PR check); `protected`: files the agent must not change (glob names, e.g. `"*.sql"`) |
| `~/.config/factory/overlay/knowledge/project.md` | What the repo is, the test command inside the container, protected files, PRD sections that do not apply |

Then `cd factory && caffeinate -dimsu .venv/bin/python app.py` and open http://127.0.0.1:8766. Stay on mains power.

## How the process gets into a repo that doesn't have it
The overlay (`~/.config/factory/overlay`, from `factory/overlay-template`) holds `AGENTS.md`, `knowledge/`, the
`qa-review` and OpenSpec skills and `openspec/config.yaml`. The shell copies it, and the ignite skills, into each run's
clone and lists every file in `.git/info/exclude`, so none of it reaches the PR and nothing is committed to the work
repo to set it up. If the repo already has one of those files, the run stops and names it: drop it from the overlay.

## Decide before the first real run
- **What the PR contains.** The agent's outputs are committed: `intent/<feature>/brief.md`, `openspec/changes/...`,
  `.ignite/log.md` and `.ignite/qa.md`, plus the code. Keep them (reviewable trail) or add them to the overlay's exclude
  list later.
- **Branch protection** on the repo (required review and CI) so the factory can open but never merge a PR.
- **Data:** code and briefs go only to the local model. Langfuse is local. Check with security before enabling
  Telegram (a personal app) or sending metrics to DX.
- **Test command in the container.** The agent runs tests inside `agent-server` (Python 3.13 + Node). A repo that
  needs other services (databases, private package registries) needs those reachable from the container, or a
  narrower test command.

## Known limits
One run at a time; a crash or sleep mid-turn fails the run (retry from RunView/API); slow on the local model (30-45 min
for a small function); stage boundaries come from the agent's `.ignite/log.md` lines. Bedrock: untested
(`LLM_MODEL=bedrock/...`, `LLM_BASE_URL=` empty, AWS credentials from SSO).

---

## Earlier checklist (SUPERSEDED 2026-10-25)

**Superseded by:** the guide above. **Why it changed:** ADR 0005 replaced the Temporal blueprint with the OpenHands
shell in `factory/`; steps 1-2 and 5 below describe `blueprint/`, which is no longer the main path.

### Setting this up on a work repo (2026-10-18)

A checklist for moving the prototype from the toy repo to a real (work) repository. Read `docs/adr/` first.

> **Under review (2026-10-19):** this checklist assumes the coded Temporal blueprint (ADR 0001). ADR 0005 (proposed)
> would replace it with a prompt-defined process in an agent harness; steps 4 (skills), 6 (intake) and 7 (dashboard)
> carry over, steps 1-2 and 5 would change. Check ADR 0005's status before following this.
Written 2026-10-18; items marked **untested** were not exercised in the prototype.

## 0. Decide before you start

| Question | Prototype answer | Work repo needs |
|---|---|---|
| Where does it run? | Laptop: Temporal in Docker, worker on host | A host or VM in the company network; Temporal + worker containers |
| Which model? | Ollama `qwen3:14b` | AWS Bedrock in the company account (**untested**, see step 3) |
| Who can see code and prompts? | Only this laptop | Code goes to the model provider; Bedrock keeps it in your AWS account |
| GitHub access | Your personal `gh` login | A dedicated GitHub App or fine-grained token scoped to the target repo(s) only |
| Who answers decisions? | You, in RunView | Named people, notified in Google Chat or Jira (not built yet, step 6) |
| Data rules | Toy code only | Check with security: no customer data or secrets in tickets, prompts or logs |

## 1. Copy the code

Copy `blueprint/` and `dashboard/` into a new internal repo (not the target product repo). Keep `docs/adr/` and
`CHANGELOG.md` so the reasoning travels with it. Do not copy `runs/` or `pipeline/`.

## 2. Point it at the target repo

In `blueprint/worker.py`, `DEFAULT_CFG` (or pass `cfg` per run from the intake):

```python
{"repo": "<org>/<repo>", "workdir": ".",              # subfolder if the change is scoped
 "test_cmd": "<the repo's real test command>",        # must run headless in the worker image
 "protected": ["<files agents must never edit>"],     # e.g. existing tests, migrations, CI config
 "throwaway_base": False}                             # True only for experiments; False targets the default branch
```

With `throwaway_base: False` the PR targets the repo's default branch. The final gate is still a human merge.
Add branch protection on the target repo (required review, required CI) so the agent cannot merge.

## 3. Switch the model to Bedrock (**untested**)

Environment for the worker:

```bash
LLM_MODEL=bedrock/<model-id>      # e.g. a Claude model enabled in your Bedrock account
LLM_BASE_URL=                     # empty: litellm uses Bedrock, not Ollama
AWS_REGION=<region>               # credentials from the instance role / SSO profile, never a key in a file
```

Then run one ticket end to end and confirm tokens and cost appear per stage in RunView before trusting it.
Raise `MAX_ACTIVITIES` once the model can serve parallel runs (local Ollama needed 1-2).

## 4. Replace the dummy skills

`blueprint/skills/*.md` are placeholders. Replace with the real `ignite:brief`, `ignite:plan`, `ignite:build` and the
team's engineering, security and QA review skills. Keep two contracts the workflow relies on:
- Reviews write `.ignite/<name>.md` with a `PASS` or `CONCERNS` verdict (parsed into the resolution summary).
- Build writes `test_decisions.py` with one test per human decision (enforced, ADR 0002).

## 5. Run Temporal and the worker as services

- Temporal: `blueprint/docker-compose.yml` uses the dev server with SQLite in a Docker volume. Fine for a pilot.
  For production, use Temporal's Postgres-backed deployment or Temporal Cloud (paid).
- Worker: `docker compose --profile worker up -d --build` with `GH_TOKEN` (repo-scoped) and the Bedrock env in `.env`
  (never committed). **Untested end to end** in the prototype: the image builds and imports cleanly only.

## 6. Intake and notifications (not built)

- **Jira**: a Jira Automation rule (label added or ticket assigned) calls `POST /api/briefs` with `{title, brief, source}`.
- **Decisions**: when a run asks a question, post it to Google Chat (incoming webhook) or as a Jira comment with a link to
  RunView; the answer comes back through `POST /api/runs/<id>/answer` or the RunView Answer button.
- **Merge**: replace PR polling with a GitHub webhook that sends a Temporal signal (ADR 0003).

## 7. Lock down the dashboard

RunView has no authentication and binds to 127.0.0.1. Before anyone else uses it: put it behind the company SSO proxy
(or add auth), serve it over HTTPS, and restrict who can answer decisions and start runs.

## 8. Pilot checklist

- [ ] One ticket end to end on the work repo with Bedrock
- [ ] A blocking decision answered by someone other than the author
- [ ] Branch protection confirmed: the agent cannot merge
- [ ] Metrics visible per stage (tokens, time, cost)
- [ ] Security sign-off on data sent to the model and stored in Temporal history (prompts and diffs are in the history)

## Visuals to reuse

`docs/visuals/` has the v1 vs v2 comparison page and screenshots of both dashboards for explaining the setup.
