"""Start a run from a ticket file or text.   .venv/bin/python start.py ../trials/TICKET.md"""
import asyncio, sys
from pathlib import Path

from worker import start

if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent.parent / "trials" / "TICKET.md")
    text = Path(src).read_text() if Path(src).exists() else src
    title = next((l.split(":", 1)[1].strip(" *") for l in text.splitlines() if l.lower().startswith("**title")), text.splitlines()[0][:80])
    print(asyncio.run(start(title, text, source="cli")))
