# SPDX-License-Identifier: MIT
# lib_r3.sh (R3): what the laptop-side R3 stage runner shares (sourced by run_stage.sh, never run).
# Built from R2's lib_r2.sh with its fixes kept (every item below is tested in tests/run_mock.sh); the poke, the sweep, the watchdog and the
# STATUS2 reads are gone (R3 has none of them) and the dynamic rows are new: the runner derives a DPM row's P from the OBSERVATIONS
# of the jobs it kept (the bisect cell, the last raise / first silent cell of a group), never from a person.
#
# Safety rules of this runner (checked by run/guard_r3.sh):
#  - the only debugfs files ever written by the runner: render_pb_pages (allow-listed set_knob) and reset (the kernel's own reset), plus
#    /dev/kmsg for the markers.  No kreg, no kregnow, no kpoke, no /dev/mem write, no clock-gate register, no trc_hazard, no firmware str.
#  - EVERY debugfs access (read, write, test, glob) goes through sudo -n; the guard refuses a code line that names the debugfs without sudo.
#  - the debugfs directory is the FIRST of `dri/*/sgx` (the node has three names: dri/0, dri/0000:00:02.0, dri/128): never "exactly one".
#  - never a reboot, a boot-loader change or a kernel build; the tool is R1's binary (~/sgxfive-test-r1, pinned by sha256: a mismatch STOPS
#    the session, nothing is rebuilt); the laptop directories are ~/r3g, ~/r3g-stage, ~/r3g-out (other sessions use ~/r3p-*, ~/r3xev).
#  - no git, no recursive delete (work files are removed one by one by name), no polling or wait loop: no while/until anywhere; the only
#    delays are single fixed sleeps after a reset and before a health triangle.
# Root through sudo -n.  SGXFIVE_DEBUGFS points the runner at a plain directory (tests/run_mock.sh).
set -u
STAGE=${STAGE:?lib_r3.sh: STAGE not set}
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-r1}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
S=${SGXFIVE_PROBE_BINS:-$HOME/r3g-stage}
OUTROOT=${OUTROOT:-$HOME/r3g-out}
KEEP=${KEEP:-$OUTROOT/$STAGE}
STATE=${STATE:-$OUTROOT/state}
TOOL_SHA_FILE=${TOOL_SHA_FILE:-$HOME/r3g/TOOL.sha256}
EXPECT_SRCV=${EXPECT_SRCV:-B21FDA82BD5E5CB5A627E3B}
MIN_FREE_KB=${MIN_FREE_KB:-600000}
MIN_THR0=${MIN_THR0:-96}
D=${SGXFIVE_DEBUGFS:-$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)}
KMSG=${KMSG:-/dev/kmsg}
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|general protection|machine check|psb.*watchdog'
[ -x "$T" ] || { echo "no $T: stage it with run/stage_r3.sh (R1's tool must be in place; a missing or different tool STOPS the session, no rebuild)"; exit 1; }
[ -n "$D" ] || { echo "no sgx debugfs directory (debug option off?)"; exit 1; }
export SGXFIVE_DEBUGFS="$D"
mkdir -p "$KEEP" "$STATE"
START=$(date +%s)
RUN=$(date +%s)-$$
sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }

mark() { printf "resgx545 r3g %s %s\n" "$*" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null 2>&1; }
# the case marker keeps the format of the earlier batches ("resgx545 case NAME RUN")
mark_case() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null 2>&1; }

