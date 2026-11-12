# SPDX-License-Identifier: MIT
# lib_m.sh: what the laptop-side r6-misc stage runner shares (sourced by run_stage.sh, never run).  Built from round 5's r5-render4x
# lib_k.sh (closing5/r5-render4x/run/lib_k.sh) with round 6's laptop file rule and without its knobs: this session writes NO debugfs
# knob (no render_pb_pages, render_rgn_arrays or hold_recovery write); the one debugfs write of the runner is `reset 1`.
#
# Safety rules of this runner (checked by run/guard_m.sh and tests/run_mock.sh):
#  - debugfs is root only: EVERY access goes through `sudo -n` (dbg_cat, dbg_write, snap, the preflight's `sudo -n test -e`, the
#    directory test and the glob).  The mock makes the debugfs directory unreadable to the user, so a bare access fails the mock run.
#  - the ONLY debugfs file the runner writes is `reset 1`; /dev/kmsg gets the markers (an append).  The tool itself writes the
#    table's kernel pokes (q287's --depth: ta:7, rd:1, rd:11..13 as E831; q086's --kpoke-render ta:143, 144, 146 as E511) through
#    debugfs kpoke; the reset before every job and at exit disarms what a job left.  No kreg, no kregnow, no BIF write, no
#    clock-gate register, no firmware-task str, no /dev/mem write.
#  - never a reboot, a boot-loader change or a kernel build; no compile at all.
#  - no polling or wait loop: no while/until; single fixed sleeps; each health attempt is written out one after the other.
#  - laptop files (round 6): everything under ~/scratch/r6m/ (run, stage, out); the work directory is one
#    `mktemp -d ~/scratch/tmp/r6m.XXXXXX` (never /tmp: sudo drops TMPDIR), each job's work directory is removed once its files are
#    kept (drop_work, only inside that mktemp directory) and the mktemp directory at exit; >= MIN_FREE_KB free on ~ before each job.
#  - the kernel log of a job or a step is the slice after its marker (never a line count); the kernel's reset information lines
#    ("SGX reset: BIF_FAULT ...", "SGX reset: after the fault clear ...") are not bad lines.
set -u
STAGE=${STAGE:?lib_m.sh: STAGE not set}
LIBDIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$LIBDIR/m.env"
TOOL_SHA=${M_TOOL_SHA:-$TOOL_SHA}
SRCV_EXPECT=${M_SRCV_EXPECT:-$SRCV_EXPECT}
TOOL6_SHA=${TOOL6_SHA:?lib_m.sh: TOOL6_SHA not set}
T4=${SGXFIVE_TEST4:-$HOME/sgxfive-test-rgn4}
T6=${SGXFIVE_TEST6:-$HOME/scratch/$PREFIX/bin/sgxfive-test}
BASE=$HOME/scratch/$PREFIX
# one directory an attempt (ATT from the driver), never reused: no merging of attempts
KEEP=$BASE/out/${ATT:?lib_m.sh: ATT not set}/$STAGE
if [ -d "$KEEP" ] && [ -n "$(ls -A "$KEEP")" ]; then echo "$KEEP is not empty: an attempt is never rerun into its directory"; exit 1; fi
mkdir -p "$KEEP" "$HOME/scratch/tmp" || { echo "cannot create $KEEP or ~/scratch/tmp"; exit 1; }
# everything printed from here on also goes to runner.log; with SIGPIPE ignored (run_stage.sh) a dropped ssh leaves tee writing it
TEE_P=""; tee -p /dev/null < /dev/null > /dev/null 2>&1 && TEE_P=-p
WROOT=$(mktemp -d "$HOME/scratch/tmp/$PREFIX.XXXXXX") || { echo "mktemp under ~/scratch/tmp failed"; exit 1; }
case "$WROOT" in "$HOME/scratch/tmp/$PREFIX."??????) ;; *) echo "unexpected work directory $WROOT"; exit 1 ;; esac
mkfifo "$WROOT/out.fifo" || { echo "mkfifo failed"; exit 1; }
tee $TEE_P -a "$KEEP/runner.log" < "$WROOT/out.fifo" &
TEEPID=$!
exec > "$WROOT/out.fifo" 2>&1
KMSG=${KMSG:-/dev/kmsg}
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|general protection|machine check|psb.*watchdog'
RESET_INFO_RE='SGX reset: (after the fault clear )?BIF_FAULT'
if [ -n "${SGXFIVE_DEBUGFS:-}" ]; then
	D=$SGXFIVE_DEBUGFS
