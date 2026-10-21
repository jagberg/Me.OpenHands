"""Codex SDK harness: start the agent on the ticket, relay QUESTION: lines to a (scripted) human."""
import json, os, sys, time
from openai_codex import ApprovalMode, Codex, CodexConfig, Sandbox


def find_question(final):
    """Exact `QUESTION:` line, else a reply that says it is pausing for the question protocol (same rule for both harnesses)."""
    for line in final.splitlines():
        if "QUESTION:" in line:
            return line.split("QUESTION:", 1)[1].strip()
    low = final.lower()
    if "question" in low and ("paus" in low or "answer and i" in low or "waiting for" in low):
        return final.strip()[-300:]
    return None


ws, ticket, answer = sys.argv[1:4]
B = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = CodexConfig(codex_bin=f"{B}/npm/node_modules/.bin/codex", cwd=ws,
                  env={**os.environ, "CODEX_HOME": f"{B}/codex-home"})
rounds, msg, usage = [], ticket, None
with Codex(cfg) as codex:
    th = codex.thread_start(model="qwen3.8-27b-32k:latest", model_provider="ollama", cwd=ws,
                            sandbox=Sandbox.workspace_write, approval_mode=ApprovalMode.auto_review,
                            config={"model_context_window": 32768})  # Ollama serves 32k; Codex assumed 258k
    for r in range(1, 5):
        t0 = time.time()
        res = th.run(msg)
        final = res.final_response or ""
        usage = res.usage
        q = find_question(final)
        rounds.append({"round": r, "seconds": round(time.time() - t0), "status": str(res.status), "question": q,
                       "final": final[-500:], "items": len(res.items)})
        if not q:
            break
        msg = f"Answer from the product owner: {answer}"
u = usage.model_dump() if hasattr(usage, "model_dump") else str(usage)
print("RESULT " + json.dumps({"harness": "codex", "rounds": rounds, "usage": u}, default=str))
