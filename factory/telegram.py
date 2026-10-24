"""Telegram relay: the agent's questions go to your chat; your reply is the answer. Stdlib only, long polling (no
public URL). Config lives in ~/.config/factory/telegram.env (chmod 600, you write it):
    TELEGRAM_BOT_TOKEN=...      from @BotFather (a new bot: two pollers on one bot conflict)
    TELEGRAM_CHAT_ID=...        only this chat may answer; find it with `python telegram.py chat-id` after messaging the bot
Reply to a question message to answer it; a plain message answers the only open question if there is exactly one.
"""
import json, sys, threading, time, urllib.request
from pathlib import Path

import shell

ENV = Path.home() / ".config" / "factory" / "telegram.env"


def config():
    if not ENV.exists():
        return {}
    return dict(l.split("=", 1) for l in ENV.read_text().split() if "=" in l)


CFG = config()
API = f"https://api.telegram.org/bot{CFG.get('TELEGRAM_BOT_TOKEN', '')}/"
CHAT = CFG.get("TELEGRAM_CHAT_ID", "")


def call(method, **params):
    req = urllib.request.Request(API + method, json.dumps(params).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["result"]


def send(text):
    return call("sendMessage", chat_id=CHAT, text=text[:4000])["message_id"]


def notify(rid, kind, msg):
    """shell.event hook. Runs in the worker thread; a Telegram outage must not fail the run."""
    try:
        r = shell.load(rid)
        if kind == "question":
            q = next(q for q in reversed(r["questions"]) if q["status"] == "open")
            context = r["turns"][-1]["final"].split("QUESTION:")[0].strip()[-2500:] if r.get("turns") else ""
            mid = send(f"❓ {r['title']} ({rid}, {q['id']})\n\n{context}\n\n{q['text']}\n\nReply to this message to answer.")
            shell.update(rid, lambda r: next(x for x in r["questions"] if x["id"] == q["id"]).update(tg_msg=mid))
        elif kind == "pr_opened":
            send(f"✅ {r['title']} ({rid})\nPR ready for your review: {msg}")
        elif kind == "failed":
            send(f"❌ {r['title']} ({rid}) failed: {msg}")
    except Exception as e:
        print("telegram notify failed:", e, file=sys.stderr)


def open_questions():
    return [(r["id"], q) for r in shell.runs() for q in r["questions"] if q["status"] == "open"]


def handle(m):
    if str(m.get("chat", {}).get("id")) != CHAT or not m.get("text"):
        return  # trust boundary: ignore everyone but the configured chat
    if m["text"].startswith("/"):
        return  # bot commands (/start) are not answers; one answered a design-review gate on 2026-10-24
    open_q = open_questions()
    to = (m.get("reply_to_message") or {}).get("message_id")
    hit = [x for x in open_q if x[1].get("tg_msg") == to] if to else (open_q if len(open_q) == 1 else [])
    if not hit:
        return send("No matching open question. Reply to the question message." if open_q else "No open questions.")
    rid, q = hit[0]
    shell.answer(rid, q["id"], m["text"])
    send(f"Got it. {rid} resumes.")


def poll():
    pending = call("getUpdates", offset=-1, timeout=0)  # skip messages sent while the relay was down: stale, not answers
    offset = pending[-1]["update_id"] + 1 if pending else None
    while True:
        try:
            for u in call("getUpdates", timeout=50, offset=offset, allowed_updates=["message"]):
                offset = u["update_id"] + 1
                if "message" in u:
                    handle(u["message"])
        except Exception as e:
            print("telegram poll error:", e, file=sys.stderr)
            time.sleep(10)


def start():
    """Called by app.py. No config, no relay (RunView still works)."""
    if not (CFG.get("TELEGRAM_BOT_TOKEN") and CHAT):
        return False
    shell.NOTIFY.append(notify)
    threading.Thread(target=poll, daemon=True).start()
    return True


if __name__ == "__main__" and sys.argv[1:] == ["chat-id"]:
    for u in call("getUpdates"):  # message the bot first; prints chat ids only
        c = u.get("message", {}).get("chat", {})
        print(c.get("id"), c.get("type"), c.get("username") or c.get("title"))
