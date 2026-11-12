# SPDX-License-Identifier: MIT
# lib_f.sh: what the laptop-side r7-faults stage runner shares (sourced by run_f.sh, never run).  From r6-held's lib_h.sh
# (closing6/r6-held/run/lib_h.sh) on the same module (fork r6-kernel 3f0b3e74, srcversion 41E2F5C7...), with round 7's laptop files:
# everything under ~/scratch/r7f/ (stage: the staged tree; out: the kept stages; run: the session's -110 ledger), the work
# directories under ONE `mktemp -d ~/scratch/tmp/r7f.XXXXXX` (never /tmp: a 991M tmpfs in RAM), each job's work directory removed
# once its files are kept and the whole mktemp directory at every exit, a free-space check (MIN_FREE_MB on ~) before each job.
# Knobs written: hold_recovery (Y and N by the held flow only) and render_rgn_arrays (1 for a row that names rgn:1, back to 0 after
# every job and at every exit).  One register written, through the kernel: CR_BIF_CTRL bit 4 (CLEAR_FAULT) by debugfs kregnow
# `0x0c00^=0x10`, always as a pair (set, then cleared), in s0's gate row (nothing held) and in a `clr` cell (while held, E826's
# write); a set left by an interrupted pair is cleared by the exit trap.
#
# Safety rules of this runner (checked by run/guard_f.sh and tests/run_mock.sh):
#  - debugfs is root only: EVERY access goes through `sudo -n` (dbg_cat, dbg_write, clr_write, snap, the preflight's `sudo -n test
#    -e`, the directory test and the glob).  The mock makes the debugfs directory unreadable to the user, so a bare access fails.
#  - the ONLY debugfs files written are `reset 1`, `render_rgn_arrays 0|1`, `hold_recovery Y|N` (dbg_write) and `kregnow
#    0x0c00^=0x10` (clr_write, bounded by BIF_ANSWER); /dev/kmsg gets the markers (an append).  `peek` and `kregnow` are read in the
#    preflight only.  No kreg, no kpoke, no other kregnow row, no bif_flush, no render_pb_pages or render_tail_room write (both only
#    read, at the defaults 0x422 and 0), no clock-gate register, no firmware-task str, no /dev/mem write.
#  - never a reboot, a boot-loader change or a kernel build; no compile at all.
#  - no polling or wait loop: no while/until; single fixed sleeps; one `wait PID` for a background job that is itself bounded by
#    `timeout -k`; each health attempt and each step of a cell is written out one after the other (no loop).
#  - files: the kept ones under ~/scratch/r7f/out/ATT/STAGE (never deleted); the ledger ~/scratch/r7f/run/minus110.ledger (appended);
#    each job works in its own new directory under one `mktemp -d ~/scratch/tmp/r7f.XXXXXX`; rm_work removes a job's directory after
#    its files are kept (and refuses any path that is not under that mktemp directory), the exit trap removes the mktemp directory
#    itself; nothing else is ever removed.  /tmp is not used.
#  - a free-space check before each job: at least MIN_FREE_MB (f.env) free on ~, else the stage stops (rc 21) before the job.
#  - the kernel log of a job or a step is the slice after its marker (never a line count); the kernel's reset information lines
#    ("SGX reset: BIF_FAULT ...", "SGX reset: after the fault clear ...") are not bad lines.
#  - a -110 (a boot with no INIT_COMPLETE) is a reading; two failed boots in a row (the second boot of one recovery), or "SGX boot:
#    BIF fault during reset", stop the session at once with no further reset (rc 26).
set -u
STAGE=${STAGE:?lib_f.sh: STAGE not set}
LIBDIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
. "$LIBDIR/f.env"
TOOL_SHA=${K_TOOL_SHA:-$TOOL_SHA}
SRCV_EXPECT=${K_SRCV_EXPECT:-$SRCV_EXPECT}
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-rgn4}
# one directory an attempt (ATT from the driver), never reused: no merging of attempts
KEEP=$HOME/scratch/r7f/out/${ATT:?lib_f.sh: ATT not set}/$STAGE
if [ -d "$KEEP" ] && [ -n "$(ls -A "$KEEP")" ]; then echo "$KEEP is not empty: an attempt is never rerun into its directory"; exit 1; fi
mkdir -p "$KEEP" "$HOME/scratch/r7f/run" || { echo "cannot create $KEEP"; exit 1; }
LEDGER=$HOME/scratch/r7f/run/minus110.ledger
TEE_P=""; tee -p /dev/null < /dev/null > /dev/null 2>&1 && TEE_P=-p
mkdir -p "$HOME/scratch/tmp" || { echo "cannot create $HOME/scratch/tmp"; exit 1; }
WROOT=$(mktemp -d "$HOME/scratch/tmp/r7f.XXXXXX") || { echo "mktemp under $HOME/scratch/tmp failed"; exit 1; }
case "$WROOT" in "$HOME"/scratch/tmp/r7f.??????) ;; *) echo "the work directory $WROOT is not ~/scratch/tmp/r7f.XXXXXX"; exit 1 ;; esac
# until the full exit trap below is set, an early exit still removes the work directory
trap 'case "$WROOT" in "$HOME"/scratch/tmp/r7f.??????) rm -rf -- "$WROOT" ;; esac' EXIT
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
[ -x "$T" ] || { echo "no $T (r7-faults uses ~/sgxfive-test-rgn4: see PREFLIGHT.md)"; exit 1; }
START=$(date +%s)
RUN=$(date +%s)-$$
sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }
W=$WROOT

