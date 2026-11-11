#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_r4e.sh: static checks of everything R4-events runs, against the laptop limits of the round 4 brief and the lessons of R3k-events'
# guard_r3.sh and R4b's guard_r4b.sh.  Run before staging (stage_r4e.sh does).  Exit 0 clean, 1 with the matching lines.
#  1. no reboot / GRUB / kernel build or install / push; no trc_hazard; no clock register; no kreg or kpoke write; no /dev/mem; no git
#     stash/clean/reset; no delete (rm, unlink, os.remove, rmtree).  The shell scripts name no debugfs write at all and no kregnow.
#  2. no loop that waits: no while/until in the shell scripts, no `while` in the runner or its op modules, and the runner calls none of the
#     landed fwtask_run.py commands that poll (one_cmd, cmd_run, cmd_pair, cmd_tailpair, cmd_events, wait_state, wait_cmd_clear) or write
#     registers (kreg)
#  3. debugfs only through root: every shell line that names /sys/kernel/debug runs it under `sudo -n`; the runner is started only as
#     `sudo -n python3`; the test-only overrides (R3_*, MOCK_) appear in no script that drives the laptop; no `set -f`
#  4. /dev/kmsg is opened with os.open(path, os.O_WRONLY | os.O_APPEND), never Python's "a" mode; the runner slices the kernel log with the
#     landed dmesg_new(marker) and judges a line with the landed is_bad_log
#  5. the debugfs writes of the runner and its op modules, by name: own_code, own_arm, load, boot, reset (the landed commands); kicker only
#     through r4layout's constant (ops_kicker2.py, `=0x42`); kick_no_bump only through the constant (Y); hold_recovery only through `knob`
#     with "Y" / "N" (ops_e3p.py and the runner's put-back); kregnow only in ops_e3p.py and only the CLEAR register 0x0134 (the value from
#     the frozen table: bits 15 and 18): never CLEAR2, a BIF register, an enable or CLKGATECTL2
#  6. the task sources and tables: run/guard_blobs.py on the ASSEMBLED code (no firmware str at all; ldr of #81 only; no pa or sa write; the
#     phase end once, at the end of the own-end block; no cfi.global, no cont4; the tables are exactly r4layout.ROW_SPEC; the only trigger
#     is none or miscinfo, never a bare kick); each source file is one of the three known ones
cd "$(dirname "$0")/.." || exit 1
st=0
bad() { echo "GUARD: $*"; st=1; }
BAD='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make (-j|bzImage|modules)|build-kernel|install-test-kernel|boot-test-kernel|push-gma500|trc_hazard|CLKGATE|clkgate|kreg_write|"kreg"|kpoke|xfer_sync|/dev/mem|git (stash|clean|reset)|(^|[^a-z_])rm [-a-z]|unlink|os\.remove|rmtree|rmdir'
SH="run/r4e.sh run/stage_r4e.sh run/freeze_r4e.sh run/health_remote.sh"
for f in $SH; do
	# comment lines may NAME what is forbidden; code may not
	if grep -nE "$BAD" "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "forbidden word in $f"; fi
	if grep -nE '(^|[;&|[:space:]])(while|until)[[:space:]]' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "wait loop in $f"; fi
	if grep -n '/sys/kernel/debug' "$f" | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n'; then bad "unprivileged debugfs access in $f"; fi
	if grep -nE 'R3_[A-Z_]+|MOCK_' "$f" | grep -vE '^[0-9]+:[[:space:]]*#' | grep -vE 'R3_OUT|R3_TOOL_NAME'; then bad "a test-only override in $f"; fi
	if grep -nE '(^|[;&|[:space:]])set[[:space:]]+-[a-z]*f' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "set -f in $f (breaks the globs that keep dumps)"; fi
	if grep -nE '(>|tee)[[:space:]]*"?\$\{?d\}?/|/sys/kernel/debug[^ ]*[[:space:]]*>' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "a shell debugfs write in $f"; fi
done
PYTHON=${PYTHON:-python3}
PYRUN="run/r4e_run.py run/ops_kicker2.py run/ops_e3p.py"
# shellcheck disable=SC2086
if ! "$PYTHON" run/guard_py.py $PYRUN run/r3common.py gen/r3layout.py gen/r4layout.py gen/r3blobs.py gen/r4blobs.py gen/gen_r4.py gen/laptop_files.py \
	score/score_r4e.py score/scorelib.py score/scorekit.py score/r4common.py score/sc_kb2.py score/sc_kp.py score/sc_e3p.py; then bad "forbidden word in the Python code"; fi
