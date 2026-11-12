# SPDX-License-Identifier: MIT
# lib_k.sh: what the laptop-side r5-render4x stage runner shares (sourced by run_stage.sh, never run).  Copied from R4-G's
# (closing4/r4-render4x/run/lib_k.sh: R4-A's with K2's held-job flow) with the r5x directories and markers and the fault-word readers
# of round 5's stop rule (fault_int, fault_word, num_word).  Three knobs: render_pb_pages (a row's own value, put back to 0x422 after
# the job and at every exit), hold_recovery (written Y and N by the held flow only) and render_rgn_arrays (forced to 1 for a row that
# names rgn:1, back to 0 after every job and at every exit).
#
# Safety rules of this runner (checked by run/guard_k.sh and tests/run_mock.sh):
#  - debugfs is root only: EVERY access goes through `sudo -n` (dbg_cat, dbg_write, snap, the preflight's `sudo -n test -e`, the
#    directory test and the glob).  The mock makes the debugfs directory unreadable to the user, so a bare access fails the mock run.
#  - the ONLY debugfs files written are `reset 1`, `render_rgn_arrays 0|1`, `render_pb_pages 0xNN` (0x23 to 0x422) and
#    `hold_recovery Y|N`; /dev/kmsg gets the markers (an append).  No kreg, no kregnow, no kpoke write of the runner's (the tool writes
#    the table's pokes), no BIF write, no clock-gate register, no firmware-task str, no /dev/mem write (the tool READS registers with
#    --regs).  render_param and render_tadata are only READ (a held job's dump).
#  - never a reboot, a boot-loader change or a kernel build; no compile at all.
#  - no polling or wait loop: no while/until; single fixed sleeps; one `wait PID` for a background job that is itself bounded by
#    `timeout -k`; each health attempt is written out one after the other (no loop).
#  - no file is deleted: each job writes into its own new directory under one mktemp directory.
#  - the kernel log of a job or a step is the slice after its marker (never a line count); the kernel's reset information lines
#    ("SGX reset: BIF_FAULT ...", "SGX reset: after the fault clear ...") are not bad lines.
set -u
STAGE=${STAGE:?lib_k.sh: STAGE not set}
LIBDIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$LIBDIR/k.env"
TOOL_SHA=${K_TOOL_SHA:-$TOOL_SHA}
SRCV_EXPECT=${K_SRCV_EXPECT:-$SRCV_EXPECT}
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-rgn4}
S=${SGXFIVE_PROBE_BINS:-$HOME/r5x-stage}
# one directory an attempt (ATT from the driver), never reused: no merging of attempts
KEEP=${K_OUT:-$HOME/r5x-out}/${ATT:?lib_k.sh: ATT not set}/$STAGE
if [ -d "$KEEP" ] && [ -n "$(ls -A "$KEEP")" ]; then echo "$KEEP is not empty: an attempt is never rerun into its directory"; exit 1; fi
mkdir -p "$KEEP" || { echo "cannot create $KEEP"; exit 1; }
# everything printed from here on also goes to runner.log; with SIGPIPE ignored (run_stage.sh) a dropped ssh leaves tee writing it
TEE_P=""; tee -p /dev/null < /dev/null > /dev/null 2>&1 && TEE_P=-p
WROOT=$(mktemp -d)
mkfifo "$WROOT/out.fifo" || { echo "mkfifo failed"; exit 1; }
tee $TEE_P -a "$KEEP/runner.log" < "$WROOT/out.fifo" &
TEEPID=$!
exec > "$WROOT/out.fifo" 2>&1
KMSG=${KMSG:-/dev/kmsg}
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|general protection|machine check|psb.*watchdog'
# the kernel's reset information lines (sgxfive_reset): never a sign of trouble by themselves
RESET_INFO_RE='SGX reset: (after the fault clear )?BIF_FAULT'
if [ -n "${SGXFIVE_DEBUGFS:-}" ]; then
	D=$SGXFIVE_DEBUGFS