mark() { printf "resgx545 r7f %s %s\n" "$*" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null; }
mark_case() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null; }

dbg_cat() { sudo -n timeout -k 5 20 cat "$D/$1"; }
dbg_write() { # NAME VALUE: the allow-listed debugfs files only, bounded; the status of the write (tee's) is returned
	case "$1 $2" in
	"reset 1"|"render_rgn_arrays 0"|"render_rgn_arrays 1"|"hold_recovery Y"|"hold_recovery N") ;;
	*) echo "dbg_write: $1 $2 is not allowed in r7-faults"; exit 7 ;;
	esac
	printf '%s\n' "$2" | sudo -n timeout -k 5 20 tee "$D/$1" >/dev/null
}
# clr_write NAME STEP: one flip of CR_BIF_CTRL bit 4 (CLEAR_FAULT) through debugfs kregnow, the only kregnow form of this session;
# its status into $JW/NAME.kw.txt; bounded (no answer within BIF_ANSWER s: E317's stall, the session stops, nothing more touched)
CLR_SET=0
clr_write() {
	local nm=$1 st=$2 r
	mark "kregnow $nm $st 0x0c00^=0x10"
	printf '%s\n' "0x0c00^=0x10" | sudo -n timeout -k 3 "$BIF_ANSWER" tee "$D/kregnow" >/dev/null 2> "$JW/kw.err"
	r=$?
	echo "$st 0x0c00^=0x10 rc $r $(head -c 80 "$JW/kw.err")" >> "$JW/$nm.kw.txt"
	echo "  kregnow $st: 0x0c00^=0x10 -> status $r"
	if [ "$r" -eq 124 ] || [ "$r" -eq 137 ]; then
		echo "## STOP: no answer within $BIF_ANSWER s from the kregnow write (E317's stall): nothing more is touched"
		NO_MORE_RESET=1; FATAL_STOP=1; exit 18
	fi
	[ "$r" -eq 0 ] && CLR_SET=$(( 1 - CLR_SET ))
	return "$r"
}
hold_now() { dbg_cat hold_recovery; }
set_hold() { dbg_write hold_recovery "$1"; dbg_cat hold_recovery; }
rgn_now() { dbg_cat render_rgn_arrays; }
rgn_is() { local v; v=$(rgn_now); [ -n "$v" ] && [ $(( v )) -eq "$1" ]; }
pb_now() { dbg_cat render_pb_pages; }
room_now() { dbg_cat render_tail_room; }
rgn_set() { dbg_write render_rgn_arrays "$1"; rgn_is "$1"; }
knobs_ok() { # RGN: hold_recovery N, render_rgn_arrays RGN, render_pb_pages 0x422 and render_tail_room 0 (never written here)
	local pb room
	pb=$(pb_now); room=$(room_now)
	[ "$(hold_now)" = N ] && rgn_is "$1" && [ -n "$pb" ] && [ $(( pb )) -eq $(( 0x422 )) ] && [ -n "$room" ] && [ $(( room )) -eq 0 ]
}
NO_MORE_RESET=0
reset_gpu() {
	[ "$NO_MORE_RESET" = 1 ] && { echo "  (no reset: the session stopped on a boot or a fault that did not clear)"; return 1; }
	dbg_write reset 1; local r=$?
	sleep "${RESET_WAIT:-3}"
	return $r
}
regval() { awk -v r="$2" '$1 == "reg" && $2 == r { print $3 }' "$1"; }
snap() { # NAME K: debugfs regs into $JW/snapK.regs; prints the registers; 1 if unreadable (bounded by BIF_ANSWER)
	local f="$JW/snap$2.regs"
	sudo -n timeout -k 3 "$BIF_ANSWER" cat "$D/regs" > "$f" 2>&1
	local r=$?
	if [ "$r" -eq 124 ] || [ "$r" -eq 137 ]; then
		echo "## STOP: no answer within $BIF_ANSWER s reading regs (E317's stall): nothing more is touched"
		NO_MORE_RESET=1; FATAL_STOP=1; exit 18
	fi
	if [ "$r" -ne 0 ] || ! grep -q '^reg 0x0c04 ' "$f"; then echo "  snap $2: regs unreadable (status $r)"; return 1; fi
	echo "  snap $2: clock-status $(regval "$f" 0x0008) status $(regval "$f" 0x012c) status2 $(regval "$f" 0x0118) bif_ctrl $(regval "$f" 0x0c00) bif_int $(regval "$f" 0x0c04) bif_fault $(regval "$f" 0x0c08) dpm_page_status $(regval "$f" 0x0724)"
	mark "snap $1 $2 $(regval "$f" 0x0c00) $(regval "$f" 0x0c04) $(regval "$f" 0x0c08) $(regval "$f" 0x012c) $(regval "$f" 0x0118)"
	return 0
}
fault_req() { local v; v=$(regval "$1" 0x0c04); [ -n "$v" ] && echo $(( v & 0xffff )); }

