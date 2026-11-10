# SPDX-License-Identifier: MIT
# lib_r1.sh (R1): what the laptop-side R1 stage runner shares (sourced by run_stage.sh, never run).
# Built from S1b's lib_s1.sh with the fixes of its review (every item below is tested in tests/run_mock.sh).
#
# Safety rules of this runner (checked by run/guard_r1.sh):
#  - the only debugfs files ever written: render_pb_pages (allow-listed set_knob) and reset (the kernel's own
#    reset), plus /dev/kmsg for the markers.  No kreg, no kregnow, no kpoke write of ours, no /dev/mem write, no
#    clock-gate register and no trc_hazard written by any script here.  (The debugfs reset makes the KERNEL run its
#    boot sequence, which writes the clock-gate registers with the firmware's own values; every earlier batch resets
#    between jobs, so does this.)
#  - EVERY debugfs access (read, write, test, glob) goes through sudo -n (S1: an unprivileged read failed; S1b:
#    `[ -e ]` and globs too); run/guard_r1.sh refuses a code line that names the debugfs without sudo.
#  - the debugfs directory is the FIRST of `dri/*/sgx` (the node has three names: dri/0, dri/0000:00:02.0, dri/128):
#    never "exactly one".
#  - never a reboot, a boot-loader change or a kernel build; the tool is a userspace compile (deploy-tool.sh).
#  - no firmware-task `str`, no git, no recursive delete (work files are removed one by one by name).
#  - no polling or wait loop: no while/until anywhere; the only delays are single fixed sleeps after a reset and
#    before a health triangle; each attempt of the health check is written out one after the other.
# Root through sudo -n.  SGXFIVE_DEBUGFS points the runner at a plain directory (tests/run_mock.sh).
set -u
STAGE=${STAGE:?lib_r1.sh: STAGE not set}
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-r1}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
S=${SGXFIVE_PROBE_BINS:-$HOME/r1-stage}
OUTROOT=${OUTROOT:-$HOME/r1-out}
KEEP=${KEEP:-$OUTROOT/$STAGE}
TOOL_SHA_FILE=${TOOL_SHA_FILE:-$HOME/r1/TOOL.sha256}
GATE_FILE=${GATE_FILE:-$OUTROOT/gate072c.state}
GATE_MAX_AGE=${GATE_MAX_AGE:-21600}
D=${SGXFIVE_DEBUGFS:-$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)}
KMSG=${KMSG:-/dev/kmsg}
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|general protection|machine check|psb.*watchdog'
[ -x "$T" ] || { echo "no $T: stage it with run/stage_r1.sh (userspace compile only)"; exit 1; }
[ -n "$D" ] || { echo "no sgx debugfs directory (debug option off?)"; exit 1; }
export SGXFIVE_DEBUGFS="$D"
mkdir -p "$KEEP"
START=$(date +%s)
RUN=$(date +%s)-$$
sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }

mark() { printf "resgx545 r1 %s %s\n" "$*" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null 2>&1; }
# the case marker keeps the format of the earlier batches ("resgx545 case NAME RUN")
mark_case() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null 2>&1; }

set_knob() { # NAME VALUE: the allow-listed debugfs knob only; echoes the read-back
	case "$1" in
	render_pb_pages) ;;
	*) echo "set_knob: $1 is not allowed in R1"; exit 7 ;;
	esac
	echo "$2" | sudo -n tee "$D/$1" >/dev/null
	sudo -n cat "$D/$1"
}
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep "${RESET_WAIT:-3}"; }

