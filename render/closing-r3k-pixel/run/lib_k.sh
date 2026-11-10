# SPDX-License-Identifier: MIT
# lib_k.sh: what the laptop-side R3K-pixel (kernel-batch session K2) stage runner shares (sourced by run_stage.sh, never run).
# Built from R2-pixel's lib_r2.sh (held jobs, fault limit) with R3-pixel's conventions (the module pin, attempts) and the
# new module's debugfs files: render_rgn_arrays (a row knob), kregnow (the BIF rows only) and the par kpoke space (the tool
# writes it, from a table row of k-pb).
#
# Safety rules of this runner (checked by run/guard_k.sh and tests/run_mock.sh):
#  - debugfs is root only: EVERY access goes through `sudo -n` (dbg_cat, dbg_write, snap, the preflight's
#    `sudo -n test -e`, the directory test and the glob).  The mock makes the debugfs directory unreadable to the user,
#    so a bare access fails the mock run.
#  - the only debugfs files written: hold_recovery, reset, render_rgn_arrays (1 or 4 only) and, in bif_write alone,
#    kregnow with exactly two forms (0x0c04=VALUE, VALUE without bit 19 and not 0x0c00 related; 0x0c00^=0x10), and /dev/kmsg
#    for the markers.  A held fault is ended by the kernel's own debugfs reset.  No kreg, no other kregnow row (no clear
#    register, no enable, no clock gate), no kpoke write of ours (the tool writes the par pokes of k-pb), no /dev/mem write, no
#    firmware-task str, no register write beyond those two.  Every write to the BIF is bounded (timeout -k, BIF_ANSWER s) and
#    a laptop that does not answer stops the session (rc 18, E317).  render_rgn_arrays is restored to 1 at every exit.
#  - never a reboot, a boot-loader change or a kernel build; no compile at all (R1's tool and regtimeline are reused).
#  - no polling or wait loop: no while/until; single fixed sleeps; one `wait PID` for a background job that is itself
#    bounded by `timeout -k`; each health attempt is written out one after the other.  The job table is walked by line number (for ... seq),
#    never with `set -f`: a disabled glob once stopped the dumps from being kept.
#  - no file is deleted: each job writes into its own new directory under one mktemp directory.
set -u
STAGE=${STAGE:?lib_k.sh: STAGE not set}
LIBDIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$LIBDIR/k.env"
TOOL_SHA=${K_TOOL_SHA:-$TOOL_SHA}
RT_SHA=${K_RT_SHA:-$RT_SHA}
SRCV_EXPECT=${K_SRCV_EXPECT:-$SRCV_EXPECT}
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-r1}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
S=${SGXFIVE_PROBE_BINS:-$HOME/r3kpx-stage}
# one directory an attempt (ATT from the driver), never reused: no merging of attempts
KEEP=${K_OUT:-$HOME/r3kpx-out}/${ATT:?lib_k.sh: ATT not set}/$STAGE
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
[ -x "$T" ] || { echo "no $T (R3K reuses R1's tool: see PREFLIGHT.md)"; exit 1; }
START=$(date +%s)
RUN=$(date +%s)-$$
sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }
W=$WROOT

mark() { printf "resgx545 r3k %s %s\n" "$*" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null; }
# the case marker keeps the format of the earlier batches ("resgx545 case NAME RUN")
mark_case() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null; }

