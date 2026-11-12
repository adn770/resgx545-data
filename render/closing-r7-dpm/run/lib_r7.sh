# SPDX-License-Identifier: MIT
# lib_r7.sh (R7-dpm): what the laptop-side stage runner shares (sourced by run_stage.sh, never run).  R6-dpm's lib_r6.sh (freeze 2)
# with round 7's additions: two sets on two modules (the table's `#set` and `#module` lines; the preflight refuses a module that is not
# the set's), the own task oomring2 (set B), the premise check through the landed tools/closing/sessioncheck.py (staged with scorekit.py),
# tri dumps kept.  R5-dpm's lib_r5.sh (every fix kept: the capture check, the space stop) with round 6's laptop rule (HACKING.md, user 2026-11-12): every laptop file under
# ~/scratch/r7d/ (run, stage, out), the per-job work directory `mktemp -d ~/scratch/tmp/r7d.XXXXXX` (never /tmp: a 991 MiB tmpfs in
# RAM; sudo drops TMPDIR, so the path is named), 600 MB free at the preflight on the kept files' and the work directory's
# filesystems and 200 MB before every job, the work directory removed at the stage's end (its files one by one, then rmdir).  The
# ONE reader run/r7read.py (python3 stdlib; the scorer imports the same file); derived cells M:G:k:d:0xP read from a calibration's own
# timeline when it is off the model; the own firmware task of stage s-k through the landed fwtask_run.py (resgx545
# tools/fwtask, copied unchanged as run/fwtask_run.py).
#
# Safety rules of this runner (checked by run/guard_r7.sh and tests/run_mock.sh):
#  - the only debugfs files the runner writes itself: render_pb_pages (allow-listed set_knob, restored after every job and by the trap)
#    and reset (the kernel's own reset).  Stage s-k only: fwtask_run.py `arm` (own_code, own_arm, load, boot: the blob is
#    bins/oomring2.blob of set B, pinned by sha256, no str in it), `write` (the results page: zeroes) and `page` / `status` (reads).  No kreg,
#    no kregnow, no kpoke, no /dev/mem write, no clock-gate register, no trc_hazard, no firmware str.
#  - EVERY debugfs access goes through sudo -n (fwtask_run.py runs as `sudo -n python3`); markers to /dev/kmsg by `sudo -n tee -a`.
#  - the debugfs directory is the FIRST of `dri/*/sgx` (the node has three names).
#  - never a reboot, a boot-loader change or a kernel build; no compile at all; the tool, regtimeline and module are the pinned ones
#    (a mismatch STOPS the session, nothing is rebuilt); laptop files under ~/scratch/r7d and ~/scratch/tmp/r7d.* only.
#  - no git, no recursive delete (work files removed one by one by name), no polling or wait loop: no while/until anywhere; every
#    timeout has -k.
# Root through sudo -n.  SGXFIVE_DEBUGFS points the runner at a plain directory (tests/run_mock.sh).
set -u
STAGE=${STAGE:?lib_r7.sh: STAGE not set}
HERE_LIB=$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)
# freeze 2: a file the runner sources must be there (attempt a1's tree had no lib_check.sh: num_eq was "command not found" at a control)
for f in r7.env lib_check.sh r7read.py sessioncheck.py scorekit.py; do [ -f "$HERE_LIB/$f" ] || { echo "the runner tree lacks $f: STOP (stage_r7.sh copies it)"; exit 1; }; done
. "$HERE_LIB/r7.env" || exit 1
. "$HERE_LIB/lib_check.sh" || exit 1
for fn in num_eq is_num; do type "$fn" >/dev/null 2>&1 || { echo "the runner tree does not define $fn: STOP"; exit 1; }; done
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-rgn4}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
R7D=${R7D:-$HOME/scratch/r7d}
S=${SGXFIVE_PROBE_BINS:-$R7D/stage}
OUTROOT=${OUTROOT:-$R7D/out}
TMPROOT=${TMPROOT:-$HOME/scratch/tmp}
KEEP=${KEEP:-$OUTROOT/$STAGE}
STATE=${STATE:-$OUTROOT/state}
# the set of this stage (its table's `#set` line) and the module it runs on: set A the test module 41E2F5C7, set B 37EC97AB
SET=$(awk '/^#set / {print $2; exit}' "$DIR/../tables/$STAGE.txt" 2>/dev/null)
case "$SET" in
A) EXPECT_SRCV=${EXPECT_SRCV_A:-$SRCV_A}; BLOB=""; BLOB_SHA="" ;;
B) EXPECT_SRCV=${EXPECT_SRCV_B:-$SRCV_B}; BLOB=oomring2.blob; BLOB_SHA=$OOMRING2_SHA ;;
*) echo "table $STAGE has no #set A or B line: STOP"; exit 1 ;;
esac
TABLE_MODULE=$(awk '/^#module / {print $2; exit}' "$DIR/../tables/$STAGE.txt")
[ "$TABLE_MODULE" = "$SRCV_A" ] || [ "$TABLE_MODULE" = "$SRCV_B" ] || { echo "table $STAGE names module $TABLE_MODULE, not one of r7.env's: STOP"; exit 1; }
{ [ "$SET" = A ] && [ "$TABLE_MODULE" = "$SRCV_A" ]; } || { [ "$SET" = B ] && [ "$TABLE_MODULE" = "$SRCV_B" ]; } || { echo "table $STAGE: set $SET with module $TABLE_MODULE: STOP"; exit 1; }
EXPECT_TOOL=${EXPECT_TOOL:-$TOOL_SHA}
EXPECT_RT=${EXPECT_RT:-$RT_SHA}
FWRUN=${FWTASK_RUN:-$HERE_LIB/fwtask_run.py}
PY3=${RUNNER_PY:-python3}
MIN_FREE_KB=${MIN_FREE_KB:-600000}
MIN_JOB_KB=${MIN_JOB_KB:-200000}   # free space the work directory must have before every job (r5 attempt 1: a full RAM tmpfs cut a capture)
MIN_THR0=${MIN_THR0:-32}          # 0x20: derived 1500-vertex cells (the lowest is 1024x1024's B3 - 1 = 0x40)
MAX_P=1058                         # 0x422: the knob's clamp
D=${SGXFIVE_DEBUGFS:-$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)}
KMSG=${KMSG:-/dev/kmsg}
FATAL_RE='soft lockup|hard LOCKUP|NMI watchdog|watchdog: BUG|rcu.*(stall|self-detected)|blocked for more than|Oops|BUG:|Call Trace|kernel panic|general protection|machine check|psb.*watchdog'
[ -x "$T" ] || { echo "no $T: the rgn4 tool must be in place (a missing or different tool STOPS the session, no rebuild)"; exit 1; }
[ -n "$D" ] || { echo "no sgx debugfs directory (debug option off?)"; exit 1; }
export SGXFIVE_DEBUGFS="$D"
mkdir -p "$KEEP" "$STATE"
START=$(date +%s)
RUN=$(date +%s)-$$
sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$@"; else shasum -a 256 "$@"; fi; }

