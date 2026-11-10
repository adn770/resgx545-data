#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_r3.sh: static checks of everything R3k runs, against the laptop limits (as relaxed by the kernel batch, R3-K1 to R3-K11) and the lessons of
# S1, S2, S2b, R1 and L3.  Run before staging (stage_r3.sh does).  Exit 0 clean, 1 with the matching lines.
#  1. no reboot / GRUB / kernel build or install / push; no trc_hazard; no clock register; no kreg or kpoke write; no /dev/mem write; no git
#     stash/clean/reset; no delete (rm, unlink, os.remove, rmtree).  The shell scripts name no debugfs write at all (they only test that files exist).
#  2. no loop that waits: no while/until in the shell scripts, no `while` in the laptop runner or its op modules, and the runner calls none of the
#     landed fwtask_run.py commands that poll (one_cmd, cmd_run, cmd_pair, cmd_tailpair, cmd_events, wait_state, wait_cmd_clear) or write registers (kreg)
#  3. debugfs only through root: every shell line that names /sys/kernel/debug runs it under `sudo -n`; the runner is started only as `sudo -n python3`;
#     the test-only overrides (R3_MOCK_ROOT, R3_FWTASK_DIR, R3_KMSG, R3_SRCV_PATH, R3_DEBUGFS, R3_NO_FREEZE_CHECK, R3_TOOL_R1, MOCK_) appear in no script
#     that drives the laptop; no `set -f` (it breaks the globs that keep dumps)
#  4. /dev/kmsg is opened with os.open(path, os.O_WRONLY | os.O_APPEND), never Python's "a" mode (it seeks: EINVAL)
#  5. the debugfs writes of the runner and its op modules, by name: own_code, own_arm, load, boot, reset; kicker and kick_no_bump only through
#     r3layout's constants (ops_kicker.py); hold_recovery only through `knob` with "Y" / "N"; kregnow only in ops_e3.py and only the two clear
#     registers 0x0114 (CLEAR2) and 0x0134 (CLEAR): never a BIF register, never an enable, never CLKGATECTL2
#  6. the task sources and tables: run/guard_blobs.py on the ASSEMBLED code (str only #69, #77, #691, each where it belongs; ldr of #81 only; mov to
#     pa only pa2-pa4 in pa_write2.s; the exit's words only in ring_exit.s; cont4 once; the sa write sets; the tables are exactly r3layout.ROW_SPEC; the
#     only trigger is none or miscinfo, never a bare kick); each source file is one of the known ones
cd "$(dirname "$0")/.." || exit 1
st=0
bad() { echo "GUARD: $*"; st=1; }
BAD='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make (-j|bzImage|modules)|build-kernel|install-test-kernel|boot-test-kernel|push-gma500|trc_hazard|CLKGATE|clkgate|kreg_write|"kreg"|kpoke|xfer_sync|/dev/mem|git (stash|clean|reset)|(^|[^a-z_])rm [-a-z]|unlink|os\.remove|rmtree|rmdir'
SH="run/r3.sh run/stage_r3.sh run/freeze_r3.sh run/health_remote.sh"
for f in $SH; do
	# comment lines may NAME what is forbidden; code may not
	if grep -nE "$BAD" "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "forbidden word in $f"; fi
done
# Python files: guard_py.py checks every line of code (comments and docstrings left out)
PYTHON=${PYTHON:-python3}
if ! "$PYTHON" run/guard_py.py run/r3_run.py run/ops_kicker.py run/ops_e2b.py run/ops_e3.py run/ops_k0.py run/r3common.py gen/r3layout.py gen/r3blobs.py gen/r3kblobs.py gen/gen_r3.py gen/laptop_files.py score/score_r3.py score/scorelib.py score/sc_ring.py score/sc_e2b.py score/sc_e3.py; then bad "forbidden word in the Python code"; fi
for f in $SH; do      # (this guard names the patterns it looks for)
	if grep -nE '(^|[;&|[:space:]])(while|until)[[:space:]]' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "wait loop in $f"; fi
	# 3: debugfs through sudo only
	if grep -n '/sys/kernel/debug' "$f" | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n'; then bad "unprivileged debugfs access in $f"; fi
	if grep -nE 'R3_MOCK_ROOT|R3_FWTASK_DIR|R3_KMSG|R3_SRCV_PATH|R3_SRCV_EXPECT|R3_DEBUGFS|R3_NO_FREEZE_CHECK|R3_TOOL_R1|MOCK_' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "a test-only override in $f"; fi
	if grep -nE '(^|[;&|[:space:]])set[[:space:]]+-[a-z]*f' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "set -f in $f (breaks the globs that keep dumps)"; fi
	if grep -nE '(>|tee)[[:space:]]*"?\$\{?d\}?/|/sys/kernel/debug[^ ]*[[:space:]]*>' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "a shell debugfs write in $f"; fi