else
	DL=/sys/kernel/debug/dri/0/sgx
	if ! sudo -n test -d "$DL"; then DL=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1); fi
	[ -n "$DL" ] && sudo -n test -d "$DL" || { echo "no sgx debugfs directory (dri/0/sgx or any dri/*/sgx)"; exit 1; }
	D=$DL
fi
START=$(date +%s)
RUN=$(date +%s)-$$
sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }

mark() { printf "resgx545 r6m %s %s\n" "$*" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null; }
mark_case() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null; }

dbg_cat() { sudo -n cat "$D/$1"; }
dbg_write() { # NAME VALUE: `reset 1` only, bounded
	case "$1 $2" in
	"reset 1") ;;
	*) echo "dbg_write: $1 $2 is not allowed in r6-misc"; exit 7 ;;
	esac
	printf '%s\n' "$2" | sudo -n timeout -k 5 20 tee "$D/$1" >/dev/null
}
NO_MORE_RESET=0
reset_gpu() {
	[ "$NO_MORE_RESET" = 1 ] && { echo "  (no reset: the session stopped)"; return 1; }
	dbg_write reset 1; local r=$?
	sleep "${RESET_WAIT:-3}"
	return $r
}
regval() { awk -v r="$2" '$1 == "reg" && $2 == r { print $3 }' "$1"; }
snap() { # NAME K: debugfs regs into $JW/snapK.regs (kept as NAME.snapK.regs.gz); 1 if unreadable
	local f="$JW/snap$2.regs"
	sudo -n cat "$D/regs" > "$f" 2>&1
	local r=$?
	if [ "$r" -ne 0 ] || ! grep -q '^reg 0x0c04 ' "$f"; then echo "  snap $2: regs unreadable (status $r)"; return 1; fi
	echo "  snap $2: status $(regval "$f" 0x012c) status2 $(regval "$f" 0x0118) bif_int $(regval "$f" 0x0c04) bif_fault $(regval "$f" 0x0c08)"
	mark "snap $1 $2 $(regval "$f" 0x0c04) $(regval "$f" 0x0c08) $(regval "$f" 0x012c) $(regval "$f" 0x0118)"
	return 0
}
fault_req() { local v; v=$(regval "$1" 0x0c04); [ -n "$v" ] && echo $(( v & 0xffff )); }
has_kept() { [ -f "$1" ]; }    # has_kept GLOB...: the first match exists (an unmatched glob stays literal)
free_kb() { df -Pk "$HOME" | awk 'NR == 2 { print $4 }'; }
free_ok() { local f; f=$(free_kb); [ -n "$f" ] && [ "$f" -ge "$MIN_FREE_KB" ]; }
# drop_work DIR: remove one job's work directory once its files are kept; only a directory inside this run's mktemp directory
drop_work() {
	case "$1" in "$WROOT"/[0-9]*|"$WROOT"/begin|"$WROOT"/end) rm -rf -- "$1" ;; *) echo "  drop_work: $1 is not a job directory of $WROOT: kept" ;; esac
}