set_knob() { # NAME VALUE: the allow-listed debugfs knob only; echoes the read-back
	case "$1" in
	render_pb_pages) ;;
	*) echo "set_knob: $1 is not allowed in R3"; exit 7 ;;
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
	[ "$EXPECT_SRCV" = any ] || [ "$SRCV_LOADED" = "$EXPECT_SRCV" ] \
		|| { echo "the loaded module $SRCV_LOADED is not the expected $EXPECT_SRCV (the kernel changed: stop and ask; EXPECT_SRCV=any to override)"; exit 1; }
	for f in reset render_pb_pages regs buf09 render_param render_tadata; do
		sudo -n test -e "$D/$f" || { echo "the loaded driver has no debugfs $f (kernel too old for R3)"; exit 1; }
	done
	echo "## debugfs directory: $D"
	echo "## tool"; got=$(sha "$T" | cut -d' ' -f1); echo "$got $T"
	want=$(cut -d' ' -f1 "$TOOL_SHA_FILE" 2>/dev/null)
	[ -n "$want" ] && [ "$want" = "$got" ] || { echo "the tool is not the pinned one ($got, pinned ${want:-none}): STOP and ask, nothing is rebuilt"; exit 1; }
	echo "## regtimeline"; sha "$RT" 2>/dev/null || { echo "(none: R1 built ~/regtimeline; it is missing)"; [ "${NEED_RT:-1}" = 1 ] && exit 1; }
	echo "## free space"; free=$(df -Pk "$KEEP" | awk 'NR==2 {print $4}'); echo "$free KB free in $KEEP (need $MIN_FREE_KB)"
	[ "${free:-0}" -ge "$MIN_FREE_KB" ] || { echo "not enough free space for the dumps"; exit 1; }
	echo "## knobs at start"
	PB_RESTORE=$(sudo -n cat "$D/render_pb_pages" 2>/dev/null); echo "render_pb_pages=$PB_RESTORE"
	[ -n "$PB_RESTORE" ] || { echo "the knob cannot be read (sudo?)"; exit 1; }
	# the markers are the job slices: one must arrive in the kernel log before any job
	mark "preflight $STAGE"
	sudo -n dmesg 2>/dev/null | grep -q "resgx545 r3g preflight $STAGE $RUN" \
		|| { echo "the kmsg marker did not arrive in dmesg (sudo -n tee $KMSG)"; exit 1; }
	echo "## kmsg marker arrived"
	echo "## clock"; date
	echo "## R3 safety rules: see the header of lib_r3.sh (allow-listed knob only; no poke; laptop directories ~/r3g*)"
}

W=$(mktemp -d "${TMPDIR:-/tmp}/r3w.XXXXXX")
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

# ---------------------------------------------------------------------------------------------------------------------- DPM readings
HERE_LIB=$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)
# dpm_read FILE: `nparts=N thr0=0xH reach=0|1 valid=0|1 knob=0xH need=N c1=N cN=N` of a tool output (run/dpm_read.awk)
dpm_read() { awk -f "$HERE_LIB/dpm_read.awk" "$1"; }
field() { # LINE KEY: the value of KEY=VALUE in LINE
	for kv in $1; do case "$kv" in "$2="*) echo "${kv#*=}"; return 0 ;; esac; done
	echo ""
}
# dword 38 of the control block (buf09 word 38 = byte 152): 32 (0x20) is the raise
raise_word() { od -An -tu4 -j152 -N4 -v "$1" 2>/dev/null | tr -d ' '; }
# obs_class NAME: R raise, N none, V void, from this job's own kept output ($W/NAME.out, $W/after.buf09.bin): the reading the
# scorer makes (score/dpm3.py): valid = the second TA run reaches the first abort's status and there are at least two partial renders
obs_class() {
	rd=$(dpm_read "$W/$1.out")
	[ "$(field "$rd" valid)" = 1 ] || { echo V; return 0; }
	rw=$(raise_word "$W/after.buf09.bin")
	if [ "${rw:-0}" = 32 ]; then echo R; else echo N; fi
}
obs_add() { echo "$2 $3 $4" >> "$STATE/$1.obs"; } # GROUP THR0 CLASS NAME
bis() { awk -v mode="$2" -v off="${3:-0}" -f "$HERE_LIB/bis.awk" "$STATE/$1.obs" 2>/dev/null || echo "SKIP no state"; }
cal_need() { awk '{print $1}' "$STATE/$1.cal" 2>/dev/null | head -n 1; }
