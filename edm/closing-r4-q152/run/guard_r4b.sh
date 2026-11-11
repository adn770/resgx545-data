#!/bin/bash
# SPDX-License-Identifier: MIT
# guard_r4b.sh: static checks of everything R4b runs (the limits and the lessons of R3k-events' guard_r3.sh, reduced to one stage and one
# blob).  Run before staging (stage_r4b.sh does).  Exit 0 clean, 1 with the matching lines.
#  1. no reboot / GRUB / kernel build or install / push; no trc_hazard; no clock register; no kreg, kregnow or kpoke; no /dev/mem; no git
#     stash/clean/reset; no delete.  The shell scripts name no debugfs write (they only test that files exist).
#  2. no loop that waits: no while/until in the shell scripts, no `while` in the runner, and the runner calls none of the landed
#     fwtask_run.py commands that poll or write registers
#  3. debugfs only through root: every shell line that names /sys/kernel/debug runs it under `sudo -n`; the runner is started only as
#     `sudo -n python3`; the test-only overrides (R3_*, MOCK_) appear in no script that drives the laptop
#  4. /dev/kmsg is opened with os.open(path, os.O_WRONLY | os.O_APPEND); the runner slices the kernel log with the landed dmesg_new(marker)
#     and judges a line with the landed is_bad_log (the reset's info line is not bad)
#  5. the runner writes no debugfs file by itself (FR.wr is not called; the landed cmd_arm, cmd_reset and cmd_gate write own_code, own_arm,
#     load, boot, reset) and writes no knob
#  6. run/guard_blob_r4b.py: the blob is R3k-events' (published hashes), the landed verifier accepts it and its source assembles to it,
#     the table is exactly gen/gen_r4b.py's
cd "$(dirname "$0")/.." || exit 1
st=0
bad() { echo "GUARD: $*"; st=1; }
BAD='reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make (-j|bzImage|modules)|build-kernel|install-test-kernel|boot-test-kernel|push-gma500|trc_hazard|CLKGATE|clkgate|kreg_write|"kreg"|kregnow|kpoke|xfer_sync|/dev/mem|git (stash|clean|reset)|(^|[^a-z_])rm [-a-z]|unlink|os\.remove|rmtree|rmdir'
SH="run/r4b.sh run/stage_r4b.sh run/freeze_r4b.sh run/health_remote.sh"
for f in $SH; do
	if grep -nE "$BAD" "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "forbidden word in $f"; fi
	if grep -nE '(^|[;&|[:space:]])(while|until)[[:space:]]' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "wait loop in $f"; fi
	if grep -n '/sys/kernel/debug' "$f" | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n'; then bad "unprivileged debugfs access in $f"; fi
	if grep -nE 'R3_[A-Z_]+|MOCK_' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "a test-only override in $f"; fi
	if grep -nE '(>|tee)[[:space:]]*"?\$\{?d\}?/|/sys/kernel/debug[^ ]*[[:space:]]*>' "$f" | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "a shell debugfs write in $f"; fi
done
PYTHON=${PYTHON:-python3}
if ! "$PYTHON" run/guard_py.py run/r4b_run.py run/r3common.py gen/r3layout.py gen/r4blayout.py gen/gen_r4b.py gen/laptop_files.py score/score_r4b.py score/scorelib.py score/scorekit.py; then bad "forbidden word in the Python code"; fi
if grep -nE 'kregnow' run/r4b_run.py gen/r4blayout.py | grep -vE '^[0-9]+:[[:space:]]*#'; then bad "kregnow named in the runner"; fi
if grep -nE '^[[:space:]]*while[[:space:]]' run/r4b_run.py; then bad "a while loop in the runner"; fi
if grep -nE 'FR\.(one_cmd|cmd_run|cmd_pair|cmd_tailpair|cmd_events|wait_state|wait_cmd_clear|kreg|wr)\b' run/r4b_run.py; then bad "the runner calls a polling, register-writing or debugfs-writing command"; fi
if grep -nE '\.knob\(|FR\.D\}/[^"]*", *"w|open\([^)]*FR\.D[^)]*"w' run/r4b_run.py; then bad "the runner writes a knob or a debugfs file"; fi
if grep -n 'r4b_run.py' run/r4b.sh | grep -vE '^[0-9]+:[[:space:]]*#' | grep -v 'sudo -n python3'; then bad "the runner started without sudo -n python3"; fi
grep -q 'os.open(KMSG, os.O_WRONLY | os.O_APPEND)' run/r4b_run.py || bad "the kmsg marker is not written with os.open(..., os.O_WRONLY | os.O_APPEND)"
if grep -nE 'open\(KMSG|open\("/dev/kmsg"' run/r4b_run.py | grep -v 'os\.open'; then bad "the kernel log opened in a Python mode"; fi
if grep -nE 'dmesg_new\(0\)|dmesg_len\(\)' run/r4b_run.py; then bad "the runner slices the kernel log by a line count"; fi
grep -q 'FR.is_bad_log' run/r4b_run.py || bad "the runner does not judge kernel lines with the landed is_bad_log"
for f in asm/*.s; do [ "$f" = asm/ring_exit.s ] || bad "an unknown source: $f"; done
if ! "$PYTHON" run/guard_blob_r4b.py; then bad "run/guard_blob_r4b.py refused the blob or the table"; fi
[ $st = 0 ] && echo "guard: clean"
exit $st
