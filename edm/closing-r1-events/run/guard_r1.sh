#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_r1.sh: static checks of everything R1-events runs, against the forbidden list and the lessons of S1, S2 and S2b.  Run
# before staging (stage_r1.sh does).  Exit 0 clean, 1 with the matching lines.
#  1. no reboot / GRUB / kernel build or install / push; no trc_hazard; no clock-gate register; no kreg, kregnow or kpoke
#     write; no /dev/mem write; no git stash/clean/reset; no delete (rm, unlink, os.remove, rmtree)
#  2. no loop that waits: no while/until in the shell scripts, no `while` in the laptop runner, and the runner calls none of
#     the landed fwtask_run.py commands that poll (one_cmd, cmd_run, cmd_pair, cmd_tailpair, cmd_events, wait_state,
#     wait_cmd_clear) or write registers (kreg)
#  3. debugfs only through root: every shell line that names /sys/kernel/debug runs it under `sudo -n`; the runner is started
#     only as `sudo -n python3`; the test-only overrides (R1_MOCK_ROOT, R1_FWTASK_DIR, R1_KMSG, R1_SRCV_PATH, R1_DEBUGFS,
#     MOCK_) appear in no script that drives the laptop; no `set -f` (it breaks the globs that keep dumps)
#  4. /dev/kmsg is opened with os.open(path, os.O_WRONLY | os.O_APPEND), never Python's "a" mode (it seeks: EINVAL)
#  5. the task sources: no `str`, ldr only of #81 (CR_TIMER), no sa write, no pa, i or pclink write other than the tail call
#     (ring_e1.s only); the loop programs (asm/loop-*.s) have no str, no ldr and no register-space access
#  6. the tables: arm line from the allow-list, knobs render_pb_pages and hold_recovery only, kick counts within the limits, no
#     value in a tool argument that names a register write
cd "$(dirname "$0")/.." || exit 1
st=0
bad() { echo "GUARD: $*"; st=1; }
BAD='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make (-j|bzImage|modules)|build-kernel|install-test-kernel|boot-test-kernel|push-gma500|trc_hazard|CLKGATE|clkgate|kregnow|kreg_write|"kreg"|kpoke|/dev/mem|git (stash|clean|reset)|(^|[^a-z_])rm [-a-z]|unlink|os\.remove|rmtree|rmdir'
SH="run/r1.sh run/stage_r1.sh run/freeze_r1.sh run/health_remote.sh"
for f in $SH; do
	# comment lines may NAME what is forbidden; code may not
	if grep -nE "$BAD" "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "forbidden word in $f"; fi
done
# Python files: guard_py.py checks every line of code (comments and docstrings left out)
PYTHON=${PYTHON:-python3}
if ! "$PYTHON" run/guard_py.py run/r1_run.py gen/r1layout.py gen/gen_r1.py score/score_r1.py; then bad "forbidden word in the Python code"; fi
for f in $SH; do      # (this guard names the patterns it looks for)
	if grep -nE '(^|[;&|[:space:]])(while|until)[[:space:]]' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "wait loop in $f"; fi
	# 3: debugfs through sudo only
	if grep -n '/sys/kernel/debug' "$f" | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n'; then bad "unprivileged debugfs access in $f"; fi
	if grep -nE 'R1_MOCK_ROOT|R1_FWTASK_DIR|R1_KMSG|R1_SRCV_PATH|R1_DEBUGFS|R1_TOOL_TIMEOUT_S|MOCK_' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "a test-only override in $f"; fi
	if grep -nE '(^|[;&|[:space:]])set[[:space:]]+-[a-z]*f' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "set -f in $f (breaks the globs that keep dumps)"; fi
done
if grep -nE '^[[:space:]]*while[[:space:]]' run/r1_run.py; then bad "a while loop in the runner"; fi
if grep -nE 'FR\.(one_cmd|cmd_run|cmd_pair|cmd_tailpair|cmd_events|wait_state|wait_cmd_clear|kreg)' run/r1_run.py; then bad "the runner calls a polling or register-writing command"; fi
if grep -n 'r1_run.py' run/r1.sh | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n python3'; then bad "the runner started without sudo -n python3"; fi
# 4: the kernel-log marker
grep -q 'os.open(KMSG, os.O_WRONLY | os.O_APPEND)' run/r1_run.py || bad "the kmsg marker is not written with os.open(..., os.O_WRONLY | os.O_APPEND)"
if grep -nE 'open\(KMSG|open\("/dev/kmsg"' run/r1_run.py | grep -v 'os\.open'; then bad "the kernel log opened in a Python mode (EINVAL on the laptop)"; fi
# 5: the sources
for f in asm/*.s; do
	if grep -nE '^[[:space:]]*str[[:space:]]' "$f"; then bad "str in $f"; fi
	case "$f" in
	asm/ring_e1.s)
		if grep -nE '^[[:space:]]+ldr[[:space:]]' "$f" | grep -v '#81,'; then bad "ldr of a register other than CR_TIMER in $f"; fi
		if grep -nE '^[[:space:]]+mov sa[0-9]+,' "$f"; then bad "an sa write in $f"; fi
		if grep -nE 'mov (pa|i)[0-9]+,|mov pclink, r[0-9]+$' "$f" | grep -v 'mov pclink, r30'; then bad "a pa, i or pclink write in $f"; fi ;;
	asm/loop-*.s)
		if grep -nE '^[[:space:]]*(ldr|emit|lock|release)' "$f"; then bad "a register or event instruction in $f"; fi ;;
	*) bad "an unknown source: $f" ;;
	esac
done
# 6: the tables
for f in tables/*.json; do
	if ! grep -qE '"arm": (null|"slots=0xf entry=0,1,2,3")' "$f"; then bad "arm line of $f"; fi
	if grep -nE 'trc|kreg|kpoke|alias_skip|own_|"blob": "(pa_|ring_hold)' "$f"; then bad "a forbidden word in $f"; fi
	if grep -oE '"(render_pb_pages|hold_recovery)": "[^"]*"' "$f" | grep -vE '"render_pb_pages": "0x(30|320|3a0|422)"|"hold_recovery": "Y"'; then bad "a knob value outside the allow-list in $f"; fi
	n=$(grep -oE '"warm": [0-9]+' "$f" | awk '{print $2}' | sort -n | tail -1)
	[ "${n:-0}" -le 300 ] || bad "warm kick count $n in $f above the limit"
done
[ $st = 0 ] && echo "guard: clean"
exit $st
