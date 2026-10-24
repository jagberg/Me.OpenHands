"""OpenHands SDK harness: start the agent on the ticket, relay QUESTION: lines to a (scripted) human."""
import json, os, sys, time
os.environ.setdefault("OPENHANDS_SUPPRESS_BANNER", "1")
from openhands.sdk import LLM, Agent, AgentContext, Conversation
from openhands.sdk.conversation.response_utils import get_agent_final_response
from openhands.sdk.skills import load_project_skills
from openhands.tools.preset.default import get_default_tools


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
llm = LLM(model="ollama_chat/" + os.environ.get("BAKE_MODEL", "qwen3.8-27b-32k"), base_url="http://localhost:11434", api_key="ollama",  # reasoning left on: with skills + reasoning off, qwen3 returned empty replies
          max_input_tokens=32768, max_output_tokens=8192, timeout=900, native_tool_calling=True,
          litellm_extra_body={"options": {"num_ctx": 32768}}, usage_id="agent")
skills = load_project_skills(ws)  # repo .agents/skills + AGENTS.md
agent = Agent(llm=llm, tools=get_default_tools(enable_browser=False)[:2],
              agent_context=AgentContext(skills=skills, load_user_skills=False, load_public_skills=False))
conv = Conversation(agent=agent, workspace=ws, visualizer=None, max_iteration_per_run=80,
                    persistence_dir=os.path.join(os.path.dirname(ws), "state"))
rounds, msg = [], ticket
for r in range(1, 5):
    t0 = time.time()
    conv.send_message(msg)
    conv.run()
    final = get_agent_final_response(conv.state.events) or ""
    q = find_question(final)
    rounds.append({"round": r, "seconds": round(time.time() - t0), "question": q, "final": final[-500:]})
    if not q:
        break
    msg = f"Answer from the product owner: {answer}"
m = conv.conversation_stats.get_combined_metrics()
u = m.accumulated_token_usage
print("RESULT " + json.dumps({"harness": "openhands", "skills_loaded": [s.name for s in skills], "rounds": rounds,
                              "llm_calls": len(m.response_latencies), "prompt_tokens": u.prompt_tokens,
                              "completion_tokens": u.completion_tokens}))
