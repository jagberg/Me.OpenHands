"""Codex SDK harness: start the agent on the ticket, relay QUESTION: lines to a (scripted) human."""
import json, os, sys, time
from openai_codex import ApprovalMode, Codex, CodexConfig, Sandbox

ws, ticket, answer = sys.argv[1:4]
B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = CodexConfig(codex_bin=f"{B}/npm/node_modules/.bin/codex", cwd=ws,
                  env={**os.environ, "CODEX_HOME": f"{B}/codex-home"})
rounds, msg, usage = [], ticket, None
with Codex(cfg) as codex:
    th = codex.thread_start(model="qwen3-14b-oh:latest", model_provider="ollama", cwd=ws,
                            sandbox=Sandbox.workspace_write, approval_mode=ApprovalMode.auto_review,
                            config={"model_context_window": 32768})  # Ollama serves 32k; Codex assumed 258k
    for r in range(1, 5):
        t0 = time.time()
        res = th.run(msg)
        final = res.final_response or ""
        usage = res.usage
        q = next((l.split("QUESTION:", 1)[1].strip() for l in final.splitlines() if "QUESTION:" in l), None)
        rounds.append({"round": r, "seconds": round(time.time() - t0), "status": str(res.status), "question": q,
                       "final": final[-500:], "items": len(res.items)})
        if not q:
            break
        msg = f"Answer from the product owner: {answer}"
u = usage.model_dump() if hasattr(usage, "model_dump") else str(usage)
print("RESULT " + json.dumps({"harness": "codex", "rounds": rounds, "usage": u}, default=str))