# shellcheck disable=SC2086
if grep -nE '^[[:space:]]*while[[:space:]]' $PYRUN; then bad "a while loop in the runner or an op module"; fi
# shellcheck disable=SC2086
if grep -nE 'FR\.(one_cmd|cmd_run|cmd_pair|cmd_tailpair|cmd_events|wait_state|wait_cmd_clear|kreg)' $PYRUN; then bad "the runner calls a polling or register-writing command"; fi
if grep -n 'r4e_run.py' run/r4e.sh | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n python3'; then bad "the runner started without sudo -n python3"; fi
# 5: the debugfs writes by name
# shellcheck disable=SC2086
if grep -nE 'FR\.wr\(' $PYRUN | grep -vE 'FR\.wr\(L\.(KICKER_FILE|KICK_NO_BUMP_FILE),|FR\.wr\("kregnow", f"0x0134=0x\{value:x\}"\)|FR\.wr\(name, val\)'; then bad "a debugfs write off the allow-list"; fi
if grep -nE 'FR\.wr\(L\.KICKER_FILE' run/*.py | grep -v 'f"={j\[.set_kicker.\]}"'; then bad "a kicker write that is not the table's word"; fi
if grep -nE 'FR\.wr\(L\.KICK_NO_BUMP_FILE' run/*.py | grep -v '"Y")'; then bad "a kick_no_bump write that is not Y"; fi
if grep -nE '\.knob\(' $PYRUN | grep -vE 'def knob|\.knob\("hold_recovery", (j\["hold_recovery"\]|"N")\)'; then bad "a knob other than hold_recovery"; fi
if grep -n 'FR.wr("kregnow"' run/*.py | grep -v '^run/ops_e3p\.py:'; then bad "a kregnow write outside ops_e3p.py"; fi
# shellcheck disable=SC2086
if ! "$PYTHON" run/guard_names.py 'kregnow' --allow '^"kicker", "kick_no_bump",$|^"kregnow", "hold_recovery"|"kregnow",' run/r4e_run.py run/ops_kicker2.py; then bad "kregnow named outside ops_e3p.py and the file list"; fi
if ! "$PYTHON" run/guard_names.py '0x0114|0x012[0-9a-f]|CLEAR2|0x0c0|0x0b' run/ops_e3p.py; then bad "ops_e3p.py names CLEAR2 or another register"; fi
# 4: the kernel-log marker
grep -q 'os.open(KMSG, os.O_WRONLY | os.O_APPEND)' run/r4e_run.py || bad "the kmsg marker is not written with os.open(..., os.O_WRONLY | os.O_APPEND)"
if grep -nE 'open\(KMSG|open\("/dev/kmsg"' run/r4e_run.py | grep -v 'os\.open'; then bad "the kernel log opened in a Python mode (EINVAL on the laptop)"; fi
if grep -nE 'dmesg_new\(0\)|dmesg_len\(\)' run/r4e_run.py; then bad "the runner slices the kernel log by a line count"; fi
grep -q 'FR.is_bad_log' run/r4e_run.py || bad "the runner does not judge kernel lines with the landed is_bad_log"
grep -q 'def restore_knobs' run/r4e_run.py || bad "the runner has no knob put-back"
grep -q 'signal.SIGTERM' run/r4e_run.py || bad "the runner has no trap on TERM, HUP and INT"
# 6: the sources (a quick text screen; the real check is on the assembled code)
for f in asm/*.s; do
	case "$f" in
	asm/ring_hold.s | asm/ring_exit2.s | asm/ring_skip3p.s) ;;
	*) bad "an unknown source: $f" ;;
	esac
	if grep -nE '^[[:space:]]*(p[0-3][[:space:]]+)?str[[:space:]]' "$f"; then bad "a firmware str in $f (none is allowed)"; fi
	if grep -nE '^[[:space:]]+ldr[[:space:]]' "$f" | grep -v '#81,'; then bad "ldr of a register other than CR_TIMER in $f"; fi
done
if ! "$PYTHON" run/guard_blobs.py; then bad "run/guard_blobs.py refused a blob or a table"; fi
[ $st = 0 ] && echo "guard: clean"
exit $st
