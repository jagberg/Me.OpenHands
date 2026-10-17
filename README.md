# Me.OpenHands

Local OpenHands eval: Ollama (`qwen3-14b-oh`, qwen3:14b with 32k ctx) -> ignite stages -> fix -> PR on Me.Compass -> dashboard.

```bash
~/.local/share/uv/tools/openhands/bin/python pipeline/run.py [--no-pr]   # one run (~4 min)
python3 dashboard/server.py                                               # http://localhost:8765
```
Skills are dummy prompts in `pipeline/skills/`. The SDK is used (not the CLI) so user/public skills are not loaded into the prompt.
PRs target a throwaway base branch `openhands-eval/base-<id>`; Me.Compass master is never touched.