mark() { printf "resgx545 r7d %s %s\n" "$*" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null 2>&1; }
mark_case() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee -a "$KMSG" >/dev/null 2>&1; }

set_knob() { # NAME VALUE: the allow-listed debugfs knob only; echoes the read-back
	case "$1" in
	render_pb_pages) ;;
	*) echo "set_knob: $1 is not allowed in R7-dpm"; exit 7 ;;
	esac
	echo "$2" | sudo -n tee "$D/$1" >/dev/null
	sudo -n cat "$D/$1"
}
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep "${RESET_WAIT:-3}"; }

# ---------------------------------------------------------------------------------------------------------------- the own task (s-k)
# fwtask_run.py prints one JSON object; the runner keeps it whole and reads `"ok": true` / `"advancing": true` from it
fw() { sudo -n timeout -k 5 60 "$PY3" "$FWRUN" "$@" 2>&1 </dev/null; }
fw_arm() { fw arm "{\"blob\": \"$S/$BLOB\", \"arm\": \"$OOMRING_ARM\"}"; }
fw_clear() { # the pass counters and lost count (dwords 16..20) and the 48 rungs (dwords 256..639): zeroes
	fw write '{"dword": 16, "vals": [0, 0, 0, 0, 0]}' >/dev/null &&
	fw write "{\"dword\": 256, \"vals\": [$(printf '0,%.0s' $(seq 1 383))0]}" >/dev/null
}
fw_ok() { printf '%s' "$1" | grep -q '"ok": true'; }
fw_alive() { printf '%s' "$1" | grep -q '"advancing": true'; }

