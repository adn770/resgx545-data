# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# lib_kit.sh: the laptop side of a closing session built with the session kit (tools/closing/kit,
# HACKING.md "Session kit"); sourced by run_stage.sh, never run. The session declares its env in
# session.toml; session.py writes it as run/session.env, which this file sources.
#
# Safety rules (session.py guard checks them, the mock runs them under env -i):
#  - every laptop file under ~/scratch/$PREFIX/ (stage, out, run); work directories under ONE
#    `mktemp -d ~/scratch/tmp/$PREFIX.XXXXXX` (never /tmp: a 991 MiB tmpfs in RAM; sudo drops
#    TMPDIR), each job's removed once its files are kept, the whole one at every exit;
#  - debugfs only through `sudo -n`; the only debugfs writes are `reset 1` and the knobs
#    session.toml declares, to the values it allows, read back after each write and restored to
#    their defaults after every job and by the exit trap; kernel-log markers are appended;
#  - every laptop command that can block is bounded by `timeout -k`; no wait loop (no while or
#    until), single fixed sleeps whose length the mock sets to 0;
#  - at least MIN_FREE_MB free on ~ before each job; the kernel log of a job is its slice after
#    its own marker, never a count of lines; no reboot, boot loader, kernel build or compile.
set -u
STAGE=${STAGE:?lib_kit.sh: STAGE not set}
KIT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
STAGED=$(dirname "$KIT")
. "$STAGED/run/session.env"
SRCV_EXPECT=${KIT_SRCV_EXPECT:-$SRCV_EXPECT}
BASE=$HOME/scratch/$PREFIX
KEEP=$BASE/out/${ATT:?lib_kit.sh: ATT not set}/$STAGE
if [ -d "$KEEP" ] && [ -n "$(ls -A "$KEEP")" ]; then echo "$KEEP is not empty: an attempt is never rerun into its directory"; exit 1; fi
mkdir -p "$KEEP" "$BASE/run" "$HOME/scratch/tmp" || { echo "cannot create $KEEP or ~/scratch/tmp"; exit 1; }
WROOT=$(mktemp -d "$HOME/scratch/tmp/$PREFIX.XXXXXX") || { echo "mktemp under ~/scratch/tmp failed"; exit 1; }
case "$WROOT" in "$HOME/scratch/tmp/$PREFIX."??????) ;; *) echo "unexpected work directory $WROOT"; exit 1 ;; esac
# until the full exit trap is set, an early exit still removes the work directory
trap 'case "$WROOT" in "$HOME/scratch/tmp/$PREFIX."??????) rm -rf -- "$WROOT" ;; esac' EXIT
# everything printed from here on also goes to runner.log; SIGPIPE is ignored (run_stage.sh), so a
# dropped ssh leaves tee writing it
TEE_P=""; tee -p /dev/null < /dev/null > /dev/null 2>&1 && TEE_P=-p
mkfifo "$WROOT/out.fifo" || { echo "mkfifo failed"; exit 1; }
tee $TEE_P -a "$KEEP/runner.log" < "$WROOT/out.fifo" &
TEEPID=$!
exec > "$WROOT/out.fifo" 2>&1
KMSG=${KIT_KMSG:-/dev/kmsg}
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|general protection|machine check|psb.*watchdog'
RESET_INFO_RE='SGX reset: (after the fault clear )?BIF_FAULT'
FAULT_RE=${FAULT_RE:-'BIF fault|faulted'}
HANG_RE=${HANG_RE:-'job [0-9]+ hung|hung|timed out waiting'}
if [ -n "${KIT_DEBUGFS:-}" ]; then
	D=$KIT_DEBUGFS
else
	DL=/sys/kernel/debug/dri/0/sgx
	if ! sudo -n test -d "$DL"; then DL=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1); fi
	[ -n "$DL" ] && sudo -n test -d "$DL" || { echo "no sgx debugfs directory (dri/0/sgx or any dri/*/sgx)"; exit 1; }
	D=$DL
fi
START=$(date +%s)
RUN=$(date +%s)-$$
W=$WROOT
JW=$WROOT
sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }

