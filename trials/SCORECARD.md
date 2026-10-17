# Scorecard: Devin vs Factory (fill in during trial; "doc claim" = what vendor docs say, unverified)

Score each: PASS / PARTIAL / FAIL / N/A (could not test at $0). Note evidence (link/screenshot).

| # | Requirement | Devin doc claim | Factory doc claim | Devin | Factory |
|---|---|---|---|---|---|
| 1 | Takes brief from Jira | Jira **Cloud** only: assign to Devin, @mention, or `devin` label | Jira/Slack delegations (third-party source) | | |
| 2 | Takes brief from chat | Slack / Teams | Slack / Teams | | |
| 3 | Runs OUR stages (ignite brief/plan/build, eng/sec/qa) as gated steps with our skills | unknown | unknown (Droid has plan/build/validate; custom skills?) | | |
| 4 | Asks a human a question in Jira/chat, then continues | Rovo agent panel shows question; reply continues session | unknown | | |
| 5 | Keeps working while waiting (non-blocking) | unknown | unknown | | |
| 6 | Raises PR | yes | yes | | |
| 7 | AI code review on the PR | Devin Review | unconfirmed | | |
| 8 | Notifies on chat when ready | Slack PR status | Slack | | |
| 9 | Dashboard: current state + metrics (tokens/cost/time/status) | PR metrics view; admin analytics on Teams+ | Analytics + Mission Control (marketing page) | | |
| 10 | Human final review/merge gate (agent cannot merge) | | | | |
| 11 | Deploy where we like / secure hosted | Enterprise: VPC / dedicated | Enterprise: on-prem options | | |
| 12 | LLM via AWS Bedrock | not found | Droid CLI BYOK documents a `bedrock` block (plan gating unstated) | | |
| 13 | Cost for 1 run of this ticket | | | | |
| 14 | Fix quality: minimal diff, test file untouched, stale `# bug` comment removed | | | | |

Reference result (OpenHands + local qwen3-14b): 6 stages, ~4 min, PR #1 on jagberg/Me.Compass, $0.

## $0 reality check (from vendor pricing pages, 2026-10-18)
- Devin: Free plan = Devin Desktop/CLI with light quota. **Cloud agents (Devin Cloud) start at Pro $20/mo.** Trials are "promotional", decided at checkout.
- Factory: pricing page lists only paid plans (Pro $20/mo up). No free tier or trial stated.
- So #1-#2, #4-#9 (Jira/Slack/dashboard/review) cannot be confirmed at $0 without a vendor-run demo/POC. #6, #14 can be tested locally on the free Devin tier.
