#!/bin/bash
# Round 4: QA loop-back. Requirement (round to 2 dp) only in qa/checklist.md; brief/plan told not to read qa/.
B=/private/tmp/claude-501/bake; OHPY=/Users/justingoldberg/.superset/worktrees/Me.OpenHands/charm-odometer-019b9460/blueprint/.venv/bin/python
TICKET='Ticket: average() in calc.py returns the wrong value: average([2, 4, 6]) should be 4. Fix it, following the process in AGENTS.md. Before building, you must ask the product owner how an empty list should behave, using the QUESTION protocol in AGENTS.md.'
ANSWER='return 0 for an empty list (and for a list of only None values); do not raise.'
[ "$(head -1 ~/llm-compare/STATUS.txt)" = "STATE: READY" ] || { echo "gate closed, not starting"; exit 1; }
R=$B/runs/r4-openhands; rm -rf $R; mkdir -p $R; git clone -q $B/fixture-qa $R/ws; start=$(date +%s)
$OHPY $B/harness/oh_harness.py $R/ws "$TICKET" "$ANSWER" > $R/harness.log 2>&1
echo "{\"harness\":\"openhands\",\"model\":\"qwen3.8-27b-32k\",\"fixture\":\"fixture-qa\",\"exit\":$?,\"wall_seconds\":$(( $(date +%s) - start ))}" > $R/meta.json
HIDDEN=test_hidden_qa.py python3 -I $B/harness/evaluate.py $R/ws $B > $R/eval.json 2>&1
grep '^RESULT ' $R/harness.log | sed 's/^RESULT //' > $R/result.json
echo "== done: $(cat $R/meta.json) | swap: $(sysctl -n vm.swapusage | awk '{print $6}')"
