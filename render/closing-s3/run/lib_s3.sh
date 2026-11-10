# SPDX-License-Identifier: MIT
# lib_s3.sh: what the laptop-side S3 stage runner shares (sourced by run_stage.sh, never run).
#
# Safety rules of this runner (checked by run/guard_s3.sh and tests/run_mock.sh):
#  - debugfs is root only: EVERY access goes through `sudo -n` (dbg_cat, dbg_write, snap, the
#    preflight's `sudo -n test -e`, the xfer_ro read under regtimeline).  The mock makes the debugfs
#    directory unreadable to the user, so a bare access fails the mock run.
#  - the only debugfs files written: hold_recovery and reset (dbg_write has an allow-list), and
#    /dev/kmsg for the markers.  A held fault is ended by the kernel's own debugfs reset.  No kreg,
#    no kregnow, no kpoke write of ours, no /dev/mem write, no clock-gate register, no trc_hazard,
#    no firmware-task str, no CR_BIF_CTRL / CR_BIF_INT_STAT write (pixel E2 is not approved).
#    debugfs reset makes the KERNEL run its halt and boot sequence (sgxfive_reset: the deinit script,
#    the soft reset, CR_BIF_CTRL clear-fault, the boot writes): that is the kernel's own recovery.
#  - never a reboot, a GRUB change or a kernel build; no compile at all in S3 (S1's tool is reused).
#  - no polling or wait loop: no while/until; single fixed sleeps; one `wait PID` for a background
#    job that is itself bounded by `timeout`; each health attempt is written out one after the other.
#  - no file is deleted: each job writes into its own new directory under one mktemp directory.
set -u
STAGE=${STAGE:?lib_s3.sh: STAGE not set}
LIBDIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$LIBDIR/s3.env"
TOOL_SHA=${S3_TOOL_SHA:-$TOOL_SHA}
RT_SHA=${S3_RT_SHA:-$RT_SHA}
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-s1}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
S=${SGXFIVE_PROBE_BINS:-$HOME/s3-stage}
# one directory an attempt (ATT from the driver), never reused: no merging of attempts
KEEP=${S3_OUT:-$HOME/s3-out}/${ATT:?lib_s3.sh: ATT not set}/$STAGE
if [ -d "$KEEP" ] && [ -n "$(ls -A "$KEEP")" ]; then echo "$KEEP is not empty: an attempt is never rerun into its directory"; exit 1; fi
mkdir -p "$KEEP" || { echo "cannot create $KEEP"; exit 1; }
# everything printed from here on also goes to runner.log; with SIGPIPE ignored (run_stage.sh) a dropped
# ssh leaves tee writing the file (GNU tee -p: warn on a broken pipe, keep the file; BSD tee goes on anyway)
TEE_P=""; tee -p /dev/null < /dev/null > /dev/null 2>&1 && TEE_P=-p
WROOT=$(mktemp -d)
mkfifo "$WROOT/out.fifo" || { echo "mkfifo failed"; exit 1; }
tee $TEE_P -a "$KEEP/runner.log" < "$WROOT/out.fifo" &
TEEPID=$!
exec > "$WROOT/out.fifo" 2>&1
KMSG=${KMSG:-/dev/kmsg}
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|general protection|machine check|psb.*watchdog'
if [ -n "${SGXFIVE_DEBUGFS:-}" ]; then
	D=$SGXFIVE_DEBUGFS
else
	# the device appears under dri/0, dri/0000:00:02.0 and dri/128 (one device, three names); the
	# tool's dump_render uses dri/0, so the runner uses exactly that one and refuses without it
	DL=/sys/kernel/debug/dri/0/sgx; sudo -n test -d "$DL" || { echo "no sgx debugfs directory at $DL"; exit 1; }
	D=$DL
fi
[ -x "$T" ] || { echo "no $T (S3 reuses S1's tool: see PREFLIGHT.md)"; exit 1; }
START=$(date +%s)
RUN=$(date +%s)-$$
sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }
W=$WROOT

mark() { printf "resgx545 s3 %s %s\n" "$*" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null; }
# the case marker keeps the format of the earlier batches ("resgx545 case NAME RUN")
mark_case() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null; }

dbg_cat() { sudo -n cat "$D/$1"; }
dbg_write() { # NAME VALUE: the allow-listed debugfs files only
	case "$1" in
	hold_recovery|reset) ;;
	*) echo "dbg_write: $1 is not allowed in S3"; exit 7 ;;
	esac
	printf '%s\n' "$2" | sudo -n tee "$D/$1" >/dev/null
}
set_hold() { dbg_write hold_recovery "$1"; dbg_cat hold_recovery; }
# the kernel's own recovery (sgxfive_reset); the status of the write is the reset's result
NO_MORE_RESET=0
reset_gpu() {
	[ "$NO_MORE_RESET" = 1 ] && { echo "  (no reset: the session stopped on a fault that did not clear)"; return 1; }
	dbg_write reset 1; local r=$?
	sleep "${RESET_WAIT:-3}"
	return $r
}
regval() { awk -v r="$2" '$1 == "reg" && $2 == r { print $3 }' "$1"; }
snap() { # NAME K: debugfs regs into $JW/snapK.regs (kept as NAME.snapK.regs.gz); prints the four registers; 1 if unreadable
	local f="$JW/snap$2.regs"
	sudo -n cat "$D/regs" > "$f" 2>&1
	local r=$?
	if [ "$r" -ne 0 ] || ! grep -q '^reg 0x0c04 ' "$f"; then echo "  snap $2: regs unreadable (status $r)"; return 1; fi
	echo "  snap $2: status $(regval "$f" 0x012c) status2 $(regval "$f" 0x0118) bif_int $(regval "$f" 0x0c04) bif_fault $(regval "$f" 0x0c08)"
	mark "snap $1 $2 $(regval "$f" 0x0c04) $(regval "$f" 0x0c08) $(regval "$f" 0x012c) $(regval "$f" 0x0118)"
	return 0
}
fault_req() { local v; v=$(regval "$1" 0x0c04); [ -n "$v" ] && echo $(( v & 0xffff )); }