preflight() {
	echo "## stage $STAGE"; echo "## uname"; uname -r
	echo "## firmware"; sha "${FW_PATH:-/lib/firmware/sgx545_ukernel.fw}" || { echo "no firmware file"; exit 1; }
	echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx); echo "$SRCV_FILE"
	echo "## loaded module"; SRCV_LOADED=$(sudo -n cat "${SRCV_PATH:-/sys/module/gma500_gfx/srcversion}"); echo "$SRCV_LOADED"
	[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
	[ "$SRCV_LOADED" = "$SRCV_EXPECT" ] || { echo "the loaded module ($SRCV_LOADED) is not the expected build ($SRCV_EXPECT)"; exit 1; }
	echo "## debugfs directory: $D"
	for f in reset regs kpoke hold_recovery render_pb_pages alias_skip render_rgn_arrays; do
		sudo -n test -e "$D/$f" || { echo "the loaded driver has no debugfs $f"; exit 1; }
	done
	echo "## tools"
	[ -x "$T4" ] || { echo "no $T4 (see PREFLIGHT.md)"; exit 1; }
	got=$(sha "$T4" | cut -d' ' -f1); echo "$got $T4"
	[ "$got" = "$TOOL_SHA" ] || { echo "t4 is not the rgn4 build ($TOOL_SHA)"; exit 1; }
	if [ "$NEED_T6" = 1 ]; then
		[ -x "$T6" ] || { echo "no $T6: the lead stages the d9b2969 build (lead/build_tool6.sh, run/stage_m.sh)"; exit 1; }
		got=$(sha "$T6" | cut -d' ' -f1); echo "$got $T6"
		[ "$got" = "$TOOL6_SHA" ] || { echo "t6 is not the frozen build ($TOOL6_SHA)"; exit 1; }
	fi
	echo "## knobs at start (read only; must be the defaults of fork a2788bd8: nothing of an earlier session left)"
	h=$(dbg_cat hold_recovery); pb=$(dbg_cat render_pb_pages); as=$(dbg_cat alias_skip); ra=$(dbg_cat render_rgn_arrays)
	echo "hold_recovery=$h render_pb_pages=$pb alias_skip=$as render_rgn_arrays=$ra"
	[ -n "$ra" ] && [ $(( ra )) -eq 0 ] || { echo "render_rgn_arrays is not 0 (automatic, the default) at the start"; exit 1; }
	[ "$h" = N ] || { echo "hold_recovery is not N at the start"; exit 1; }
	[ -n "$pb" ] && [ $((pb)) -eq $((0x422)) ] || { echo "render_pb_pages is not 0x422"; exit 1; }
	[ -n "$as" ] && [ $((as)) -eq 0 ] || { echo "alias_skip is not 0"; exit 1; }
	echo "## free space on ~: $(free_kb) KiB (at least $MIN_FREE_KB before each job)"
	free_ok || { echo "less than $MIN_FREE_KB KiB free on ~"; exit 22; }
	echo "## work directory $WROOT"
	echo "## clock"; date
}

FATAL_STOP=0
STARTED=0
cleanup_gpu() {
	if [ "$STARTED" != 1 ]; then echo "## exit before the preflight passed: nothing touched"; return; fi
	# nothing of the GPU's state is the runner's to restore (no knob written); a reset disarms a kpoke a job left armed
	if [ "$FATAL_STOP" != 1 ]; then reset_gpu; fi
	echo "## exit: hold_recovery=$(dbg_cat hold_recovery) render_pb_pages=$(dbg_cat render_pb_pages) render_rgn_arrays=$(dbg_cat render_rgn_arrays)"
	mark "exit"
	finish_log
}
cleanup() {
	cleanup_gpu
	case "$WROOT" in "$HOME/scratch/tmp/$PREFIX."??????) rm -rf -- "$WROOT" ;; esac
	exec >&- 2>&-
	( sleep "${TEE_GRACE:-10}"; kill "$TEEPID" 2>/dev/null ) </dev/null >/dev/null 2>&1 &
	wait "$TEEPID"
}
trap cleanup EXIT
finish_log() {
	if sudo -n journalctl -k --since "@$START" --no-pager > "$KEEP/kernel.log" 2>&1; then
		echo "## kernel log (journalctl)"
	else
		sudo -n dmesg > "$KEEP/kernel.log" 2>&1; echo "## kernel log (dmesg: journalctl failed)"
	fi
	echo "## kernel log: $(grep -c 'resgx545 case' "$KEEP/kernel.log") case markers kept in $KEEP/kernel.log"
}
keep() { # NAME FILE [SUFFIX]: gzip the whole raw file (mtime 0), print its sizes and raw sha256
	raw=$(wc -c < "$2" | tr -d ' ')
	sum=$(sha "$2" | cut -d' ' -f1)
	gzip -n -6 -c "$2" > "$KEEP/$1${3:-.txt}.gz"
	echo "$1${3:-.txt} $raw $sum" >> "$KEEP/raw.sha256"
	echo "  kept $1${3:-.txt}: $raw bytes raw, raw sha256 $sum"
}

