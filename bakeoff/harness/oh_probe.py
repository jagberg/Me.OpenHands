import os, sys
os.environ.setdefault("OPENHANDS_SUPPRESS_BANNER", "1")
from openhands.sdk import LLM, Agent, AgentContext, Conversation
from openhands.sdk.event import ActionEvent, MessageEvent
from openhands.sdk.skills import load_project_skills
from openhands.tools.preset.default import get_default_tools
ws, variant = sys.argv[1], sys.argv[2]
kw = dict(model="ollama_chat/qwen3-14b-oh", base_url="http://localhost:11434", api_key="ollama", max_input_tokens=32768,
          max_output_tokens=4096, timeout=900, native_tool_calling=True, litellm_extra_body={"options": {"num_ctx": 32768}}, usage_id="agent")
if variant != "reasoning_on":
    kw["reasoning_effort"] = "none"
skills = [] if variant == "no_skills" else load_project_skills(ws)
agent = Agent(llm=LLM(**kw), tools=get_default_tools(enable_browser=False)[:2],
              agent_context=AgentContext(skills=skills, load_user_skills=False, load_public_skills=False))
ev = []
conv = Conversation(agent=agent, workspace=ws, visualizer=None, max_iteration_per_run=3, callbacks=[ev.append])
conv.send_message("Ticket: average() in calc.py returns the wrong value. Fix it, following the process in AGENTS.md.")
try: conv.run()
except Exception as e: print("run error", e)
acts = [e.tool_name for e in ev if isinstance(e, ActionEvent)]
empties = sum(1 for e in ev if isinstance(e, MessageEvent) and e.source == "agent" and not "".join(getattr(c, "text", "") for c in e.llm_message.content).strip())
print(f"PROBE {variant}: actions={acts} empty_agent_msgs={empties}")
