# SPDX-License-Identifier: MIT
# lib_r5.sh: what the laptop-side R5-pixel stage runner shares (sourced by run_stage.sh, never run).
# R3-pixel's lib_r3.sh (built from R2-pixel's lib_r2.sh) without held-fault machinery (no fault is expected in R5-pixel: any fault
# or hang stops the stage), the STATUS2 reads of R2-geo (knob s2), tool ~/sgxfive-test-rgn4 on the rgn4 module.
#
# Safety rules of this runner (checked by run/guard_r5.sh and tests/run_mock.sh):
#  - debugfs is root only: EVERY access goes through `sudo -n` (dbg_cat, dbg_write, snap, the preflight's
#    `sudo -n test -e`, the directory test and the glob).  The mock makes the debugfs directory unreadable to the user,
#    so a bare access fails the mock run.
#  - the only debugfs file written is reset (dbg_write has an allow-list: the kernel's own reset), and /dev/kmsg for the
#    markers.  hold_recovery is only READ (it must be N).  No kreg, no kregnow, no kpoke, no /dev/mem write, no clock-gate
#    register, no trc_hazard, no firmware-task str, no register write at all.  regtimeline (read-only, /dev/mem reads of
#    0x0008, 0x0118, 0x012c) is the only other reader.
#  - never a reboot, a boot-loader change or a kernel build; no compile at all (the rgn4 tool and regtimeline are reused,
#    pinned by sha256 in r5.env: a mismatch stops the preflight, nothing is rebuilt).
#  - no polling or wait loop: no while/until; single fixed sleeps; one `wait PID` for a background job that is itself
#    bounded by `timeout -k`; each health attempt is written out one after the other.  The job table is walked by line number (for ... seq),
#    never with `set -f`: a disabled glob once stopped the dumps from being kept.
#  - no file is deleted: each job writes into its own new directory under one mktemp directory.
set -u
STAGE=${STAGE:?lib_r5.sh: STAGE not set}
LIBDIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$LIBDIR/r5.env"
TOOL_SHA=${R5_TOOL_SHA:-$TOOL_SHA}
RT_SHA=${R5_RT_SHA:-$RT_SHA}
SRCV_EXPECT=${R5_SRCV_EXPECT:-$SRCV_EXPECT}
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-rgn4}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
S=${SGXFIVE_PROBE_BINS:-$HOME/r5p-stage}
# one directory an attempt (ATT from the driver), never reused: no merging of attempts
KEEP=${R5_OUT:-$HOME/r5p-out}/${ATT:?lib_r5.sh: ATT not set}/$STAGE
if [ -d "$KEEP" ] && [ -n "$(ls -A "$KEEP")" ]; then echo "$KEEP is not empty: an attempt is never rerun into its directory"; exit 1; fi
mkdir -p "$KEEP" || { echo "cannot create $KEEP"; exit 1; }
# everything printed from here on also goes to runner.log; with SIGPIPE ignored (run_stage.sh) a dropped ssh leaves tee
# writing the file (GNU tee -p: warn on a broken pipe, keep the file; BSD tee goes on anyway)
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
	# the device appears under dri/0, dri/0000:00:02.0 and dri/128 (one device, three names): never "exactly one".
	# The tool's dump_render uses dri/0, so that one is preferred; else the first of dri/*/sgx (the glob runs under sudo)
	DL=/sys/kernel/debug/dri/0/sgx
	if ! sudo -n test -d "$DL"; then DL=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1); fi
	[ -n "$DL" ] && sudo -n test -d "$DL" || { echo "no sgx debugfs directory (dri/0/sgx or any dri/*/sgx)"; exit 1; }
	D=$DL
fi
[ -x "$T" ] || { echo "no $T (R5-pixel needs the rgn4 tool: see PREFLIGHT.md)"; exit 1; }
START=$(date +%s)
RUN=$(date +%s)-$$
sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }
W=$WROOT