else
	# the device appears under dri/0, dri/0000:00:02.0 and dri/128 (one device, three names); the tool's dump uses dri/0
	DL=/sys/kernel/debug/dri/0/sgx
	if ! sudo -n test -d "$DL"; then DL=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1); fi
	[ -n "$DL" ] && sudo -n test -d "$DL" || { echo "no sgx debugfs directory (dri/0/sgx or any dri/*/sgx)"; exit 1; }
	D=$DL
fi
[ -x "$T" ] || { echo "no $T (r5-render4x uses ~/sgxfive-test-rgn4: see PREFLIGHT.md)"; exit 1; }
START=$(date +%s)
RUN=$(date +%s)-$$
sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }
W=$WROOT

mark() { printf "resgx545 r5x %s %s\n" "$*" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null; }
mark_case() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null; }

dbg_cat() { sudo -n cat "$D/$1"; }
dbg_write() { # NAME VALUE: the allow-listed debugfs files only, bounded
	case "$1 $2" in
	"reset 1"|"render_rgn_arrays 0"|"render_rgn_arrays 1"|"hold_recovery Y"|"hold_recovery N") ;;
	"render_pb_pages 0x"[0-9a-f][0-9a-f]|"render_pb_pages 0x"[0-9a-f][0-9a-f][0-9a-f])
		# 0x23 (the smallest the fork takes) to 0x422 (the default and the largest: its page table sits at 0x423000)
		[ $(( $2 )) -ge $(( 0x23 )) ] && [ $(( $2 )) -le $(( 0x422 )) ] || { echo "dbg_write: $1 $2 is not in 0x23 to 0x422"; exit 7; } ;;
	*) echo "dbg_write: $1 $2 is not allowed in r5-render4x"; exit 7 ;;
	esac
	printf '%s\n' "$2" | sudo -n timeout -k 5 20 tee "$D/$1" >/dev/null
}
hold_now() { dbg_cat hold_recovery; }
set_hold() { dbg_write hold_recovery "$1"; dbg_cat hold_recovery; }
rgn_now() { dbg_cat render_rgn_arrays; }
rgn_is() { local v; v=$(rgn_now); [ -n "$v" ] && [ $(( v )) -eq "$1" ]; }
pb_now() { dbg_cat render_pb_pages; }
pb_is() { local v; v=$(pb_now); [ -n "$v" ] && [ $(( v )) -eq $(( $1 )) ]; }
# the kernel prints a debugfs x32 as 0x%08llx: written and read back NUMERICALLY
rgn_set() { dbg_write render_rgn_arrays "$1"; rgn_is "$1"; }
pb_set() { dbg_write render_pb_pages "$1"; pb_is "$1"; }
knobs_ok() { # RGN PB: hold_recovery N, render_rgn_arrays RGN and render_pb_pages PB as the row asks
	[ "$(hold_now)" = N ] && rgn_is "$1" && pb_is "$2"
}
NO_MORE_RESET=0
reset_gpu() {
	[ "$NO_MORE_RESET" = 1 ] && { echo "  (no reset: the session stopped on a fault that did not clear)"; return 1; }
	dbg_write reset 1; local r=$?
	sleep "${RESET_WAIT:-3}"
	return $r
}
regval() { awk -v r="$2" '$1 == "reg" && $2 == r { print $3 }' "$1"; }
snap() { # NAME K: debugfs regs into $JW/snapK.regs (kept as NAME.snapK.regs.gz); prints the registers; 1 if unreadable
	local f="$JW/snap$2.regs"
	sudo -n cat "$D/regs" > "$f" 2>&1
	local r=$?
	if [ "$r" -ne 0 ] || ! grep -q '^reg 0x0c04 ' "$f"; then echo "  snap $2: regs unreadable (status $r)"; return 1; fi
	echo "  snap $2: clock-status $(regval "$f" 0x0008) status $(regval "$f" 0x012c) status2 $(regval "$f" 0x0118) bif_int $(regval "$f" 0x0c04) bif_fault $(regval "$f" 0x0c08) pb $(regval "$f" 0x0724)"
	mark "snap $1 $2 $(regval "$f" 0x0c04) $(regval "$f" 0x0c08) $(regval "$f" 0x012c) $(regval "$f" 0x0118)"
	return 0
}
fault_req() { local v; v=$(regval "$1" 0x0c04); [ -n "$v" ] && echo $(( v & 0xffff )); }

