#!/bin/bash
# Round 5: round 4 (ask + QA loop-back) with Recursive Flint (40B MoE, ~2.5B active) instead of qwen3.8:27b.
B=/private/tmp/claude-501/bake; OHPY=/Users/justingoldberg/.superset/worktrees/Me.OpenHands/charm-odometer-019b9460/blueprint/.venv/bin/python
TICKET='Ticket: average() in calc.py returns the wrong value: average([2, 4, 6]) should be 4. Fix it, following the process in AGENTS.md. Before building, you must ask the product owner how an empty list should behave, using the QUESTION protocol in AGENTS.md.'
ANSWER='return 0 for an empty list (and for a list of only None values); do not raise.'
[ "$(head -1 ~/llm-compare/STATUS.txt)" = "STATE: READY" ] || { echo "gate closed, not starting"; exit 1; }
cp "$(dirname "$0")"/oh_harness.py "$(dirname "$0")"/Modelfile.flint-32k $B/harness/
ollama list | grep -q '^flint:40b' || ollama pull flint:40b || exit 1   # Ollama library tag (benchmarked in ~/llm-compare)
ollama create flint-32k -f $B/harness/Modelfile.flint-32k || exit 1
R=$B/runs/r5-flint; rm -rf $R; mkdir -p $R; git clone -q $B/fixture-qa $R/ws; start=$(date +%s)
BAKE_MODEL=flint-32k $OHPY $B/harness/oh_harness.py $R/ws "$TICKET" "$ANSWER" > $R/harness.log 2>&1
echo "{\"harness\":\"openhands\",\"model\":\"flint-32k (flint:40b)\",\"fixture\":\"fixture-qa\",\"exit\":$?,\"wall_seconds\":$(( $(date +%s) - start ))}" > $R/meta.json
HIDDEN=test_hidden_qa.py python3 -I $B/harness/evaluate.py $R/ws $B > $R/eval.json 2>&1
grep '^RESULT ' $R/harness.log | sed 's/^RESULT //' > $R/result.json
echo "== done: $(cat $R/meta.json) | swap: $(sysctl -n vm.swapusage | awk '{print $6}')"