preflight() {
	echo "## stage $STAGE"; echo "## uname"; uname -r
	echo "## firmware"; sha "${FW_PATH:-/lib/firmware/sgx545_ukernel.fw}" || { echo "no firmware file"; exit 1; }
	echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx); echo "$SRCV_FILE"
	echo "## loaded module"; SRCV_LOADED=$(sudo -n cat "${SRCV_PATH:-/sys/module/gma500_gfx/srcversion}"); echo "$SRCV_LOADED"
	[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
	for f in reset hold_recovery regs xfer_ro render_param render_tadata render_pb_pages alias_skip; do
		sudo -n test -e "$D/$f" || { echo "the loaded driver has no debugfs $f"; exit 1; }
	done
	echo "## tool"; got=$(sha "$T" | cut -d' ' -f1); echo "$got $T"
	[ "$got" = "$TOOL_SHA" ] || { echo "the tool is not S1's ($TOOL_SHA)"; exit 1; }
	echo "## regtimeline"; got=$(sha "$RT" | cut -d' ' -f1); echo "$got $RT"
	[ "$got" = "$RT_SHA" ] || { echo "regtimeline is not S1's ($RT_SHA)"; exit 1; }
	echo "## knobs at start (must be the defaults: nothing of an earlier session left)"
	h=$(dbg_cat hold_recovery); pb=$(dbg_cat render_pb_pages); as=$(dbg_cat alias_skip)
	echo "hold_recovery=$h render_pb_pages=$pb alias_skip=$as"
	[ "$h" = N ] || { echo "hold_recovery is not N at the start"; exit 1; }
	[ -n "$pb" ] && [ $((pb)) -eq $((0x422)) ] || { echo "render_pb_pages is not 0x422"; exit 1; }
	[ -n "$as" ] && [ $((as)) -eq 0 ] || { echo "alias_skip is not 0"; exit 1; }
	echo "## clock"; date
	echo "## S3 safety rules: see the header of lib_s3.sh"
}

FATAL_STOP=0
JOBPID=""
STARTED=0
cleanup_gpu() {
	# before the preflight passed nothing of the GPU is ours (another session may hold a fault): touch nothing
	if [ "$STARTED" != 1 ]; then echo "## exit before the preflight passed: nothing touched"; return; fi
	# the knob first, whatever happened: a hold left set would hold every later fault
	dbg_write hold_recovery N
	echo "## exit: hold_recovery=$(dbg_cat hold_recovery)"
	if [ "$FATAL_STOP" != 1 ]; then
		reset_gpu
		[ -n "$JOBPID" ] && wait "$JOBPID"
	fi
	finish_log
}
cleanup() {
	cleanup_gpu
	# runner.log complete before the exit: close our end of the fifo, let tee drain it
	exec >&- 2>&-
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
tri_ok() { # one plain 64x64 triangle, kept; 0 if it drew exactly
	HN=$((HN + 1))
	mark "health $1 try $HN"
	sudo -n timeout -k 10 60 "$T" tri > "$JW/health.$HN.out" 2>&1 </dev/null
	keep "$1.health$HN" "$JW/health.$HN.out"
	grep -q "^diff: 0 of 4096" "$JW/health.$HN.out"
}
health() { # NAME: the plain triangle must draw exactly; a reset and two more attempts, written out one by one; then stop
	sleep "${HEALTH_WAIT:-3}"
	if tri_ok "$1"; then return 0; fi
	reset_gpu; sleep "${HEALTH_WAIT:-5}"
	if tri_ok "$1"; then echo "  health: recovered after a reset"; return 0; fi
	sleep "${HEALTH_WAIT:-5}"
	if tri_ok "$1"; then echo "  health: recovered on the retry"; return 0; fi
	echo "## abort: the plain triangle does not draw after a reset and a retry (the first failed recovery stops)"
	exit 5
}
begin() {
	printf 'name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tmode\tfault_req\treset_rc\theld_msg\n' > "$KEEP/cases.tsv"
	: > "$KEEP/raw.sha256"
	JW=$WROOT/begin; mkdir -p "$JW"
	preflight
	STARTED=1
	# a clean start whatever an earlier session left armed (sgxfive_debug_reset disarms the debug switches)
	reset_gpu || { echo "the first debugfs reset failed"; exit 1; }
	health begin </dev/null
}
# kernel log lines after a marker: the slice of one job (taken before its health triangles)
slice_since() { sudo -n dmesg > "$JW/dmesg.all"; awk -v m="$1" 'f{print} index($0,m){f=1}' "$JW/dmesg.all"; }