preflight() {
	echo "## stage $STAGE"; echo "## uname"; uname -r
	echo "## firmware"; sha "${FW_PATH:-/lib/firmware/sgx545_ukernel.fw}" || { echo "no firmware file"; exit 1; }
	# the installed module and the loaded one must be the same build, and the build this session was prepared for (k.env)
	echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx); echo "$SRCV_FILE"
	echo "## loaded module"; SRCV_LOADED=$(sudo -n cat "${SRCV_PATH:-/sys/module/gma500_gfx/srcversion}"); echo "$SRCV_LOADED"
	[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
	[ "$SRCV_LOADED" = "$SRCV_EXPECT" ] || { echo "the loaded module ($SRCV_LOADED) is not the expected build ($SRCV_EXPECT)"; exit 1; }
	echo "## debugfs directory: $D"
	for f in reset hold_recovery regs render_param render_tadata render_pb_pages alias_skip render_rgn_arrays kpoke; do
		sudo -n test -e "$D/$f" || { echo "the loaded driver has no debugfs $f"; exit 1; }
	done
	echo "## tool"; got=$(sha "$T" | cut -d' ' -f1); echo "$got $T"
	[ "$got" = "$TOOL_SHA" ] || { echo "the tool is not the rgn4 build ($TOOL_SHA)"; exit 1; }
	echo "## knobs at start (must be the defaults of fork a2788bd8: nothing of an earlier session left)"
	h=$(dbg_cat hold_recovery); pb=$(dbg_cat render_pb_pages); as=$(dbg_cat alias_skip); ra=$(dbg_cat render_rgn_arrays)
	echo "hold_recovery=$h render_pb_pages=$pb alias_skip=$as render_rgn_arrays=$ra"
	[ -n "$ra" ] && [ $(( ra )) -eq 0 ] || { echo "render_rgn_arrays is not 0 (automatic, the default) at the start"; exit 1; }
	[ "$h" = N ] || { echo "hold_recovery is not N at the start"; exit 1; }
	[ -n "$pb" ] && [ $((pb)) -eq $((0x422)) ] || { echo "render_pb_pages is not 0x422"; exit 1; }
	[ -n "$as" ] && [ $((as)) -eq 0 ] || { echo "alias_skip is not 0"; exit 1; }
	echo "## clock"; date
	echo "## r5-render4x safety rules: see the header of lib_k.sh"
}

