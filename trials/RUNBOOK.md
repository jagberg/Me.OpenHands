# Trial runbook (only the steps that need you; everything else is prepared)

Prepared already: private repo https://github.com/jagberg/ai-agent-trial-sandbox (seeded bug), TICKET.md, SCORECARD.md, vendor-requests.md.
Rules: no card, no paid plan. If a signup asks for payment, stop.

## Devin (free tier = local only)
1. https://app.devin.ai/login -> Sign up (GitHub / Google / email). Pick the **Free** plan. If it asks for a card, stop.
2. Download Devin Desktop/CLI, open the trial repo, paste TICKET.md as the task.
3. Score rows 6, 14 in SCORECARD.md. Rows needing Jira/Slack/dashboard stay N/A until the POC.
4. Submit vendor-requests.md at https://devin.ai ("Get a demo") for the cloud/Jira/VPC/Bedrock rows.

## Factory
1. https://app.factory.ai -> Sign up. Check whether it offers a free trial/credits **without a card**. If not, stop (pricing page shows $20/mo minimum).
2. If free: `curl -fsSL https://app.factory.ai/cli | sh`, open the trial repo, paste TICKET.md.
3. BYOK/Bedrock: see https://docs.factory.com/cli/byok/overview (`bedrock` block). Test only with a spend-capped AWS identity, never your main one.
4. Submit vendor-requests.md via "Contact sales" at https://factory.com for Jira/Slack/dashboard/on-prem rows.

## Safety
- Grant GitHub access to the trial repo only (repo-scoped install, not "all repositories").
- Never paste real company code, tickets or keys. Revoke the GitHub app and delete the repo when finished.
