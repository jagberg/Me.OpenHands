# ADR 0003: Run state lives only in Temporal; big workflow changes ship as a new workflow type

- Status: accepted
- Date: 2026-10-18

## Context

Blueprint v1 (`blueprint/workflow_v1.py`, type `IgniteBlueprint`) wrote run state to `runs/<id>/run.json` through a
`write_run` activity after every step, checked for agent questions in a separate activity after every stage, and polled
the PR state every 60 seconds. Measured on run `ignite-20261018-210055`: 445 history events, 60 activities, of which
only 14 were real work (23 `write_run`, 16 `pr_state`, 7 `harvest_question`). Waiting a day for PR review would add
roughly 11,500 more events (estimate: about 8 events per poll).

## Decision

Blueprint v2 (`blueprint/workflow.py`, type `IgniteBlueprintV2`):
- Keeps state in workflow memory. The dashboard reads it with the `state` query while running and from the workflow
  result once finished (`blueprint/worker.py: runs()`). No `write_run` activity.
- Folds the question check into the `agent_stage` activity's return value.
- Polls the PR with backoff (1, 2, 4, 8, then every 15 minutes).
- Labels every activity and timer (`summary=`) and publishes a live Markdown summary with
  `workflow.set_current_details` (issue, decisions, resolution, metrics).

Result on run `ignite-20261018-213144`: 99 events, 15 activities.

**Versioning rule:** small shape changes use `workflow.patched("<name>")`; large ones ship as a new workflow type and the
old one stays registered, frozen, until its runs finish. Without either, in-flight runs fail replay with a
nondeterminism error.

## Alternatives considered

- **Keep run.json files** - simple to read, but doubled the history and duplicated state outside Temporal.
- **Local activities for saves** - fewer events than activities, still noise and still a second copy of state.
- **GitHub webhook to signal on merge** - the right production answer (zero polling) but GitHub cannot reach a laptop;
  deferred to the hosted deployment.
- **Patch every change into one workflow type** - unreadable after a few versions.

## Consequences

- The dashboard needs the worker running to query live runs (finished results are cached).
- `workflow_v1.py`, `write_run` and `harvest_question` stay until no `IgniteBlueprint` runs are open, then can be deleted
  (check: `temporal workflow list -q 'WorkflowType="IgniteBlueprint" AND ExecutionStatus="Running"'`).
- Merge detection can lag up to 15 minutes until the webhook exists.