mark() { printf "resgx545 r5p %s %s\n" "$*" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null; }
# the case marker keeps the format of the earlier batches ("resgx545 case NAME RUN")
mark_case() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null; }

dbg_cat() { sudo -n cat "$D/$1"; }
dbg_write() { # NAME VALUE: the allow-listed debugfs files only
	case "$1" in
	reset) ;;
	*) echo "dbg_write: $1 is not allowed in R5-pixel"; exit 7 ;;
	esac
	printf '%s\n' "$2" | sudo -n tee "$D/$1" >/dev/null
}
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
# STATUS2 (CR_EVENT_STATUS2, 0x0118) of a debugfs regs file as a number; nothing if unreadable
status2_of() { local v; v=$(regval "$1" 0x0118); [ -n "$v" ] && echo $(( v )); }
fault_req() { local v; v=$(regval "$1" 0x0c04); [ -n "$v" ] && echo $(( v & 0xffff )); }

preflight() {
	echo "## stage $STAGE"; echo "## uname"; uname -r
	echo "## firmware"; sha "${FW_PATH:-/lib/firmware/sgx545_ukernel.fw}" || { echo "no firmware file"; exit 1; }
	# the installed module and the loaded one must be the same build (S3: srcversion), whatever the debugfs says
	echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx); echo "$SRCV_FILE"
	echo "## loaded module"; SRCV_LOADED=$(sudo -n cat "${SRCV_PATH:-/sys/module/gma500_gfx/srcversion}"); echo "$SRCV_LOADED"
	[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
	# and it is the build this session was prepared for (the rgn4 module of fork a2788bd8, srcversion 99CD90DA26E3AFF9C450517; r5.env)
	[ "$SRCV_LOADED" = "$SRCV_EXPECT" ] || { echo "the loaded module ($SRCV_LOADED) is not the expected build ($SRCV_EXPECT)"; exit 1; }
	echo "## debugfs directory: $D"
	for f in reset hold_recovery regs render_param render_tadata render_pb_pages alias_skip; do
		sudo -n test -e "$D/$f" || { echo "the loaded driver has no debugfs $f"; exit 1; }
	done
	echo "## tool"; got=$(sha "$T" | cut -d' ' -f1); echo "$got $T"
	[ "$got" = "$TOOL_SHA" ] || { echo "the tool is not the pinned rgn4 tool ($TOOL_SHA)"; exit 1; }
	if [ "${NEED_RT:-1}" = 1 ]; then
		echo "## regtimeline"; got=$(sha "$RT" | cut -d' ' -f1); echo "$got $RT"
		[ "$got" = "$RT_SHA" ] || { echo "regtimeline is not the staged one ($RT_SHA)"; exit 1; }
	fi
	echo "## knobs at start (must be the defaults: nothing of an earlier session left)"
	h=$(dbg_cat hold_recovery); pb=$(dbg_cat render_pb_pages); as=$(dbg_cat alias_skip)
	echo "hold_recovery=$h render_pb_pages=$pb alias_skip=$as"
	[ "$h" = N ] || { echo "hold_recovery is not N at the start"; exit 1; }
	[ -n "$pb" ] && [ $((pb)) -eq $((0x422)) ] || { echo "render_pb_pages is not 0x422"; exit 1; }
	[ -n "$as" ] && [ $((as)) -eq 0 ] || { echo "alias_skip is not 0"; exit 1; }
	echo "## clock"; date
	echo "## R5-pixel safety rules: see the header of lib_r5.sh"
}

FATAL_STOP=0
STARTED=0
cleanup_gpu() {
	# before the preflight passed nothing of the GPU is ours (another session may hold a fault): touch nothing
	if [ "$STARTED" != 1 ]; then echo "## exit before the preflight passed: nothing touched"; return; fi
	echo "## exit: hold_recovery=$(dbg_cat hold_recovery)"
	if [ "$FATAL_STOP" != 1 ]; then reset_gpu; fi
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
