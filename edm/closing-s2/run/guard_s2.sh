#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_s2.sh: static checks of everything S2 runs, against the forbidden list and the lessons of S1.  Run before
# staging (stage_s2.sh does).  Exit 0 clean, 1 with the matching lines.
#  1. no reboot / GRUB / kernel build or install / push; no trc_hazard; no clock-gate register; no kreg, kregnow or
#     kpoke write; no /dev/mem write; no git stash/clean/reset; no delete (rm, unlink, os.remove, rmtree)
#  2. no loop that waits: no while/until in the shell scripts, no `while` in the laptop runner, and the runner calls
#     none of the landed fwtask_run.py commands that poll (one_cmd, cmd_run, cmd_pair, cmd_tailpair, cmd_events,
#     wait_state, wait_cmd_clear)
#  3. debugfs only through root: every shell line that names /sys/kernel/debug runs it under `sudo -n`; the runner is
#     started only as `sudo -n python3`; the test-only overrides (S2_MOCK_ROOT, S2_FWTASK_DIR, S2_KMSG, S2_SRCV_PATH,
#     S2_TOOL_TIMEOUT_S, MOCK_*) appear in no script that drives the laptop
#  4. the task sources: no `str` (S2 needs none), ldr only of #81 (CR_TIMER), no write of sa64, sa65 or sa66, sa
#     writes only in pa_write.s, and pa_write only in the table of e2w
#  5. the tables: arm lines from the allow-list, knobs render_pb_pages and hold_recovery only, n at most N_MAX
cd "$(dirname "$0")/.." || exit 1
st=0
bad() { echo "GUARD: $*"; st=1; }
BAD='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make (-j|bzImage|modules)|build-kernel|install-test-kernel|boot-test-kernel|push-gma500|trc_hazard|CLKGATE|clkgate|kregnow|kreg_write|"kreg"|kpoke|/dev/mem|git (stash|clean|reset)|(^|[^a-z_])rm [-a-z]|unlink|os\.remove|rmtree|rmdir'
for f in run/s2.sh run/stage_s2.sh run/freeze_s2.sh; do
	# comment lines may NAME what is forbidden; code may not
	if grep -nE "$BAD" "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "forbidden word in $f"; fi
done
# Python files: guard_py.py checks every line of code (comments and docstrings left out)
PYTHON=${PYTHON:-python3}
if ! "$PYTHON" run/guard_py.py run/s2_run.py gen/s2layout.py gen/gen_s2.py score/score_s2.py; then bad "forbidden word in the Python code"; fi
for f in run/s2.sh run/stage_s2.sh run/freeze_s2.sh; do      # (this guard names the patterns it looks for)
	if grep -nE '(^|[;&|[:space:]])(while|until)[[:space:]]' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "wait loop in $f"; fi
	# 3: debugfs through sudo only
	if grep -n '/sys/kernel/debug' "$f" | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n'; then bad "unprivileged debugfs access in $f"; fi
	if grep -nE 'S2_MOCK_ROOT|S2_FWTASK_DIR|S2_KMSG|S2_SRCV_PATH|S2_TOOL_TIMEOUT_S|MOCK_' "$f"; then bad "a test-only override in $f"; fi
done
if grep -nE '^[[:space:]]*while[[:space:]]' run/s2_run.py; then bad "a while loop in the runner"; fi
if grep -nE 'FR\.(one_cmd|cmd_run|cmd_pair|cmd_tailpair|cmd_events|wait_state|wait_cmd_clear|kreg)' run/s2_run.py; then bad "the runner calls a polling or register-writing command"; fi
if grep -n 's2_run.py' run/s2.sh | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n python3'; then bad "the runner started without sudo -n python3"; fi
# 4: the sources
for f in asm/*.s; do
	if grep -nE '^[[:space:]]+str[[:space:]]' "$f"; then bad "str in $f"; fi
	if grep -nE '^[[:space:]]+ldr[[:space:]]' "$f" | grep -v '#81,'; then bad "ldr of a register other than CR_TIMER in $f"; fi
	if grep -nE '^[[:space:]]+mov sa6[456],' "$f"; then bad "a write of sa64, sa65 or sa66 in $f"; fi
	case "$f" in asm/pa_write.s) ;; *) if grep -nE '^[[:space:]]+mov sa[0-9]+,' "$f"; then bad "an sa write in $f"; fi ;; esac
	if grep -nE 'mov (pa|i)[0-9]+,|mov pclink, r[0-9]+$' "$f" | grep -v 'mov pclink, r30'; then bad "a pa, i or pclink write in $f"; fi
done
# 5: the tables
for f in tables/*.json; do
	s=$(basename "$f" .json)
	if grep -q '"blob": "pa_write"' "$f" && [ "$s" != e2w ]; then bad "pa_write in $f"; fi
	if ! grep -qE '"arm": "(slots=0xf entry=0,1,2,3|slots=0x1 entry=0)"' "$f"; then bad "arm line of $f"; fi
	if grep -nE 'trc|kreg|kpoke|alias_skip|own_' "$f"; then bad "a forbidden knob in $f"; fi
	if grep -oE '"(render_pb_pages|hold_recovery|[a-z_]+)": "(0x30|Y)"' "$f" | grep -vE 'render_pb_pages|hold_recovery'; then bad "an unknown knob in $f"; fi
	n=$(grep -oE '"n": [0-9]+' "$f" | awk '{print $2}' | sort -n | tail -1)
	[ "${n:-0}" -le 1600000 ] || bad "n $n in $f above N_MAX"
done
[ $st = 0 ] && echo "guard: clean"
exit $st
