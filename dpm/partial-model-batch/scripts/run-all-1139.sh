#!/bin/bash
# 11.39 run-all-1139.sh: the order of the batch (plan.md section 5). Every step is its own run_table.sh
# run with its own health check before and after; a step that stops itself (three failed recoveries)
# stops the batch: read the kernel log (journalctl -k) before starting another. The safe tables first,
# the unmodified tool only; then the steps that need the changed tool (the knob "new": skipped with a
# line when ~/sgxfive-test-1139 is absent); the risky steps last, one at a time.
D=$(cd "$(dirname "$0")" && pwd)
set -u
step() { echo; echo "######## $*"; "$D/run_table.sh" "$@" || { echo "######## stopped at: $*"; exit 1; }; }
# part A: no tool change, no kernel change
step free safe
step trig safe
step state safe
step depth safe
step wide safe
step owner safe          # ow-keep-* run on the unmodified tool; the cases with knob "new" are skipped
# part B: the changed tool (T2, T3, T4); skipped one by one without it
# (owner safe above already ran them when ~/sgxfive-test-1139 exists)
# risky, last
step trig risky          # the threshold pokes (pb:11)
step owner risky         # junk in the state page between the kicks; closes without keep
step wide risky          # the hangs, with hold_recovery on the first three
echo; echo "######## batch done"