# ---- tools ------------------------------------------------------------------------------------
tool_path() { local v="TOOL_$1_PATH"; printf '%s/%s\n' "$HOME" "${!v}"; }
tool_sha() { local o="KIT_TOOL_SHA_$1" v="TOOL_$1_SHA"; printf '%s\n' "${!o:-${!v}}"; }

# ---- markers ----------------------------------------------------------------------------------
mark() { printf "resgx545 %s %s %s\n" "$PREFIX" "$*" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null; }
mark_case() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null; }

# ---- debugfs: reads, the allowed writes, the knobs ---------------------------------------------
dbg_cat() { sudo -n timeout -k 5 20 cat "$D/$1"; }
knob_allows() { # NAME VALUE: 0 if session.toml lets a row write VALUE to NAME
	local k v vals="KNOB_$1_VALUES"
	for k in $KNOBS; do
		[ "$k" = "$1" ] || continue
		for v in ${!vals}; do [ "$v" = "$2" ] && return 0; done
	done
	return 1
}
dbg_write() { # NAME VALUE: `reset 1` or a declared knob value only, bounded; the write's status
	if [ "$1 $2" != "reset 1" ] && ! knob_allows "$1" "$2"; then
		echo "dbg_write: $1 $2 is not allowed in $PREFIX (session.toml [knobs])"; exit 7
	fi
	printf '%s\n' "$2" | sudo -n timeout -k 5 20 tee "$D/$1" >/dev/null
}
same_value() { # A B: equal as numbers when both are numbers (the kernel prints 0x%08x), else as text
	case "$1$2" in *[!0-9a-fA-Fx]*) [ "$1" = "$2" ] ;; *) [ -n "$1" ] && [ -n "$2" ] && [ $(( $1 )) -eq $(( $2 )) ] ;; esac
}
knob_set() { # NAME VALUE: write, then read back; 1 if it does not read back
	dbg_write "$1" "$2"
	same_value "$(dbg_cat "$1")" "$2"
}
KNOBS_SET=""
knobs_restore() { # every declared knob back to its default, read back; 1 if one does not read back
	local k d bad=0
	for k in $KNOBS; do
		d="KNOB_${k}_DEFAULT"
		dbg_write "$k" "${!d}"
		same_value "$(dbg_cat "$k")" "${!d}" || { echo "  knob $k does not read back its default ${!d}"; bad=1; }
	done
	KNOBS_SET=""
	return $bad
}
knobs_at_default() {
	local k d
	for k in $KNOBS; do
		d="KNOB_${k}_DEFAULT"
		same_value "$(dbg_cat "$k")" "${!d}" || { echo "knob $k is $(dbg_cat "$k"), not its default ${!d}"; return 1; }
	done
	return 0
}

# ---- the GPU: reset, registers ------------------------------------------------------------------
NO_MORE_RESET=0
reset_gpu() {
	[ "$NO_MORE_RESET" = 1 ] && { echo "  (no reset: the session stopped)"; return 1; }
	dbg_write reset 1; local r=$?
	sleep "${RESET_WAIT:-3}"
	return $r
}
regval() { awk -v r="$2" '$1 == "reg" && $2 == r { print $3 }' "$1"; }
snap() { # NAME K: debugfs regs into $JW/snapK.regs; 1 if unreadable
	local f="$JW/snap$2.regs" r
	sudo -n timeout -k 3 20 cat "$D/regs" > "$f" 2>&1
	r=$?
	if [ "$r" -ne 0 ] || ! grep -q '^reg 0x0c04 ' "$f"; then echo "  snap $2: regs unreadable (status $r)"; return 1; fi
	mark "snap $1 $2 $(regval "$f" 0x0c04) $(regval "$f" 0x0c08)"
	return 0
}
fault_req() { local v; v=$(regval "$1" 0x0c04); [ -n "$v" ] && echo $(( v & 0xffff )); }