HN=0
health_ok() { # NAME: one fill and one plain 64x64 triangle with the rgn4 tool, kept; 0 if both drew exactly
	HN=$((HN + 1))
	mark "health $1 fill try $HN"
	sudo -n timeout -k 10 60 "$T4" fill > "$JW/fill.$HN.out" 2>&1 </dev/null
	keep "$1.fill$HN" "$JW/fill.$HN.out"
	mark "health $1 tri try $HN"
	sudo -n timeout -k 10 60 "$T4" tri > "$JW/health.$HN.out" 2>&1 </dev/null
	keep "$1.health$HN" "$JW/health.$HN.out"
	grep -q "^diff: 0 of" "$JW/fill.$HN.out" && grep -q "^diff: 0 of 4096" "$JW/health.$HN.out"
}
health() { # NAME: fill and triangle exact; a reset and two more attempts, written out one by one; then stop
	sleep "${HEALTH_WAIT:-3}"
	if health_ok "$1"; then return 0; fi
	reset_gpu; sleep "${HEALTH_WAIT:-5}"
	if health_ok "$1"; then echo "  health: recovered after a reset"; return 0; fi
	sleep "${HEALTH_WAIT:-5}"
	if health_ok "$1"; then echo "  health: recovered on the retry"; return 0; fi
	echo "## abort: the fill and triangle do not draw after a reset and a retry (the first failed recovery stops)"
	exit 5
}
# strict_health NAME: after a fault-class event the FIRST health fill and triangle must draw (no reset of ours before); else the
# usual recovery runs and the stage stops, rc 16
strict_health() {
	sleep "${HEALTH_WAIT:-3}"
	if health_ok "$1"; then return 0; fi
	echo "## STOP: the health fill or triangle failed after $1 (strict): recovery, then stop"
	reset_gpu; sleep "${HEALTH_WAIT:-5}"
	if ! health_ok "$1"; then sleep "${HEALTH_WAIT:-5}"; health_ok "$1" || { echo "## abort: no recovery"; exit 5; }; fi
	exit 16
}
begin() {
	printf 'name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_req\tfault_word\tfree_kb\n' > "$KEEP/cases.tsv"
	: > "$KEEP/raw.sha256"
	JW=$WROOT/begin; mkdir -p "$JW"
	preflight
	STARTED=1
	reset_gpu || { echo "the first debugfs reset failed"; exit 1; }
	health begin </dev/null
	drop_work "$JW"
}
fault_int() { awk 'match($0, /BIF fault 0x[0-9a-f]+ at/) { v = substr($0, RSTART + 12, RLENGTH - 15); print v; exit }' "$1" | { read -r v; [ -n "$v" ] && echo $(( 0x$v & 0xffff )); }; }
fault_word() { awk 'match($0, /BIF fault 0x[0-9a-f]+ at 0x[0-9a-f]+/) { s = substr($0, RSTART, RLENGTH); sub(/.* at /, "", s); print s; exit }' "$1"; }
# the 3D-side class of E511's HS faults (and E845's): BIF_INT_STAT bits 15:0 0x0100, BIF_FAULT 0x100000xx
word_3d() { case "$1" in 0x[0-9a-fA-F]*) [ $(( $1 & 0xffffff00 )) -eq $(( 0x10000000 )) ] ;; *) return 1 ;; esac; }
slice_since() { sudo -n dmesg > "$JW/dmesg.all"; awk -v m="$1" 'f{print} index($0,m){f=1}' "$JW/dmesg.all"; }
bad_lines() { grep -Ev "$RESET_INFO_RE" "$@"; }
classify_plain() { # OUT ERR DMESG RC: fault | hang | ok | fail
	if bad_lines "$1" "$2" "$3" | grep -Eq "BIF fault|faulted"; then echo fault
	elif bad_lines "$1" "$2" "$3" | grep -Eq "job [0-9]+ hung|hung|timed out waiting"; then echo hang
	elif [ "$4" -eq 0 ]; then echo ok
	else echo fail; fi
}
