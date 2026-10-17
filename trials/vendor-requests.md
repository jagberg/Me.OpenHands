# Demo / POC request (send via each vendor's "Get a demo" / "Contact sales" form; free, no card)

Subject: POC request - autonomous coding agent on our AI-DLC (no spend before POC)

Hi, we are evaluating {Devin | Factory} for an agent workflow where the agent takes a Jira/chat brief, runs
our own staged process (brief -> plan -> build -> engineering/security/QA review), asks a named person a
question in Jira/chat when it needs a decision and keeps working, raises a PR, gets an AI review, then a human
reviews and merges. We would like a time-boxed POC (free) on a private toy repo, covering:

1. Can the agent run our own stages/skills as gated steps (we have markdown skills, e.g. ignite:brief, ignite:plan)?
2. Agent asks a human a question in Jira (Cloud) or Google Chat/Slack, then continues. Blocking and non-blocking.
3. Dashboard: current state of each agent run and metrics (time, tokens/cost, status, PR state). Org-wide, per run.
4. LLM via AWS Bedrock (or our own endpoint). Which plans?
5. Deployment: self-hosted/VPC/on-prem options and what runs where (is code or telemetry sent out?).
6. Guardrails: can the agent merge? Autonomy levels, deny-lists, audit log.
7. Pricing for ~20 tickets/month at the tier that includes the above, and whether a paid trial needs a card.

Test repo: private GitHub repo, toy code, no company data. We will grant access scoped to that repo only.
