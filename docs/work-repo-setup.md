# Setting this up on a work repo

A checklist for moving the prototype from the toy repo to a real (work) repository. Read `docs/adr/` first.
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
