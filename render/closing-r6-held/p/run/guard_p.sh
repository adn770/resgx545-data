#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_p.sh: static checks of everything r6-held part P runs (R5-events' guard), against the laptop limits of the round 5 and 6 briefs (R4-events'
# guard_r4e.sh with the clock knob added and the kicker dropped).  Run before staging (stage_p.sh does).  Exit 0 clean, 1 with the matching lines.
#  1. no reboot / GRUB / kernel build or install / push; no trc_hazard; no clock register; no kreg or kpoke write; no /dev/mem; no git
#     stash/clean/reset; no delete (rm, unlink, os.remove, rmtree).  The shell scripts name no debugfs write at all and no kregnow.
#  2. no loop that waits: no while/until in the shell scripts, no `while` in the runner or its op modules, and the runner calls none of the
#     landed fwtask_run.py commands that poll (one_cmd, cmd_run, cmd_pair, cmd_tailpair, cmd_events, wait_state, wait_cmd_clear) or write
#     registers (kreg)
#  3. debugfs only through root: every shell line that names /sys/kernel/debug runs it under `sudo -n`; the runner is started only as
#     `sudo -n python3`; the test-only overrides (R3_*, MOCK_) appear in no script that drives the laptop; no `set -f`
#  4. /dev/kmsg is opened with os.open(path, os.O_WRONLY | os.O_APPEND), never Python's "a" mode; the runner slices the kernel log with the
#     landed dmesg_new(marker) and judges a line with the landed is_bad_log
#  5. the debugfs writes of the runner and its op module, by name: own_code, own_arm, load, boot, reset (the landed commands); hold_recovery
#     and timer_clock only through `knob` (hold_recovery "Y" / "N"; timer_clock the job's value, checked by knob() against r5layout.CLOCKS,
#     or "0"); no kicker, no kick_no_bump write; kregnow only in ops_h.py and only the CLEAR register 0x0134 (the value from the frozen
#     table: bits 15 and 18): never CLEAR2, a BIF register, an enable or CLKGATECTL2
#  6. the task sources and tables: run/guard_blobs.py on the ASSEMBLED code (no firmware str at all; ldr of #81 only; no pa or sa write; the
#     phase end once, at the end of the own-end block; no cfi.global, no cont4; the blob is R4's bytes; the tables are exactly
#     r5layout.ROW_SPEC; the clock values are r5layout.CLOCKS); the one source file is asm/ring_skip3p.s
cd "$(dirname "$0")/.." || exit 1
st=0
bad() { echo "GUARD: $*"; st=1; }
BAD='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make (-j|bzImage|modules)|build-kernel|install-test-kernel|boot-test-kernel|push-gma500|trc_hazard|CLKGATE|clkgate|kreg_write|"kreg"|kpoke|xfer_sync|/dev/mem|git (stash|clean|reset)|(^|[^a-z_])rm [-a-z]|unlink|os\.remove|rmtree|rmdir'
SH="run/p.sh run/stage_p.sh run/freeze_p.sh run/health_remote.sh"
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
PYRUN="run/r6hp_run.py run/ops_h.py"
# shellcheck disable=SC2086
if ! "$PYTHON" run/guard_py.py $PYRUN run/r3common.py gen/r3layout.py gen/r5layout.py gen/r3blobs.py gen/gen_r5.py gen/laptop_files.py \
	score/score_p.py score/scorelib.py score/scorekit.py score/r5common.py score/sc_h.py; then bad "forbidden word in the Python code"; fi
