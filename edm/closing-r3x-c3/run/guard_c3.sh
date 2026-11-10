#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_c3.sh: static checks of everything C3 runs, against the laptop limits and the lessons of S1, S2, S2b and R1.  Run
# before staging (stage_c3.sh does).  Exit 0 clean, 1 with the matching lines.
#  1. no reboot / GRUB / kernel build or install / push; no trc_hazard; no clock register; no kreg, kregnow or kpoke write; no
#     /dev/mem write; no git stash/clean/reset; no delete (rm, unlink, os.remove, rmtree)
#  2. no loop that waits: no while/until in the shell scripts, no `while` in the laptop runner, and the runner calls none of the
#     landed fwtask_run.py commands that poll (one_cmd, cmd_run, cmd_pair, cmd_tailpair, cmd_events, wait_state, wait_cmd_clear)
#     or write registers (kreg)
#  3. debugfs only through root: every shell line that names /sys/kernel/debug runs it under `sudo -n`; the runner is started only
#     as `sudo -n python3`; the test-only overrides (R3_MOCK_ROOT, R3_FWTASK_DIR, R3_KMSG, R3_SRCV_PATH, R3_DEBUGFS, R3_NO_FREEZE_
#     CHECK, MOCK_) appear in no script that drives the laptop; no `set -f` (it breaks the globs that keep dumps)
#  4. /dev/kmsg is opened with os.open(path, os.O_WRONLY | os.O_APPEND), never Python's "a" mode (it seeks: EINVAL)
#  5. the task sources and tables: run/guard_blobs.py on the ASSEMBLED code (no str at all, ldr of #81 only, the sa write set of
#     every command of start.s = sa63 in the writer (command 1) and nothing else, r20/r21/i0/i1 only in the writer, one pclink
#     triple an entry; rows only S0, N, F, L, R; the arm line, the stop budget 0, the perturbation of each row from the allow-list);
#     the one source file is start.s
cd "$(dirname "$0")/.." || exit 1
st=0
bad() { echo "GUARD: $*"; st=1; }
BAD='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make (-j|bzImage|modules)|build-kernel|install-test-kernel|boot-test-kernel|push-gma500|trc_hazard|CLKGATE|clkgate|kregnow|kreg_write|"kreg"|kpoke|/dev/mem|git (stash|clean|reset)|(^|[^a-z_])rm [-a-z]|unlink|os\.remove|rmtree|rmdir'
SH="run/c3.sh run/stage_c3.sh run/freeze_c3.sh run/health_remote.sh"
for f in $SH; do
	# comment lines may NAME what is forbidden; code may not
	if grep -nE "$BAD" "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "forbidden word in $f"; fi
done
# Python files: guard_py.py checks every line of code (comments and docstrings left out)
PYTHON=${PYTHON:-python3}
if ! "$PYTHON" run/guard_py.py run/c3_run.py gen/c3layout.py gen/c3blobs.py gen/gen_c3.py score/score_c3.py; then bad "forbidden word in the Python code"; fi
for f in $SH; do      # (this guard names the patterns it looks for)
	if grep -nE '(^|[;&|[:space:]])(while|until)[[:space:]]' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "wait loop in $f"; fi
	# 3: debugfs through sudo only
	if grep -n '/sys/kernel/debug' "$f" | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n'; then bad "unprivileged debugfs access in $f"; fi
	if grep -nE 'R3_MOCK_ROOT|R3_FWTASK_DIR|R3_KMSG|R3_SRCV_PATH|R3_DEBUGFS|R3_NO_FREEZE_CHECK|MOCK_' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "a test-only override in $f"; fi
	if grep -nE '(^|[;&|[:space:]])set[[:space:]]+-[a-z]*f' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "set -f in $f (breaks the globs that keep dumps)"; fi
done
if grep -nE '^[[:space:]]*while[[:space:]]' run/c3_run.py; then bad "a while loop in the runner"; fi
if grep -nE 'FR\.(one_cmd|cmd_run|cmd_pair|cmd_tailpair|cmd_events|wait_state|wait_cmd_clear|kreg)' run/c3_run.py; then bad "the runner calls a polling or register-writing command"; fi
if grep -n 'c3_run.py' run/c3.sh | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n python3'; then bad "the runner started without sudo -n python3"; fi
# the runner writes debugfs only through FR.wr / Res.w on the allow-list of names: own_code, own_arm, own_res (Res), load, boot, reset
if grep -noE 'FR\.wr\("[a-z_0-9]+"' run/c3_run.py | grep -vE 'FR\.wr\("(own_code|own_arm|load|boot|reset)"'; then bad "the runner writes a debugfs file off the allow-list"; fi
# the runner runs shell commands (FR.sh) only for modinfo, uname, sha256sum, journalctl and the gate tool's fill
if grep -n 'FR\.sh(' run/c3_run.py | grep -vE 'FR\.sh\(("|f")(modinfo|uname|sha256sum|journalctl|\{tool\} fill)'; then bad "the runner runs a shell command off the allow-list"; fi
# 4: the kernel-log marker
grep -q 'os.open(KMSG, os.O_WRONLY | os.O_APPEND)' run/c3_run.py || bad "the kmsg marker is not written with os.open(..., os.O_WRONLY | os.O_APPEND)"
if grep -nE 'open\(KMSG|open\("/dev/kmsg"' run/c3_run.py | grep -v 'os\.open'; then bad "the kernel log opened in a Python mode (EINVAL on the laptop)"; fi
# 5: the sources (a quick text screen; the real check is on the assembled code)
for f in asm/*.s; do
	case "$f" in
	asm/start.s) ;;
	*) bad "an unknown source: $f" ;;
	esac
	if grep -nE '^[[:space:]]*(p[0-3][[:space:]]+)?str[[:space:]]' "$f"; then bad "str in $f"; fi
	if grep -nE '^[[:space:]]+ldr[[:space:]]' "$f" | grep -v '#81,'; then bad "ldr of a register other than CR_TIMER in $f"; fi
done
if ! "$PYTHON" run/guard_blobs.py; then bad "run/guard_blobs.py refused a blob or a table"; fi
[ $st = 0 ] && echo "guard: clean"
exit $st