preflight() {
	echo "## stage $STAGE"; echo "## uname"; uname -r
	echo "## firmware"; sha /lib/firmware/sgx545_ukernel.fw 2>/dev/null || echo "(no firmware file)"
	echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$SRCV_FILE"
	echo "## loaded module"; SRCV_LOADED=$(sudo -n cat "${SRCV_PATH:-/sys/module/gma500_gfx/srcversion}"); echo "$SRCV_LOADED"
	[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
	[ "$SRCV_LOADED" = "$EXPECT_SRCV" ] \
		|| { echo "the loaded module $SRCV_LOADED is not set $SET's module $EXPECT_SRCV (another kernel is booted: STOP AND ASK)"; exit 1; }
	for f in reset render_pb_pages regs buf09 render_param render_tadata; do
		sudo -n test -e "$D/$f" || { echo "the loaded driver has no debugfs $f"; exit 1; }
	done
	if [ "${HAS_FW:-0}" = 1 ]; then
		for f in own_code own_arm own_res load boot status miscinfo; do
			sudo -n test -e "$D/$f" || { echo "the loaded driver has no debugfs $f (stage $STAGE arms the own task)"; exit 1; }
		done
		[ -n "$BLOB" ] || { echo "stage $STAGE arms the own task but is not of set B: STOP"; exit 1; }
		[ -f "$S/$BLOB" ] || { echo "no $S/$BLOB: run stage_r7.sh"; exit 8; }
		got=$(sha "$S/$BLOB" | cut -d' ' -f1)
		[ "$got" = "$BLOB_SHA" ] || { echo "$BLOB is not the frozen one ($got)"; exit 1; }
		[ -f "$FWRUN" ] || { echo "no $FWRUN"; exit 1; }
	fi
	"$PY3" -c 'import sys; sys.exit(sys.version_info < (3, 10))' || { echo "python3 is older than 3.10 (the landed scorekit.py needs 3.10): STOP"; exit 1; }
	"$PY3" "$HERE_LIB/sessioncheck.py" outdirs -- true >/dev/null || { echo "the staged sessioncheck.py does not run: STOP"; exit 1; }
	echo "## debugfs directory: $D"
	echo "## tool"; got=$(sha "$T" | cut -d' ' -f1); echo "$got $T"
	[ "$EXPECT_TOOL" = "$got" ] || { echo "the tool is not the pinned rgn4 tool ($got, pinned $EXPECT_TOOL): STOP and ask, nothing is rebuilt"; exit 1; }
	echo "## regtimeline"; got=$(sha "$RT" 2>/dev/null | cut -d' ' -f1); echo "$got $RT"
	[ "$EXPECT_RT" = "$got" ] || { echo "regtimeline is not the pinned one ($EXPECT_RT): STOP and ask"; exit 1; }
	echo "## work directories: $TMPROOT/r7d.XXXXXX, one a job"
	case "$TMPROOT" in /tmp*|/var/tmp*|/dev/shm*) echo "the work root $TMPROOT is a RAM filesystem: STOP"; exit 1 ;; esac
	echo "## free space"
	for fsdir in "$KEEP" "$TMPROOT"; do
		free=$(df -Pk "$fsdir" | awk 'NR==2 {print $4}'); echo "$free KB free on the filesystem of $fsdir (need $MIN_FREE_KB)"
		[ "${free:-0}" -ge "$MIN_FREE_KB" ] || { echo "not enough free space for the dumps"; exit 1; }
	done
	echo "## knobs at start"
	PB_RESTORE=$(sudo -n cat "$D/render_pb_pages" 2>/dev/null); echo "render_pb_pages=$PB_RESTORE"
	[ -n "$PB_RESTORE" ] || { echo "the knob cannot be read (sudo?)"; exit 1; }
	mark "preflight $STAGE"
	sudo -n dmesg 2>/dev/null | grep -q "resgx545 r7d preflight $STAGE $RUN" \
		|| { echo "the kmsg marker did not arrive in dmesg (sudo -n tee -a $KMSG)"; exit 1; }
	echo "## kmsg marker arrived"
	echo "## clock"; date
}