# shellcheck disable=SC2086
if grep -nE '^[[:space:]]*while[[:space:]]' $PYRUN; then bad "a while loop in the runner or an op module"; fi
# shellcheck disable=SC2086
if grep -nE 'FR\.(one_cmd|cmd_run|cmd_pair|cmd_tailpair|cmd_events|wait_state|wait_cmd_clear|kreg)' $PYRUN; then bad "the runner calls a polling or register-writing command"; fi
if grep -n 'r6hp_run.py' run/p.sh | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n python3'; then bad "the runner started without sudo -n python3"; fi
# 5: the debugfs writes by name
# shellcheck disable=SC2086
if grep -nE 'FR\.wr\(' $PYRUN | grep -vE 'FR\.wr\("kregnow", f"0x0134=0x\{value:x\}"\)|FR\.wr\(name, str\(val\)\)|FR\.wr\(name, val\)'; then bad "a debugfs write off the allow-list"; fi
# shellcheck disable=SC2086
if grep -nE '\.knob\(' $PYRUN | grep -vE 'def knob|\.knob\("hold_recovery", (j\["hold_recovery"\]|"N")\)|\.knob\("timer_clock", (str\(v\)|"0")\)'; then bad "a knob write off the allow-list"; fi
grep -q 'if name == "timer_clock" and (not str(val).isdigit() or int(val) not in L.CLOCKS):' run/r6hp_run.py || bad "knob() does not check timer_clock against r5layout.CLOCKS"
grep -q 'KNOB_BACK = {"hold_recovery": "N", "timer_clock": "0"}' run/r6hp_run.py || bad "the knobs are not put back to N and 0"
if grep -n 'FR.wr("kregnow"' run/*.py | grep -v '^run/ops_h\.py:'; then bad "a kregnow write outside ops_h.py"; fi
if ! "$PYTHON" run/guard_names.py 'kregnow' --allow '"kregnow",' run/r6hp_run.py; then bad "kregnow named outside ops_h.py and the file list"; fi
if ! "$PYTHON" run/guard_names.py '0x0114|0x012[0-9a-f]|CLEAR2|0x0c0|0x0b|kicker|kick_no_bump' run/ops_h.py; then bad "ops_h.py names CLEAR2, another register or the kicker"; fi
# shellcheck disable=SC2086
if ! "$PYTHON" run/guard_names.py '"kicker"|KICKER_FILE|KICK_NO_BUMP_FILE' $PYRUN; then bad "the runner names the kicker (this session writes none)"; fi
# 4: the kernel-log marker
grep -q 'os.open(KMSG, os.O_WRONLY | os.O_APPEND)' run/r6hp_run.py || bad "the kmsg marker is not written with os.open(..., os.O_WRONLY | os.O_APPEND)"
if grep -nE 'open\(KMSG|open\("/dev/kmsg"' run/r6hp_run.py | grep -v 'os\.open'; then bad "the kernel log opened in a Python mode (EINVAL on the laptop)"; fi
if grep -nE 'dmesg_new\(0\)|dmesg_len\(\)' run/r6hp_run.py; then bad "the runner slices the kernel log by a line count"; fi
grep -q 'FR.is_bad_log' run/r6hp_run.py || bad "the runner does not judge kernel lines with the landed is_bad_log"
grep -q 'def restore_knobs' run/r6hp_run.py || bad "the runner has no knob put-back"
grep -q 'signal.SIGTERM' run/r6hp_run.py || bad "the runner has no trap on TERM, HUP and INT"
# r6-held part P (round 6): the peek is only read; every `timeout` has -k; no /tmp; the one delete is rm_work's
# shellcheck disable=SC2086
if grep -nE 'peek' $PYRUN $SH | grep -vE '^[^:]+:[0-9]+:[[:space:]]*#' | grep -E 'FR\.wr|os\.open|O_WRONLY|O_RDWR|"w"|tee|>[[:space:]]*"?\$'; then bad "a write to debugfs peek"; fi
grep -q '\["timeout", "-k", str(k), str(s), "cat", f"{FR.D}/{L.PEEK_FILE}"\]' run/r6hp_run.py || bad "the peek is not read with timeout -k ... cat"
[ "$(grep -c 'PEEK_FILE' run/r6hp_run.py)" = 2 ] || bad "PEEK_FILE named outside the read and the preflight's file list"
# shellcheck disable=SC2086
if grep -nE '(^|[^a-z_])timeout[[:space:]]' $SH | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'timeout -k'; then bad "a timeout without -k in a script"; fi
# shellcheck disable=SC2086
if grep -nE '"timeout", ' $PYRUN | grep -v '"timeout", "-k"'; then bad "a timeout without -k in the runner"; fi
# shellcheck disable=SC2086
if grep -nE '(^|[[:space:]"'"'"'=(~])/tmp\b|tempfile|gettempdir' $SH $PYRUN | grep -vE '^[^:]+:[0-9]+:[[:space:]]*#'; then bad "/tmp or tempfile in a script or the runner (round 6: ~/scratch only)"; fi
[ "$(grep -c 'shutil.rmtree' run/r6hp_run.py)" = 1 ] || bad "shutil.rmtree used other than once (rm_work)"
awk '/def rm_work/,/shutil.rmtree/' run/r6hp_run.py | grep -q 'if not self.work_re.fullmatch(p) or p not in self.workdirs:' || bad "rm_work does not check the path first"
grep -q 'ap.add_argument("--work", required=True)' run/r6hp_run.py || bad "the runner takes no --work directory"
grep -q -- '--work ~/$WK' run/p.sh || bad "the driver does not name ~/scratch/tmp as the work directory"
# 6: the sources (a quick text screen; the real check is on the assembled code)
for f in asm/*.s; do
	case "$f" in
	asm/ring_skip3p.s) ;;
	*) bad "an unknown source: $f" ;;
	esac
	if grep -nE '^[[:space:]]*(p[0-3][[:space:]]+)?str[[:space:]]' "$f"; then bad "a firmware str in $f (none is allowed)"; fi
	if grep -nE '^[[:space:]]+ldr[[:space:]]' "$f" | grep -v '#81,'; then bad "ldr of a register other than CR_TIMER in $f"; fi
done
if ! "$PYTHON" run/guard_blobs.py; then bad "run/guard_blobs.py refused a blob or a table"; fi
[ $st = 0 ] && echo "guard: clean"
exit $st