free_kb() { df -Pk "$HOME" | awk 'NR == 2 { print $4 }'; }
space_ok() { local k; k=$(free_kb); [ -n "$k" ] && [ "$k" -ge $(( MIN_FREE_MB * 1024 )) ]; }
rm_work() {
	case "$1" in
	"$WROOT"/?*) rm -rf -- "$1" ;;
	*) echo "rm_work: $1 is not under $WROOT: refused"; exit 1 ;;
	esac
}

preflight() {
	echo "## stage $STAGE"; echo "## uname"; uname -r
	echo "## firmware"; sha "${FW_PATH:-/lib/firmware/sgx545_ukernel.fw}" || { echo "no firmware file"; exit 1; }
	echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx); echo "$SRCV_FILE"
	echo "## loaded module"; SRCV_LOADED=$(sudo -n cat "${SRCV_PATH:-/sys/module/gma500_gfx/srcversion}"); echo "$SRCV_LOADED"
	[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
	[ "$SRCV_LOADED" = "$SRCV_EXPECT" ] || { echo "the loaded module ($SRCV_LOADED) is not the expected build ($SRCV_EXPECT)"; exit 1; }
	echo "## debugfs directory: $D"
	for f in reset hold_recovery regs render_pb_pages alias_skip render_rgn_arrays render_tail_room peek bif_flush kregnow; do
		sudo -n test -e "$D/$f" || { echo "the loaded driver has no debugfs $f (not the r6-kernel build)"; exit 1; }
	done
	echo "## peek (the module's identity only: read once, never written)"; pk=$(dbg_cat peek); echo "$pk"
	echo "$pk" | grep -Eq '^reg 0x0694 0x[0-9a-f]{8}$' || { echo "debugfs peek does not print 'reg 0x0694 0x........'"; exit 1; }
	echo "## kregnow (read: the BIF rows are listed)"; dbg_cat kregnow > "$WROOT/kregnow.pre" 2>&1
	grep -q '^0x0c00 0x' "$WROOT/kregnow.pre" || { echo "debugfs kregnow does not list 0x0c00 (BIF_CTRL)"; exit 1; }
	echo "## tool"; got=$(sha "$T" | cut -d' ' -f1); echo "$got $T"
	[ "$got" = "$TOOL_SHA" ] || { echo "the tool is not the rgn4 build ($TOOL_SHA)"; exit 1; }
	echo "## knobs at start (must be the defaults of fork r6-kernel: nothing of an earlier session left)"
	h=$(dbg_cat hold_recovery); pb=$(dbg_cat render_pb_pages); as=$(dbg_cat alias_skip); ra=$(dbg_cat render_rgn_arrays); tr=$(dbg_cat render_tail_room)
	echo "hold_recovery=$h render_pb_pages=$pb alias_skip=$as render_rgn_arrays=$ra render_tail_room=$tr"
	[ -n "$ra" ] && [ $(( ra )) -eq 0 ] || { echo "render_rgn_arrays is not 0 (automatic, the default) at the start"; exit 1; }
	[ "$h" = N ] || { echo "hold_recovery is not N at the start"; exit 1; }
	[ -n "$pb" ] && [ $((pb)) -eq $((0x422)) ] || { echo "render_pb_pages is not 0x422"; exit 1; }
	[ -n "$as" ] && [ $((as)) -eq 0 ] || { echo "alias_skip is not 0"; exit 1; }
	[ -n "$tr" ] && [ $((tr)) -eq 0 ] || { echo "render_tail_room is not 0 (automatic, the default)"; exit 1; }
	echo "## free space on ~: $(free_kb) KiB (at least $MIN_FREE_MB MiB)"
	space_ok || { echo "less than $MIN_FREE_MB MiB free on ~"; exit 21; }
	echo "## timed-out boots so far in this session (the ledger): $(used_110) of $BUDGET_110"
	[ "$(used_110)" -lt "$BUDGET_110" ] || { echo "the session's budget of $BUDGET_110 timed-out boots is spent: nothing runs"; exit 25; }
	echo "## work directory: $WROOT"
	echo "## clock"; date
	echo "## r7-faults safety rules: see the header of lib_f.sh"
}