dbg_cat() { sudo -n cat "$D/$1"; }
dbg_write() { # NAME VALUE: the allow-listed debugfs files only, every write bounded
	case "$1" in
	hold_recovery|reset) ;;
	render_rgn_arrays) case "$2" in 1|4) ;; *) echo "dbg_write: render_rgn_arrays $2 is not 1 or 4"; exit 7 ;; esac ;;
	*) echo "dbg_write: $1 is not allowed in R3K"; exit 7 ;;
	esac
	printf '%s\n' "$2" | sudo -n timeout -k 5 20 tee "$D/$1" >/dev/null
}
set_hold() { dbg_write hold_recovery "$1"; dbg_cat hold_recovery; }
# render_rgn_arrays (the knob of Q140; contexts created from now on): written and read back NUMERICALLY (the kernel prints
# 0x00000004)
rgn_now() { dbg_cat render_rgn_arrays; }
rgn_is() { local v; v=$(rgn_now); [ -n "$v" ] && [ $(( v )) -eq "$1" ]; }
set_rgn() { # N: write N unless it is already N, read back; 0 if the knob reads N
	if rgn_is "$1"; then return 0; fi
	dbg_write render_rgn_arrays "$1"
	rgn_is "$1"
}
# The two forms of host write the BIF rows use (decision R3-K4): the unset-bit / set-bits write of CR_BIF_INT_STAT and the
# flip of CR_BIF_CTRL bit 4 (CLEAR_FAULT).  Nothing else reaches debugfs kregnow; the value of an INT_STAT write never
# has bit 19 (the idle bit).  Bounded: a laptop that does not answer within BIF_ANSWER s after a write ends the session.
BIF_STALL=0
bif_write() { # NAME STEP SPEC: one kregnow write; status of the write on stdout of the caller's kw file
	local nm=$1 st=$2 spec=$3
	case "$spec" in
	0x0c04=0x[0-9a-f]*) case "$spec" in *[!0-9a-fx=]*) echo "bif_write: bad value $spec"; exit 7 ;; esac
		[ $(( ${spec#*=} & 0x80000 )) -eq 0 ] || { echo "bif_write: $spec has bit 19"; exit 7; } ;;
	0x0c00^=0x10) ;;
	*) echo "bif_write: $spec is not allowed in R3K"; exit 7 ;;
	esac
	mark "kregnow $nm $st $spec"
	printf '%s\n' "$spec" | sudo -n timeout -k 3 "$BIF_ANSWER" tee "$D/kregnow" >/dev/null
	local r=$?
	echo "$st $spec rc $r" >> "$JW/kw.txt"
	echo "  kregnow $st: $spec -> status $r"
	if [ "$r" -eq 124 ] || [ "$r" -eq 137 ]; then
		echo "## STOP: no answer within $BIF_ANSWER s from the kregnow write $spec (E317's stall): nothing more is touched"
		BIF_STALL=1; FATAL_STOP=1; exit 18
	fi
	return 0
}
# the same bound for the registers read after a BIF write
snapb() { # NAME K: debugfs regs into $JW/snapK.regs, bounded; the laptop not answering stops the session
	local f="$JW/snap$2.regs"
	sudo -n timeout -k 3 "$BIF_ANSWER" cat "$D/regs" > "$f" 2>&1
	local r=$?
	if [ "$r" -eq 124 ] || [ "$r" -eq 137 ]; then
		echo "## STOP: no answer within $BIF_ANSWER s reading regs after a BIF write (E317's stall): nothing more is touched"
		BIF_STALL=1; FATAL_STOP=1; exit 18
	fi
	if [ "$r" -ne 0 ] || ! grep -q '^reg 0x0c04 ' "$f"; then echo "  snap $2: regs unreadable (status $r)"; return 1; fi
	echo "  snap $2: status $(regval "$f" 0x012c) status2 $(regval "$f" 0x0118) bif_ctrl $(regval "$f" 0x0c00) bif_int $(regval "$f" 0x0c04) bif_fault $(regval "$f" 0x0c08)"
	mark "snap $1 $2 $(regval "$f" 0x0c00) $(regval "$f" 0x0c04) $(regval "$f" 0x0c08)"
	return 0
}
# one bif row (held fault or idle): the four writes with a regs read after each, then the watch.  JW is the job's directory.
bif_seq() { # NAME
	local nm=$1 v0 setv
	: > "$JW/kw.txt"
	snapb "$nm" b0 || { echo "## STOP: registers unreadable before the BIF writes of $nm"; exit 12; }
	v0=$(regval "$JW/snapb0.regs" 0x0c04)
	[ -n "$v0" ] || { echo "## STOP: CR_BIF_INT_STAT unreadable before the BIF writes of $nm"; exit 12; }
	setv=$(printf '0x%x' $(( v0 & ~0x80000 & 0xffffffff )))
	echo "  BIF_INT_STAT before the writes $v0: the set bits written back are $setv (bit 19, the idle bit, left out)"
	echo "set $setv" >> "$JW/kw.txt"
	bif_write "$nm" 1 "0x0c04=0x1"; snapb "$nm" b1
	bif_write "$nm" 2 "0x0c04=$setv"; snapb "$nm" b2
	bif_write "$nm" 3 "0x0c00^=0x10"; snapb "$nm" b3
	bif_write "$nm" 4 "0x0c00^=0x10"; snapb "$nm" b4
	sleep "$BIF_WATCH"
	snapb "$nm" b5
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
fault_req() { local v; v=$(regval "$1" 0x0c04); [ -n "$v" ] && echo $(( v & 0xffff )); }

preflight() {
	echo "## stage $STAGE"; echo "## uname"; uname -r
	echo "## firmware"; sha "${FW_PATH:-/lib/firmware/sgx545_ukernel.fw}" || { echo "no firmware file"; exit 1; }
	# the installed module and the loaded one must be the same build (S3: srcversion), whatever the debugfs says
	echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx); echo "$SRCV_FILE"
	echo "## loaded module"; SRCV_LOADED=$(sudo -n cat "${SRCV_PATH:-/sys/module/gma500_gfx/srcversion}"); echo "$SRCV_LOADED"
	[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
	# and it is the build this session was prepared for (the kernel batch's module: k.env)
	[ "$SRCV_LOADED" = "$SRCV_EXPECT" ] || { echo "the loaded module ($SRCV_LOADED) is not the expected build ($SRCV_EXPECT)"; exit 1; }
	echo "## debugfs directory: $D"
	for f in reset hold_recovery regs render_param render_tadata render_pb_pages alias_skip render_rgn_arrays kregnow kpoke kicker; do
		sudo -n test -e "$D/$f" || { echo "the loaded driver has no debugfs $f"; exit 1; }
	done
	echo "## tool"; got=$(sha "$T" | cut -d' ' -f1); echo "$got $T"
	[ "$got" = "$TOOL_SHA" ] || { echo "the tool is not R1's ($TOOL_SHA)"; exit 1; }
	if [ "${NEED_RT:-1}" = 1 ]; then
		echo "## regtimeline"; got=$(sha "$RT" | cut -d' ' -f1); echo "$got $RT"
		[ "$got" = "$RT_SHA" ] || { echo "regtimeline is not the staged one ($RT_SHA)"; exit 1; }
	fi
	echo "## knobs at start (must be the defaults: nothing of an earlier session left)"
	h=$(dbg_cat hold_recovery); pb=$(dbg_cat render_pb_pages); as=$(dbg_cat alias_skip); ra=$(dbg_cat render_rgn_arrays)
	echo "hold_recovery=$h render_pb_pages=$pb alias_skip=$as render_rgn_arrays=$ra"
	[ -n "$ra" ] && [ $(( ra )) -eq 1 ] || { echo "render_rgn_arrays is not 1 at the start"; exit 1; }
	# the kregnow rows of the BIF (read: no write; the clear registers are write-only and not listed)
	sudo -n cat "$D/kregnow" > "$WROOT/kregnow.pre" 2>&1
	grep -q '^0x0c00 ' "$WROOT/kregnow.pre" && grep -q '^0x0c04 ' "$WROOT/kregnow.pre" || { echo "debugfs kregnow lists no 0x0c00 and 0x0c04 rows (the loaded driver is not the kernel batch's)"; exit 1; }
	echo "## kregnow rows: $(grep -c '^0x' "$WROOT/kregnow.pre")"
	[ "$h" = N ] || { echo "hold_recovery is not N at the start"; exit 1; }
	[ -n "$pb" ] && [ $((pb)) -eq $((0x422)) ] || { echo "render_pb_pages is not 0x422"; exit 1; }
	[ -n "$as" ] && [ $((as)) -eq 0 ] || { echo "alias_skip is not 0"; exit 1; }
	echo "## clock"; date
	echo "## R3K safety rules: see the header of lib_k.sh"
}

FATAL_STOP=0
JOBPID=""
STARTED=0
cleanup_gpu() {
	# before the preflight passed nothing of the GPU is ours (another session may hold a fault): touch nothing
	if [ "$STARTED" != 1 ]; then echo "## exit before the preflight passed: nothing touched"; return; fi
	# the knobs first, whatever happened: a hold left set would hold every later fault, and render_rgn_arrays 4 would change
	# every later context (the knob must be 1 at the end of the stage and after any stop)
	dbg_write hold_recovery N
	dbg_write render_rgn_arrays 1
	echo "## exit: hold_recovery=$(dbg_cat hold_recovery) render_rgn_arrays=$(rgn_now)"
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
