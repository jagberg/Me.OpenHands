# Visuals and dashboards

| File | What it shows |
|---|---|
| `blueprint-v1-vs-v2.html` | Comparison page: history size, waiting cost, lifecycle, summaries, the two dashboards. Open in a browser. Also published (private) at https://claude.ai/artifact/T9ynthgNQwziayQutNfxFM |
| `setup-steps.html` | Conceptual view (six layers), logical view (what is configured in each component, how they connect), then setup in 8 steps: Temporal, worker and model, starting a run, skills, prompt layers, metrics, human answers, PR. Open in a browser; diagrams render via the Mermaid script from jsDelivr (needs internet). Published (private) at https://claude.ai/artifact/PXfWScVJxBcLf1he7k6AFR |
| `screens/temporal-workflow-list.png` | Temporal UI (stock) - workflow list |
| `screens/temporal-user-metadata.png` | Temporal UI - User Metadata tab: summary, live issue/decisions/resolution (v2) |
| `screens/temporal-timeline.png` | Temporal UI - Timeline: labelled stages and the human `answer` signal (v2) |
| `screens/runview-awaiting-decision.png` | RunView - run parked on a blocking question with the Answer box |
| `screens/runview-run-detail.png` | RunView - run detail: issue/resolution, metrics, answered decision, stage table |
| `screens/runview-forgeview-style-v0.png` | RunView first layout after the ForgeView reference (script pipeline runs) |
| `screens/openhands-gui-llm-profile.png` | OpenHands GUI - LLM profile pointed at local Ollama, no key |
| `screens/openhands-gui-conversation.png` | OpenHands GUI - single conversation fixing the sandbox bug |

Screenshots taken 2026-10-18 from the local prototype; data is the toy `average()` ticket only.

Inspiration (not stored here): a screenshot of ForgeView, Checkr's AgentForge runs page, and Luca Bonmassar's LinkedIn
post on AI-assisted / AI-first / AI-native process maturity.