FATAL_STOP=0
STARTED=0
JOBPID=""
cleanup_gpu() {
	if [ "$STARTED" != 1 ]; then echo "## exit before the preflight passed: nothing touched"; return; fi
	# an interrupted clr pair: clear the bit again (the only register this session sets), unless the laptop stopped answering
	if [ "$CLR_SET" = 1 ] && [ "$FATAL_STOP" != 1 ]; then clr_write exit clear; fi
	# the two knobs back to the defaults at EVERY exit (bounded writes): a hold left set would hold every later fault,
	# render_rgn_arrays 1 would change every context
	dbg_write hold_recovery N
	dbg_write render_rgn_arrays 0
	echo "## exit: hold_recovery=$(hold_now) render_rgn_arrays=$(rgn_now) render_pb_pages=$(pb_now) render_tail_room=$(room_now)"
	mark "exit hold_recovery=$(hold_now) render_rgn_arrays=$(rgn_now)"
	if [ "$FATAL_STOP" != 1 ]; then
		[ -n "$JOBPID" ] && wait "$JOBPID"
		reset_gpu
	fi
	finish_log
}
cleanup() {
	cleanup_gpu
	exec >&- 2>&-
	( sleep "${TEE_GRACE:-10}"; kill "$TEEPID" 2>/dev/null ) </dev/null >/dev/null 2>&1 &
	wait "$TEEPID"
	case "$WROOT" in "$HOME"/scratch/tmp/r7f.??????) rm -rf -- "$WROOT" ;; esac
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
# strict_health NAME: after a cell or a hang the FIRST health fill and triangle must draw (the plan's stop rule 1); if not, the
# usual recovery runs and the session stops, rc 16
strict_health() {
	sleep "${HEALTH_WAIT:-3}"
	if health_ok "$1"; then return 0; fi
	echo "## STOP: the health fill or triangle failed after $1 (strict): recovery, then stop"
	reset_gpu; sleep "${HEALTH_WAIT:-5}"
	if ! health_ok "$1"; then sleep "${HEALTH_WAIT:-5}"; health_ok "$1" || { echo "## abort: no recovery"; exit 5; }; fi
	exit 16
}
# the kernel log after a marker: the slice of one job or step, never a count of lines
slice_since() { sudo -n dmesg > "$JW/dmesg.all"; awk -v m="$1" 'f{print} index($0,m){f=1}' "$JW/dmesg.all"; }
bad_lines() { grep -Ev "$RESET_INFO_RE" "$@"; }
classify_plain() { # OUT DMESG RC: fault | hang | ok | fail
	if bad_lines "$1" "$2" | grep -Eq "BIF fault|faulted"; then echo fault
	elif bad_lines "$1" "$2" | grep -Eq "job [0-9]+ hung|hung|timed out waiting"; then echo hang
	elif [ "$3" -eq 0 ]; then echo ok
	else echo fail; fi
}
# boots FILE: the boots of a slice in order, one letter each: U (EDM up) or T (no INIT_COMPLETE: the -110)
boots() { awk '/SGX boot: EDM up after/ { s = s "U" } /SGX boot: no INIT_COMPLETE/ { s = s "T" } END { print s }' "$1"; }
# boot_dead FILE: 0 (true) if the slice shows two failed boots in a row (the second boot of one recovery failed) or "SGX boot: BIF
# fault during reset": the session stops at once (rc 26)
boot_dead() { case "$(boots "$1")" in *TT*) return 0 ;; esac; grep -q 'SGX boot: BIF fault during reset' "$1"; }
# word_problem FILE: a line naming what the plan's stop rule 2 forbids in a slice, or nothing: a "BIF fault" line whose status is not
# 0x90004 or whose word goes through list 15; in a timed-out boot's register dump (after "no INIT_COMPLETE", up to "recovery
# failed") reg 0xc04 not 0x000d0004, or reg 0xc08 outside pages 0x10000-0x10fff and 0x20000-0x20fff, or through list 15
word_problem() {
	awk '
	match($0, /BIF fault 0x[0-9a-f]+ at 0x[0-9a-f]+/) {
		s = substr($0, RSTART, RLENGTH); split(s, a, " ")
		if (a[3] != "0x90004") { print "fault status " a[3]; exit }
		if (substr(a[5], length(a[5])) == "f") { print "fault through list 15: " a[5]; exit }
	}
	/SGX boot: no INIT_COMPLETE/ { dump = 1; next }
	/recovery failed/ { dump = 0 }
	dump && /reg 0xc04 = / { v = $NF; if (v != "0x000d0004") { print "timed-out boot dump BIF_INT_STAT " v; exit } }
	dump && /reg 0xc08 = / { v = $NF; p = substr(v, 3, 5)
		if (substr(v, length(v)) == "f") { print "timed-out boot dump BIF_FAULT through list 15: " v; exit }
		if (p !~ /^(10|20)[0-9a-f][0-9a-f][0-9a-f]$/) { print "timed-out boot dump BIF_FAULT outside the two heaps: " v; exit } }
	' "$1"
}
# the ledger of timed-out boots: one line "ATT STAGE ROW N" per row that had any, every attempt of the session
used_110() { if [ -f "$LEDGER" ]; then awk '{ n += $4 } END { print n + 0 }' "$LEDGER"; else echo 0; fi; }
STAGE110=0
ledger_add() { # NAME N
	[ "$2" -gt 0 ] || return 0
	printf '%s %s %s %s\n' "$ATT" "$STAGE" "$1" "$2" >> "$LEDGER"
	STAGE110=$(( STAGE110 + $2 ))
	printf '%s\n' "$STAGE110" > "$KEEP/minus110.count"
}
# row_close NAME: the row's whole slice (from its row marker, before its reset, to now: job, steps, health), kept; the dead-boot
# check (rc 26), the -110 count into the ledger, and the word check (its line, or nothing, in ROW_WORD)
ROW_WORD=""
row_close() {
	local nm=$1 n
	slice_since "resgx545 r7f row $nm $RUN" > "$JW/$nm.row.dmesg"
	keep "$nm" "$JW/$nm.row.dmesg" ".row.dmesg"
	n=$(boots "$JW/$nm.row.dmesg" | tr -cd T | wc -c | tr -d ' ')
	ledger_add "$nm" "$n"
	echo "  boots in the row: $(boots "$JW/$nm.row.dmesg") ($n timed out); session total $(used_110) of $BUDGET_110"
	mark "minus110 $nm $n total $(used_110)"
	if boot_dead "$JW/$nm.row.dmesg"; then
		echo "## STOP: two failed boots in a row, or a BIF fault during the reset, in $nm: no further reset (PREFLIGHT.md)"
		NO_MORE_RESET=1; FATAL_STOP=1; exit 26
	fi
	ROW_WORD=$(word_problem "$JW/$nm.row.dmesg")
	[ -z "$ROW_WORD" ] || echo "  word problem in $nm: $ROW_WORD"
	return 0
}
# dead_check FILE WHAT: the early form, right after a held reset or a step
dead_check() {
	if boot_dead "$1"; then
		echo "## STOP: two failed boots in a row, or a BIF fault during the reset, after $2: no further reset (PREFLIGHT.md)"
		NO_MORE_RESET=1; FATAL_STOP=1; exit 26
	fi
	return 0
}
begin() {
	printf 'name\tstage\tset\trisk\tknobs\trt\targs\trc\tclass\tmode\tfault_req\treset_rc\theld_msg\n' > "$KEEP/cases.tsv"
	: > "$KEEP/raw.sha256"
	printf '0\n' > "$KEEP/minus110.count"
	JW=$WROOT/begin; mkdir -p "$JW"
	preflight
	STARTED=1
	mark "row begin"
	reset_gpu || { echo "the first debugfs reset failed"; exit 1; }
	health begin </dev/null
	row_close begin
	rm_work "$JW"
}