# the work directory: mktemp -d ~/scratch/tmp/r7d.XXXXXX (HACKING.md), never /tmp: r5-dpm's attempt 1 lost a0-cal-4096's capture when
# /tmp (a 991 MiB tmpfs on the laptop) filled during the tadata dump (text cut at 4096 bytes, tadata short, no buf09, no regs)
mkdir -p "$OUTROOT" "$TMPROOT"
W=""
new_w() { # a job's own work directory (dump/ and words/ inside); every file the job writes stays there till it is kept
	W=$(mktemp -d "$TMPROOT/r7d.XXXXXX") || return 1
	mkdir -p "$W/dump" "$W/words"
}
drop_w() { # remove a job's work directory once its files are kept: its files by name, then the empty directories
	[ -n "$W" ] && [ -d "$W" ] || { W=""; return 0; }
	clean_w; rmdir "$W/dump" "$W/words" 2>/dev/null; rmdir "$W" 2>/dev/null
	[ -d "$W" ] && echo "## work directory $W not empty: left for the lead"
	W=""; return 0
}
clean_w() { # no glob in a delete: each file is removed by name
	[ -n "$W" ] || return 0
	for f in "$W"/*.out "$W"/*.bin "$W"/*.txt "$W"/*.json "$W"/*.dmesg "$W"/dump/* "$W"/words/*; do
		[ -f "$f" ] && rm -f -- "$f"
	done
	return 0
}
FATAL_STOP=0
cleanup() {
	[ -n "${PB_RESTORE:-}" ] && set_knob render_pb_pages "$PB_RESTORE" >/dev/null 2>&1
	# the reset also disarms the own task (own_arm reads off after it)
	[ "$FATAL_STOP" = 1 ] || reset_gpu
	drop_w; finish_log
}
trap cleanup EXIT
finish_log() {
	sudo -n journalctl -k --since "@$START" --no-pager > "$KEEP/kernel.log" 2>&1 || sudo -n dmesg > "$KEEP/kernel.log" 2>&1
	echo "## kernel log: $(grep -c 'resgx545 case' "$KEEP/kernel.log" | tr -d ' ') case markers kept in $KEEP/kernel.log"
}
kept_name() { "$PY3" "$HERE_LIB/r7read.py" kept "$1" "$2"; } # NAME KIND: the one name function (run/r7read.py)
keep() { # NAME FILE KEPTNAME: gzip the whole raw file (mtime 0), print its sizes and raw sha256
	raw=$(wc -c < "$2" | tr -d ' ')
	sum=$(sha "$2" | cut -d' ' -f1)
	gzip -n -6 -c "$2" > "$KEEP/$3"
	echo "$3 $raw $sum" >> "$KEEP/raw.sha256"
	echo "  kept $3: $raw bytes raw, raw sha256 $sum"
}

tri_ok() { sudo -n timeout -k 5 60 "$T" tri 2>&1 </dev/null | grep -q "^diff: 0 of 4096"; }
fill_ok() { sudo -n timeout -k 5 60 "$T" fill 2>&1 </dev/null | grep -q "^diff: 0 of 2048"; }
health() { # a plain 64x64 triangle must draw exactly; reset and two more attempts; three failures stop
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
slice_since() { sudo -n dmesg 2>/dev/null | awk -v m="$1" 'f{print} index($0,m){f=1}'; }

# space_ok: the work directory's filesystem has MIN_JOB_KB free (checked before every job)
space_ok() { f=$(df -Pk "$TMPROOT" | awk 'NR==2 {print $4}'); [ "${f:-0}" -ge "$MIN_JOB_KB" ]; }
# capture_ok NAME [dump]: the job's capture is whole: the tool output holds a timeline block whose every line is complete and ends with a
# newline (run/r7read.py check), and the control block and register dump were read (non-empty).  Else: "why" on stdout, status 1.
capture_ok() {
	c=$("$PY3" "$HERE_LIB/r7read.py" check "$W/$1.out" 2>&1) || { echo "$c"; return 1; }
	[ -s "$W/after.buf09.bin" ] || { echo "no control block read (buf09)"; return 1; }
	[ -s "$W/after.regs.txt" ] || { echo "no register dump read (regs)"; return 1; }
	space_ok || { echo "the work filesystem is below $MIN_JOB_KB KB free after the job"; return 1; }
	case " ${2:-} " in *" dump "*)  # an s-v calibration: both dump files present and not empty (G5's reading of the blocks)
		for k in param tadata; do [ -s "$W/dump/p1139-green.$k.bin" ] || { echo "no $k dump"; return 1; }; done ;; esac
	case " ${2:-} " in *" tdump "*)  # s-b's 2048x2048 calibration: the tri dump (H-WALK64 reads its region headers)
		for k in param tadata; do [ -s "$W/dump/tri.$k.bin" ] || { echo "no tri $k dump"; return 1; }; done ;; esac
	return 0
}

# ---------------------------------------------------------------------------------------------------------------------- DPM readings
# dpm_read OUT BUF09: `void=0 cls=R|N|- nparts=N thr0=0xH knob=0xH need=N|- valid=0|1 grow=0|1|- gps_abort=N gps_left=N gmax=N mono=0|1
# runpeaks=0xH,... S2=0xH ...` (run/r7read.py, the scorer's own reader)
dpm_read() { "$PY3" "$HERE_LIB/r7read.py" line "$1" "$2" 2>/dev/null || echo "void=1 cls=-"; }
# premise NAME KEYS READING: the landed premise check (sessioncheck.py premise, scorekit.premise_stops): status 1 and a STOP line when
# the reading lacks a key the control declared (`-`, empty or absent); KEYS comma separated as in the table's reads: knob
premise() { printf '%s\n' "$3" | "$PY3" "$HERE_LIB/sessioncheck.py" premise "$1" "$(printf '%s' "$2" | tr ',' ' ')" -; }
field() { # LINE KEY: the value of KEY=VALUE in LINE
	for kv in $1; do case "$kv" in "$2="*) echo "${kv#*=}"; return 0 ;; esac; done
	echo ""
}
# m_cell G K D P: the frozen model's cell (P - 0x22) when calibration G's steps lie in the model's brackets (G.modelok); else (G.modeloff)
# G's own step S_K + D ("REPICK thr0": the plan's re-pick rule A_k = S_k + (model A_k - model S_k)); SKIP when G was not calibrated
m_cell() {
	if [ -e "$STATE/$1.modelok" ]; then echo $(($4 - 34)); return 0; fi
	if [ -e "$STATE/$1.modeloff" ]; then r=$(s_cell "$1" "$2" "$3"); case "$r" in SKIP*) echo "$r" ;; *) echo "REPICK $r" ;; esac; return 0; fi
	echo "SKIP no calibration of $1 against the model"
}
# s_cell G K OFF: thr0 = S_K of calibration G + OFF (state G.steps: `k S a b` lines written from the calibration's own timeline);
# "SKIP why" when the calibration is missing, had non-monotone steps, or has no step K
s_cell() {
	[ -f "$STATE/$1.steps" ] || { echo "SKIP no calibration steps for $1"; return 0; }
	[ -e "$STATE/$1.bad" ] && { echo "SKIP calibration $1 was not this scene or had non-monotone steps"; return 0; }
	s=$(awk -v k="$2" '$1 == k {print $2}' "$STATE/$1.steps" | head -n 1)
	[ -n "$s" ] || { echo "SKIP calibration $1 shows no step $2"; return 0; }
	echo $((s + $3))
}
