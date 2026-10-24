"""Routing and trust-boundary check for the Telegram relay (no network). Run: .venv/bin/python test_telegram.py"""
import shell, telegram

sent, answered = [], []
telegram.send = lambda t: sent.append(t) or 1
telegram.CHAT = "42"
shell.answer = lambda rid, qid, text: answered.append((rid, qid, text))

telegram.open_questions = lambda: [("run-a", {"id": "q1", "tg_msg": 7}), ("run-b", {"id": "q2", "tg_msg": 9})]
telegram.handle({"chat": {"id": 99}, "text": "approve"})
assert not answered and not sent, "messages from other chats are ignored"
telegram.handle({"chat": {"id": 42}, "text": "yes", "reply_to_message": {"message_id": 9}})
assert answered == [("run-b", "q2", "yes")], "a reply answers the question it replies to"
telegram.handle({"chat": {"id": 42}, "text": "hm"})
assert len(answered) == 1 and "Reply to the question" in sent[-1], "a plain message is ambiguous with two open questions"
telegram.open_questions = lambda: [("run-a", {"id": "q1", "tg_msg": 7})]
telegram.handle({"chat": {"id": 42}, "text": "/start"})
assert len(answered) == 1, "bot commands are not answers"
telegram.handle({"chat": {"id": 42}, "text": "Approved."})
assert answered[-1] == ("run-a", "q1", "Approved."), "a plain message answers the only open question"
print("ok")