preflight() {
	echo "## stage $STAGE"; echo "## uname"; uname -r
	echo "## firmware"; sha /lib/firmware/sgx545_ukernel.fw 2>/dev/null || echo "(no firmware file)"
	echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$SRCV_FILE"
	echo "## loaded module"; SRCV_LOADED=$(sudo -n cat "${SRCV_PATH:-/sys/module/gma500_gfx/srcversion}"); echo "$SRCV_LOADED"
	[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
	for f in reset render_pb_pages regs buf09 render_param render_tadata; do
		sudo -n test -e "$D/$f" || { echo "the loaded driver has no debugfs $f (kernel too old for R1)"; exit 1; }
	done
	echo "## debugfs directory: $D"
	echo "## tool"; got=$(sha "$T" | cut -d' ' -f1); echo "$got $T"
	want=$(cut -d' ' -f1 "$TOOL_SHA_FILE" 2>/dev/null)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "the tool is not the staged one ($got, staged ${want:-none}): run stage_r1.sh"; exit 1; }
	echo "## regtimeline"; sha "$RT" 2>/dev/null || { echo "(none: build tools/sweep/regtimeline.c for the laptop)"; [ "${NEED_RT:-1}" = 1 ] && exit 1; }
	echo "## knobs at start"
	PB_RESTORE=$(sudo -n cat "$D/render_pb_pages" 2>/dev/null); echo "render_pb_pages=$PB_RESTORE"
	[ -n "$PB_RESTORE" ] || { echo "the knob cannot be read (sudo?)"; exit 1; }
	# the markers are the job slices: one must arrive in the kernel log before any job
	mark "preflight $STAGE"
	sudo -n dmesg 2>/dev/null | grep -q "resgx545 r1 preflight $STAGE $RUN" \
		|| { echo "the kmsg marker did not arrive in dmesg (sudo -n tee $KMSG)"; exit 1; }
	echo "## kmsg marker arrived"
	echo "## clock"; date
	echo "## 0x072c gate state: $(gate_state)"
	echo "## R1 safety rules: see the header of lib_r1.sh (allow-listed knob only)"
}