FATAL_STOP=0
STARTED=0
JOBPID=""
cleanup_gpu() {
	# before the preflight passed nothing of the GPU is ours (another session may hold a fault): touch nothing
	if [ "$STARTED" != 1 ]; then echo "## exit before the preflight passed: nothing touched"; return; fi
	# the three knobs back to the defaults at EVERY exit (a stop, a freeze, a fatal message included: bounded writes): a hold left
	# set would hold every later fault, a small PB would overflow every later scene, render_rgn_arrays 1 would change every context
	dbg_write hold_recovery N
	dbg_write render_pb_pages 0x422
	dbg_write render_rgn_arrays 0
	echo "## exit: hold_recovery=$(hold_now) render_pb_pages=$(pb_now) render_rgn_arrays=$(rgn_now)"
	mark "exit hold_recovery=$(hold_now) render_pb_pages=$(pb_now) render_rgn_arrays=$(rgn_now)"
	if [ "$FATAL_STOP" != 1 ]; then
		[ -n "$JOBPID" ] && wait "$JOBPID"
		reset_gpu
	fi
	finish_log
}
cleanup() {
	cleanup_gpu
	exec >&- 2>&-
	# runner.log complete before the exit: tee ends at the fifo's EOF; one bounded fallback (a single sleep, no loop) ends a tee
	# that missed it (seen once in the macOS mock, R4-A tests), so the exit status always reaches the driver
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
health_ok() { # NAME: one fill and one plain 64x64 triangle, kept; 0 if both drew exactly
	HN=$((HN + 1))
	mark "health $1 fill try $HN"
	sudo -n timeout -k 10 60 "$T" fill > "$JW/fill.$HN.out" 2>&1 </dev/null
	keep "$1.fill$HN" "$JW/fill.$HN.out"
	mark "health $1 tri try $HN"
	sudo -n timeout -k 10 60 "$T" tri > "$JW/health.$HN.out" 2>&1 </dev/null
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
# strict_health NAME: after a fault-class event the FIRST health fill and triangle must draw (DECISIONS-R5 R5-4 a: strict health
# after each); if not, the usual recovery runs and the stage stops, rc 16
strict_health() {
	sleep "${HEALTH_WAIT:-3}"
	if health_ok "$1"; then return 0; fi
	echo "## STOP: the health fill or triangle failed after $1, a 3D-side fault (strict): recovery, then stop"
	reset_gpu; sleep "${HEALTH_WAIT:-5}"
	if ! health_ok "$1"; then sleep "${HEALTH_WAIT:-5}"; health_ok "$1" || { echo "## abort: no recovery"; exit 5; }; fi
	exit 16
}
begin() {
	printf 'name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tmode\tfault_req\treset_rc\theld_msg\n' > "$KEEP/cases.tsv"
	: > "$KEEP/raw.sha256"
	JW=$WROOT/begin; mkdir -p "$JW"
	preflight
	STARTED=1
	# a clean start whatever an earlier session left armed (the reset disarms the debug switches and the kpokes)
	reset_gpu || { echo "the first debugfs reset failed"; exit 1; }
	health begin </dev/null
}
# the fault of a plain job: the first "BIF fault 0xSTAT at 0xWORD" line of its slice; bits 15:0 of STAT (decimal) and WORD
fault_int() { awk 'match($0, /BIF fault 0x[0-9a-f]+ at/) { v = substr($0, RSTART + 12, RLENGTH - 15); print v; exit }' "$1" | { read -r v; [ -n "$v" ] && echo $(( 0x$v & 0xffff )); }; }
fault_word() { awk 'match($0, /BIF fault 0x[0-9a-f]+ at 0x[0-9a-f]+/) { s = substr($0, RSTART, RLENGTH); sub(/.* at /, "", s); print s; exit }' "$1"; }
num_word() { case "$1" in 0x[0-9a-fA-F]*) [ $(( $1 )) -eq $(( $2 )) ] ;; *) return 1 ;; esac; }
# the kernel log after a marker: the slice of one job or step (taken before its knob restore and health), never a count of lines
slice_since() { sudo -n dmesg > "$JW/dmesg.all"; awk -v m="$1" 'f{print} index($0,m){f=1}' "$JW/dmesg.all"; }
# the lines of a slice that can be trouble: the reset information lines left out
bad_lines() { grep -Ev "$RESET_INFO_RE" "$@"; }
# the class of a plain job or a step from its output and slice (a fault before a hang)
classify_plain() { # OUT DMESG RC: fault | hang | ok | fail
	if bad_lines "$1" "$2" | grep -Eq "BIF fault|faulted"; then echo fault
	elif bad_lines "$1" "$2" | grep -Eq "job [0-9]+ hung|hung|timed out waiting"; then echo hang
	elif [ "$3" -eq 0 ]; then echo ok
	else echo fail; fi
}
