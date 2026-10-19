#!/bin/bash
# Same fixture, ticket and scripted human for both harnesses; one after the other (one local GPU).
B=/private/tmp/claude-501/bake; OHPY=/Users/justingoldberg/.superset/worktrees/Me.OpenHands/charm-odometer-019b9460/blueprint/.venv/bin/python
TICKET='Ticket: average() in calc.py returns the wrong value: average([2, 4, 6]) should be 4. Fix it, following the process in AGENTS.md.'
ANSWER='return 0 for an empty list (and for a list of only None values); do not raise.'
for h in openhands codex; do
  R=$B/runs/$h; rm -rf $R; mkdir -p $R; git clone -q $B/fixture $R/ws
  start=$(date +%s)
  if [ $h = openhands ]; then $OHPY $B/harness/oh_harness.py $R/ws "$TICKET" "$ANSWER" > $R/harness.log 2>&1
  else $B/codex-venv/bin/python $B/harness/codex_harness.py $R/ws "$TICKET" "$ANSWER" > $R/harness.log 2>&1; fi
  echo "{\"harness\":\"$h\",\"exit\":$?,\"wall_seconds\":$(( $(date +%s) - start ))}" > $R/meta.json
  python3 -I $B/harness/evaluate.py $R/ws $B > $R/eval.json 2>&1
  grep '^RESULT ' $R/harness.log | sed 's/^RESULT //' > $R/result.json
  echo "== $h done: $(cat $R/meta.json)"
done