W=$(mktemp -d)
clean_w() { # no glob in a delete: each file is removed by name
	for f in "$W"/*.out "$W"/*.bin "$W"/*.txt "$W"/*.dmesg "$W"/dump/* "$W"/words/* "$W"/depth/*; do
		[ -f "$f" ] && rm -f -- "$f"
	done
	return 0
}
FATAL_STOP=0
cleanup() {
	[ -n "${PB_RESTORE:-}" ] && set_knob render_pb_pages "$PB_RESTORE" >/dev/null 2>&1
	[ "$FATAL_STOP" = 1 ] || reset_gpu
	clean_w; rmdir "$W/dump" "$W/words" "$W/depth" "$W" 2>/dev/null; finish_log
}
trap cleanup EXIT
finish_log() {
	sudo -n journalctl -k --since "@$START" --no-pager > "$KEEP/kernel.log" 2>&1 || sudo -n dmesg > "$KEEP/kernel.log" 2>&1
	echo "## kernel log: $(grep -c 'resgx545 case' "$KEEP/kernel.log" | tr -d ' ') case markers kept in $KEEP/kernel.log"
}
keep() { # NAME FILE [SUFFIX]: gzip the whole raw file (mtime 0), print its sizes and raw sha256
	raw=$(wc -c < "$2" | tr -d ' ')
	sum=$(sha "$2" | cut -d' ' -f1)
	gzip -n -6 -c "$2" > "$KEEP/$1${3:-.txt}.gz"
	echo "$1${3:-.txt} $raw $sum" >> "$KEEP/raw.sha256"
	echo "  kept $1${3:-.txt}: $raw bytes raw, raw sha256 $sum"
}

tri_ok() { sudo -n timeout 60 "$T" tri 2>&1 </dev/null | grep -q "^diff: 0 of 4096"; }
health() { # a plain 64x64 triangle must draw exactly; reset and two more attempts, written out one by one; three failures stop
	sleep "${HEALTH_WAIT:-3}"
	if tri_ok; then return 0; fi
	reset_gpu; sleep "${HEALTH_WAIT:-5}"
	if tri_ok; then echo "  health: recovered after a reset"; return 0; fi
	sleep "${HEALTH_WAIT:-5}"
	if tri_ok; then echo "  health: recovered on the retry"; return 0; fi
	echo "## abort: the plain triangle does not draw after a reset and a retry (the first failed recovery stops)"
	exit 5
}
begin() {
	printf 'name\tstage\tset\trisk\tP\tknobs\trt\targs\trc\tclass\tnote\n' > "$KEEP/cases.tsv"; : > "$KEEP/raw.sha256"
	preflight; health </dev/null
}
# kernel log lines after a marker: the slice of one job
slice_since() { sudo -n dmesg 2>/dev/null | awk -v m="$1" 'f{print} index($0,m){f=1}'; }

# ---------------------------------------------------------------------------------------------------------------
# The 0x072c gate (decision R2-13 b).  CR_DPM_GLOBAL_PAGE_STATUS is read-only and has been seen as 0x10001, 0x40004,
# 0x50005.  The state file holds `untested`, `pass1` (the first trial job was clean), `pass` (both were), or `fail`,
# and the time of the last change; a `pass` older than GATE_MAX_AGE seconds counts as untested.  A trial job
# (knob trial072c:U) adds 0x072c to its timeline unless the state is `fail`; a job with the knob s072c adds it only in
# state `pass`.  The criteria G1-G6 are those of score/gate072c.py (tests/test_gate.py feeds both the same jobs).
gate_state() {
	gs=$(cut -d' ' -f1 "$GATE_FILE" 2>/dev/null); gt=$(cut -d' ' -f2 "$GATE_FILE" 2>/dev/null)
	[ -n "$gs" ] || { echo untested; return 0; }
	if [ "$gs" = pass ] && [ $(( $(date +%s) - ${gt:-0} )) -gt "$GATE_MAX_AGE" ]; then echo untested; return 0; fi
	echo "$gs"
}
gate_set() { mkdir -p "$(dirname "$GATE_FILE")"; echo "$1 $(date +%s)" > "$GATE_FILE"; echo "  0x072c gate state: $1"; }
gate_col() { # NAME REG: the hex values of REG's column of the `tl` rows, one a line (the header lists the registers)
	awk -v reg="$2" '/^timeline: regs/ { c = 0; for (i = 3; i <= NF; i++) { if ($i == "samples") break; if ($i == reg) c = i } next }
		/^tl / && c { print $c }' "$W/$1.out"
}
gate_check() { # NAME CLASS EXPECTED_U HEALTH_FIRST_TRY(1|0): sets GATE_WHY, returns 0 if the job is clean
	gn=$1; gc=$2; gu=$3; gh=$4; GATE_WHY=""
	[ "$gc" = ok ] || GATE_WHY="$GATE_WHY G1:class-$gc"
	nown=$(grep -v 'resgx545' "$W/$gn.dmesg" | grep -c .)
	[ "$nown" = 0 ] || GATE_WHY="$GATE_WHY G2:$nown-kernel-log-lines"
	if ! grep -q '^timeline: regs .* 0x072c .*samples' "$W/$gn.out" || ! grep -q '^timeline: regs .* 0x0724 .*samples' "$W/$gn.out"; then
		GATE_WHY="$GATE_WHY G3:no-0x072c-column"; return 1
	fi
	nrows=0; anylo=0
	for v in $(gate_col "$gn" 0x072c); do
		nrows=$((nrows + 1)); nv=$((0x$v)); hi=$(( (nv >> 16) & 65535 )); lo=$(( nv & 65535 ))
		if [ "$nv" -eq 4294967295 ] || [ "$nv" -eq 3735928559 ] || [ "$hi" -gt 64 ] || [ "$lo" -gt 64 ]; then
			GATE_WHY="$GATE_WHY G4:implausible-0x$v"
		fi
		[ "$lo" -gt 0 ] && anylo=1
	done
	[ "$nrows" -ge 10 ] || GATE_WHY="$GATE_WHY G3:only-$nrows-rows"
	[ "$anylo" = 1 ] || GATE_WHY="$GATE_WHY G4:never-non-zero"
	peak=0
	for v in $(gate_col "$gn" 0x0724); do
		lo=$(( 0x$v & 65535 )); [ "$lo" -gt "$peak" ] && peak=$lo
	done
	[ "$peak" -eq "$gu" ] || GATE_WHY="$GATE_WHY G5:0724-peak-$peak-not-$gu"
	[ "$gh" = 1 ] || GATE_WHY="$GATE_WHY G6:triangle-needed-a-reset"
	[ -z "$GATE_WHY" ]
}