# ---- files ---------------------------------------------------------------------------------------
free_kb() { df -Pk "$HOME" | awk 'NR == 2 { print $4 }'; }
space_ok() { local k; k=$(free_kb); [ -n "$k" ] && [ "$k" -ge $(( MIN_FREE_MB * 1024 )) ]; }
rm_work() {
	case "$1" in
	"$WROOT"/?*) rm -rf -- "$1" ;;
	*) echo "rm_work: $1 is not under $WROOT: refused"; exit 1 ;;
	esac
}
keep() { # NAME FILE [SUFFIX]: gzip the whole raw file (mtime 0), its size and raw sha256 in raw.sha256
	local raw sum
	raw=$(wc -c < "$2" | tr -d ' ')
	sum=$(sha "$2" | cut -d' ' -f1)
	gzip -n -6 -c "$2" > "$KEEP/$1${3:-.txt}.gz"
	echo "$1${3:-.txt} $raw $sum" >> "$KEEP/raw.sha256"
}
has_kept() { [ -s "$KEEP/$1" ] || [ -s "$KEEP/$1.gz" ]; }
# required_missing NAME: the per-row files the scorer reads (run/required.tsv, from its REQUIRED)
# that the kept directory lacks for row NAME; with no NAME, the stage's fixed files
required_missing() {
	local s f
	for s in $(awk -F'\t' -v st="$STAGE" '$1 == st { print $2 }' "$STAGED/run/required.tsv"); do
		case "$s" in
		.*) [ -n "${1:-}" ] && { has_kept "$1$s" || echo "$1$s"; } ;;
		*) [ -z "${1:-}" ] && { has_kept "$s" || echo "$s"; } ;;
		esac
	done
	return 0
}
# outdirs ARGS...: make every directory an OUTDIR_OPTS option names under the job's work
# directory; prints the ones outside it that do not exist
outdirs() {
	local prev="" a o p
	for a in "$@"; do
		for o in $OUTDIR_OPTS; do
			if [ "$prev" = "$o" ]; then
				p=$(dirname "$a")
				case "$p" in "$W"|"$W"/*) mkdir -p "$p" ;; *) [ -d "$p" ] || echo "$o $a: no directory $p" ;; esac
			fi
		done
		prev=$a
	done
	return 0
}

# ---- the kernel log ------------------------------------------------------------------------------
slice_since() { sudo -n timeout -k 5 30 dmesg > "$JW/dmesg.all"; awk -v m="$1" 'f{print} index($0,m){f=1}' "$JW/dmesg.all"; }
bad_lines() { grep -Ehv "$RESET_INFO_RE" "$@"; }
classify() { # RC FILE...: fault | hang | ok | fail
	local rc=$1; shift
	if bad_lines "$@" | grep -Eq "$FAULT_RE"; then echo fault
	elif bad_lines "$@" | grep -Eq "$HANG_RE"; then echo hang
	elif [ "$rc" -eq 0 ]; then echo ok
	else echo fail; fi
}
# expected_end RC OUT NAME...: 0 if the job's end is one of the expected outcomes NAME... its row
# declares (`expect:NAME`, kitscore.OUTCOMES): the rc and the outcome's line in its output
expected_end() {
	local rc=$1 out=$2 e; shift 2
	for e in "$@"; do
		case "$e" in
		rc3-overflow) [ "$rc" -eq 3 ] && grep -q "scene overflowed the parameter buffer" "$out" && return 0 ;;
		esac
	done
	return 1
}

# ---- health ---------------------------------------------------------------------------------------
HN=0
health_ok() { # NAME: one fill and one plain 64x64 triangle with the health tool, kept; 0 if both drew exactly
	local ht
	ht=$(tool_path "$HEALTH_TOOL")
	HN=$((HN + 1))
	mark "health $1 try $HN"
	sudo -n timeout -k 10 60 "$ht" fill > "$JW/fill.$HN.out" 2>&1 </dev/null
	keep "$1.fill$HN" "$JW/fill.$HN.out"
	sudo -n timeout -k 10 60 "$ht" tri > "$JW/health.$HN.out" 2>&1 </dev/null
	keep "$1.health$HN" "$JW/health.$HN.out"
	grep -q "^diff: 0 of" "$JW/fill.$HN.out" && grep -q "^diff: 0 of 4096" "$JW/health.$HN.out"
}
health() { # NAME: exact draws; a reset and two more attempts, written out one by one; then stop (rc 5)
	sleep "${HEALTH_WAIT:-3}"
	if health_ok "$1"; then return 0; fi
	reset_gpu; sleep "${HEALTH_WAIT:-5}"
	if health_ok "$1"; then echo "  health: recovered after a reset"; return 0; fi
	sleep "${HEALTH_WAIT:-5}"
	if health_ok "$1"; then echo "  health: recovered on the retry"; return 0; fi
	echo "## abort: the fill and triangle do not draw after a reset and a retry"
	exit 5
}
strict_health() { # NAME: the FIRST attempt must draw; else the recovery runs and the stage stops (rc 16)
	sleep "${HEALTH_WAIT:-3}"
	if health_ok "$1"; then return 0; fi
	echo "## STOP: the health fill or triangle failed after $1 (strict): recovery, then stop"
	reset_gpu; sleep "${HEALTH_WAIT:-5}"
	health_ok "$1" || { echo "## abort: no recovery"; exit 5; }
	exit 16
}

# ---- preflight, exit ---------------------------------------------------------------------------------
preflight() {
	local f t got
	echo "## stage $STAGE of $PREFIX"; echo "## uname"; uname -r
	echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx); echo "$SRCV_FILE"
	echo "## loaded module"; SRCV_LOADED=$(sudo -n cat "${KIT_SRCV_PATH:-/sys/module/gma500_gfx/srcversion}"); echo "$SRCV_LOADED"
	[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
	[ "$SRCV_LOADED" = "$SRCV_EXPECT" ] || { echo "the loaded module ($SRCV_LOADED) is not the expected build ($SRCV_EXPECT)"; exit 1; }
	echo "## debugfs directory: $D"
	for f in reset regs $KNOBS $DEBUGFS_NEED; do
		sudo -n test -e "$D/$f" || { echo "the loaded driver has no debugfs $f"; exit 1; }
	done
	for t in $TOOLS; do
		got=$(sha "$(tool_path "$t")" | cut -d' ' -f1)
		echo "## tool $t: $got $(tool_path "$t")"
		[ "$got" = "$(tool_sha "$t")" ] || { echo "tool $t is not the pinned build ($(tool_sha "$t"))"; exit 1; }
	done
	echo "## knobs at start (their defaults: nothing of an earlier session left)"
	knobs_at_default || exit 1
	python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || { echo "python3 is older than 3.10 (sessioncheck.py premise)"; exit 1; }
	echo "## free space on ~: $(free_kb) KiB (at least $MIN_FREE_MB MiB)"
	space_ok || { echo "less than $MIN_FREE_MB MiB free on ~"; exit 22; }
	echo "## work directory: $WROOT"
	echo "## clock"; date
}
FATAL_STOP=0
STARTED=0
finish_log() {
	if sudo -n timeout -k 5 60 journalctl -k --since "@$START" --no-pager > "$KEEP/kernel.log" 2>&1; then
		echo "## kernel log (journalctl)"
	else
		sudo -n timeout -k 5 30 dmesg > "$KEEP/kernel.log" 2>&1; echo "## kernel log (dmesg: journalctl failed)"
	fi
}
cleanup() {
	if [ "$STARTED" = 1 ]; then
		# the knobs back to their defaults at EVERY exit (bounded writes), then a reset unless the kernel is in trouble
		knobs_restore
		mark "exit knobs restored"
		[ "$FATAL_STOP" = 1 ] || reset_gpu
		finish_log
	else
		echo "## exit before the preflight passed: nothing touched"
	fi
	exec >&- 2>&-
	( sleep "${TEE_GRACE:-10}"; kill "$TEEPID" 2>/dev/null ) </dev/null >/dev/null 2>&1 &
	wait "$TEEPID"
	case "$WROOT" in "$HOME/scratch/tmp/$PREFIX."??????) rm -rf -- "$WROOT" ;; esac
}
trap cleanup EXIT
begin() {
	printf 'name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_int\tfault_word\tfree_kb\n' > "$KEEP/cases.tsv"
	printf 'name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_int\tfault_word\tfree_kb\n' > "$KEEP/void.tsv"
	printf 'name\tkeys\treading\n' > "$KEEP/readings.tsv"
	: > "$KEEP/raw.sha256"
	JW=$WROOT/begin; mkdir -p "$JW"
	preflight
	STARTED=1
	mark "row begin"
	reset_gpu || { echo "the first debugfs reset failed"; exit 13; }
	health begin </dev/null
	rm_work "$JW"
}