done
PYRUN="run/r3_run.py run/ops_kicker.py run/ops_e2b.py run/ops_e3.py run/ops_k0.py"
# shellcheck disable=SC2086
if grep -nE '^[[:space:]]*while[[:space:]]' $PYRUN; then bad "a while loop in the runner or an op module"; fi
# shellcheck disable=SC2086
if grep -nE 'FR\.(one_cmd|cmd_run|cmd_pair|cmd_tailpair|cmd_events|wait_state|wait_cmd_clear|kreg)' $PYRUN; then bad "the runner calls a polling or register-writing command"; fi
if grep -n 'r3_run.py' run/r3.sh | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n python3'; then bad "the runner started without sudo -n python3"; fi
# 5: the debugfs writes by name
# shellcheck disable=SC2086
if grep -nE 'FR\.wr\(' $PYRUN | grep -vE 'FR\.wr\("(own_code|own_arm|load|boot|reset)"|FR\.wr\("kregnow", f"0x01(14|34)=0x|FR\.wr\(L\.(KICKER_FILE|KICK_NO_BUMP_FILE),|FR\.wr\(name, val\)'; then bad "a debugfs write off the allow-list"; fi
# shellcheck disable=SC2086
if grep -nE '\.knob\(' $PYRUN | grep -vE 'def knob|\.knob\("hold_recovery", (j\["hold_recovery"\]|"N")\)'; then bad "a knob other than hold_recovery"; fi
if grep -n 'wr("kregnow"' run/*.py | grep -v '^run/ops_e3\.py:'; then bad "a kregnow write outside ops_e3.py"; fi
if grep -nE '0x0*c0[04]|0x0*[0-9a-f]*[0-9a-f]=0x' run/ops_e3.py | grep -E 'wr\(' | grep -vE '0x01(14|34)=0x'; then bad "ops_e3.py writes a register other than the two clear registers"; fi
# 4: the kernel-log marker
grep -q 'os.open(KMSG, os.O_WRONLY | os.O_APPEND)' run/r3_run.py || bad "the kmsg marker is not written with os.open(..., os.O_WRONLY | os.O_APPEND)"
if grep -nE 'open\(KMSG|open\("/dev/kmsg"' run/r3_run.py | grep -v 'os\.open'; then bad "the kernel log opened in a Python mode (EINVAL on the laptop)"; fi
# 5: the sources (a quick text screen; the real check is on the assembled code)
for f in asm/*.s; do
	case "$f" in
	asm/alias2.s | asm/ring_hold.s | asm/ring_exit.s | asm/ring_timer.s | asm/ring_skip3.s | asm/pa_write2.s | asm/strclr.s | asm/loop-b16-i56.s) ;;
	*) bad "an unknown source: $f" ;;
	esac
	if grep -nE '^[[:space:]]*(p[0-3][[:space:]]+)?str[[:space:]]' "$f" | grep -vE 'str #(691|69|77),'; then bad "a str of a register off the list in $f"; fi
	if grep -nE '^[[:space:]]+ldr[[:space:]]' "$f" | grep -v '#81,'; then bad "ldr of a register other than CR_TIMER in $f"; fi
done
if ! "$PYTHON" run/guard_blobs.py; then bad "run/guard_blobs.py refused a blob or a table"; fi
[ $st = 0 ] && echo "guard: clean"
exit $st
