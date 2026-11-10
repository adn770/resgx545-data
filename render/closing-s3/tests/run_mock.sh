#!/bin/bash
# tests/run_mock.sh: the S3 runner end to end against a fake tool, a fake regtimeline and a fake debugfs
# whose directory is mode 000 (only the sudo shim reaches it: an unprivileged access fails, as on the
# laptop), then every stop rule, the guard and the driver's dry run.  Needs a current freeze
# (run/freeze_s3.sh freeze): the runner compares its tables and program with FROZEN.sha256, and that
# file with the sha256 the driver passes.  The fake kernel plays the watchdog: hold_recovery written N
# while a render fault is latched makes it recover on its own (sgxfive_watchdog, 50 ms).
# Nothing is deleted: every run writes into a new mktemp directory, printed at the end.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
PY=${PY:-$P/../pixel-faults/.venv/bin/python}
W=$(mktemp -d)
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
. "$P/run/lib_check.sh"
"$P/run/freeze_s3.sh" verify > /dev/null || { echo "FAIL: not frozen (run/freeze_s3.sh freeze)"; exit 1; }
N=0
# a fresh fake laptop: debugfs (mode 000) + its real files, the fake GPU state, the kernel log
world() {
	N=$((N + 1)); M=$W/w$N; ATT=att$N
	mkdir -p "$M/dbg" "$M/dbgreal" "$M/fake" "$M/stage" "$M/out" "$M/log"
	for f in reset regs render_param render_tadata; do : > "$M/dbgreal/$f"; done
	echo N > "$M/dbgreal/hold_recovery"; echo 0x422 > "$M/dbgreal/render_pb_pages"; echo 0 > "$M/dbgreal/alias_skip"
	printf 'dwords written through the read-only alias: 0\nBIF_INT_STAT 0x80020 BIF_FAULT 0x32200001 bif_faults 0\nkernel buffer protected; reload and boot to recover\n' > "$M/dbgreal/xfer_ro"
	echo "${FAKE_HOLD_INIT:-N}" > "$M/fake/hold"; echo "${FAKE_STATE_INIT:-idle}" > "$M/fake/state"
	echo MOCKSRCV > "$M/srcv"; echo fw > "$M/fw"; : > "$M/kmsg"
	[ -n "${NOBINS:-}" ] || cp "$P"/bins/*.bin "$M/stage/"
	chmod 000 "$M/dbg"
}
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh" SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh"
export S3_TOOL_SHA=$(sha "$P/tests/fake_tool.sh") S3_RT_SHA=$(sha "$P/tests/fake_rt.sh") PY
# HOLD_READ must outlast the fake job's start, as on the laptop the 2.8 s outlast the fault
export RESET_WAIT=0 HEALTH_WAIT=0 HOLD_READ=0.5 HOLD_GAP=0.1 RT_LEAD=0
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw SGXFIVE_PROBE_BINS=$M/stage FAKE_LOG=$M/fake.log S3_OUT=$M/out HOME=$M/home"; }
KD() { echo "$M/out/$ATT/$1"; }
# runst DIR STAGE ENV...: run one stage in the current world with the driver's arguments (the sha256 of
# DIR's FROZEN.sha256, the attempt); echoes the status.  FSHA overrides the sha256 ("none": no argument).
runst() { local d=$1 st=$2; shift 2; local fs=${FSHA:-$(sha "$d/FROZEN.sha256")}
	if [ "$fs" = none ]; then env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" > "$M/log/$st.log" 2>&1
	else env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" "$fs" "$ATT" > "$M/log/$st.log" 2>&1; fi; echo $?; }

# 1. every stage, the frozen tables, default (frozen-hypothesis) outcomes: every job runs and is kept
world
for st in $(cat "$P/stages.txt"); do
	rc=$(runst "$P" "$st")
	t=$P/tables/$st.txt; n=$(grep -vc '^#' "$t"); k=$(KD "$st")
	got=$(grep -c '^== ' "$M/log/$st.log"); nc=$(( $(wc -l < "$k/cases.tsv") - 1 ))
	nheld=$(grep -v '^#' "$t" | grep -cE '\|(held|xferro)[ |]')
	nsnap=$(ls "$k" | grep -c 'snap[0-3]\.regs\.gz')
	# a dump is kept for every completed job that asks for one (a faulted job's context is gone)
	nd=$(awk -F'\t' 'NR > 1 && $9 == "ok" && $7 ~ /--dump-render/' "$k/cases.tsv" | grep -c .); kd=$(ls "$k" | grep -c 'tadata\.bin\.gz')
	h=$(cat "$M/fake/hold")
	[ "$rc" = 0 ] && [ "$got" = "$n" ] && [ "$nc" = "$n" ] && [ "$h" = N ] && [ "$kd" = "$nd" ] \
		&& [ "$nsnap" -ge $((nheld * 4 + n - nheld)) ] && grep -q '^## end' "$k/runner.log" \
		&& ok "$st: $got of $n jobs, $nc rows, $nsnap snapshots, $kd of $nd TA dumps, runner.log kept, hold N at the end" \
		|| bad "$st: rc $rc, $got of $n jobs, rows $nc, snapshots $nsnap, dumps $kd of $nd, hold $h"
done
cases=$(grep -c 'resgx545 case' "$M/kmsg"); holds=$(grep -c 'readback .* hold_recovery=Y' "$M/kmsg")
[ "$cases" = 10 ] && [ "$holds" = 5 ] && ok "kernel log: $cases case markers, $holds hold read-backs" || bad "markers: $cases cases, $holds holds"
grep -q 'resgx545 s3 health a6-320x400-max320 try [0-9]' "$M/kmsg" && ok "health triangles carry their own markers" || bad "health markers"
awk -F'\t' 'NR > 1 && ($8 == "" || $9 == "") { x++ } END { exit x > 0 }' "$M"/out/"$ATT"/*/cases.tsv && ok "rc and class on every row" || bad "rc/class"
grep -q 'e1-xfer-ro.*xferro.*fault' "$(KD s3-xfer)/cases.tsv" && ok "xfer_ro: classified by the held registers (fault)" || bad "xfer_ro class"
# review fix 2: the debugfs reset is written while the hold is still Y (it becomes the held recovery);
# writing N first would let the watchdog recover and make the reset a second halt
r1=$(grep -n 'resgx545 s3 reset e1-ta-read ' "$M/kmsg" | cut -d: -f1); n1=$(grep -n 'readback e1-ta-read hold_recovery=N' "$M/kmsg" | cut -d: -f1)
[ -n "$r1" ] && [ -n "$n1" ] && [ "$r1" -lt "$n1" ] && ok "held job: reset written with the hold Y, then N read back" || bad "reset/N order: reset line $r1, N line $n1"
grep -q 'stalls job' "$M/kmsg" && bad "the fake watchdog recovered a held fault (N written before the reset)" || ok "no watchdog recovery of a held fault"
nres=$(awk '/resgx545 case e1-tex /{f=1} /resgx545 s3 class e1-tex /{f=0} f && /SGX reset:/' "$M/kmsg" | grep -c .)
[ "$nres" = 1 ] && ok "e1-tex: exactly one reset line after its case marker (no second halt)" || bad "e1-tex: $nres reset lines"
MAIN=$M; MATT=$ATT
# the scorers on the mock output (the fakes play the frozen H4 / HE outcomes): the whole chain gives verdicts
for st in $(cat "$P/stages.txt"); do
	s=$("$PY" "$P/score/score_s3.py" "$st" "$MAIN/out/$MATT/$st" | grep '^SUMMARY:')
	case "$st:$s" in
	s3-a-safe:*"H4 for what the TA writes"*|s3-e1-ctl:*"method ok"*|s3-e1:*"e1-tex HE"|s3-a-fault:*"H4 sufficiency"*|s3-xfer:*"e1-xfer-ro HE") ok "scorer $st: ${s:0:110}" ;;
	*) bad "scorer $st: ${s:-no SUMMARY}" ;;
	esac
done
"$PY" "$P/score/score_s3.py" gate s3-a-fault "$MAIN/out/$MATT" > /dev/null && ok "gate s3-a-fault open on passing controls" || bad "gate"
v=$("$PY" "$P/score/score_s3.py" verdict "$MAIN/out/$MATT")
case "$v" in *"Q286: closed H4"*"Q003 E1: HE for every held kind"*) ok "verdict: Q286 H4, Q003 HE" ;; *) bad "verdict: $v" ;; esac

# 2. stop rules: check NAME WANTED_RC STAGE ENV...
check() { local nm=$1 want=$2 st=$3; shift 3; world; local rc; rc=$(runst "$P" "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##' "$M/log/$st.log" | head -5 | sed 's/^/     /'; }; }
FAKE_HOLD_INIT=Y check "preflight: hold_recovery Y at the start" 1 s3-a-safe; FAKE_HOLD_INIT=N
[ "$(cat "$M/fake/hold")" = Y ] && [ ! -f "$M/fake/resets" ] && ok "  another session's hold left as it was: no knob write, no reset" || bad "  the failed preflight touched the GPU"
check "fatal kernel message" 3 s3-e1-ctl FAKE_RULES='--fault|fatal'
check "plain job does not return (freeze)" 6 s3-a-safe FAKE_RULES='--width 256|timeout'
check "held job does not return (freeze)" 6 s3-e1-ctl FAKE_RULES='--fault|timeout'
check "unexpected fault in a completing job" 4 s3-a-safe FAKE_RULES='--width 320 --height 128|fault:0x90004:0x20006062:0x480'
check "unexplained failure (rc 1, no diff line)" 4 s3-a-safe FAKE_RULES='--width 320 --height 128|nodiff'
check "a wrong image without expectdiff stops" 4 s3-a-safe FAKE_RULES='cmd:1=0x20000000|diff'
check "a wrong image in a5 (expectdiff) is recorded" 0 s3-a-fault FAKE_RULES='--max-width 544|diff'
grep -q 'a5-320x400-max544.*	ok	held' "$(KD s3-a-fault)/cases.tsv" && ok "  a5 recorded as ok (diff kept for the scorer)" || bad "  a5 diff row"
# review fix 4: a completing a6 with a wrong image is scored, not a stop; xfer_ro is the last stage
check "a6 completing with a wrong image is recorded, then scored" 0 s3-a-fault FAKE_RULES='--max-width 320 --max-height 400|diff'
s=$("$PY" "$P/score/score_s3.py" s3-a-fault "$(KD s3-a-fault)" | grep '^SUMMARY:')
case "$s" in *"a6 control failed"*COMPLETED*) ok "  scored: the a6 control failed (completed)" ;; *) bad "  a6 score: $s" ;; esac
[ "$(tail -n 1 "$P/stages.txt")" = s3-xfer ] && ! grep -q xferro "$P/tables/s3-e1.txt" && ok "xfer_ro runs alone in the last stage" || bad "xfer_ro stage order"
check "xfer_ro unavailable (-ENODEV): a stop in the last stage only" 4 s3-xfer FAKE_XFER_FAIL=1
check "a held fault that does not clear: two resets, then stop" 10 s3-e1-ctl FAKE_STUCK=1
r=$(grep -c . "$M/fake/resets"); [ "$r" = 4 ] && ok "  exactly two resets after the hold (and the start's and the pre-job one), none at exit" || bad "  resets: $r"
check "hold_recovery does not read back N" 11 s3-e1-ctl FAKE_HOLD_STUCK=1
check "hold_recovery does not read back Y (job not started)" 9 s3-e1-ctl FAKE_HOLD_NOY=1
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started without its hold" || ok "  no job started"
check "registers unreadable" 12 s3-e1-ctl FAKE_SNAP_FAIL=1
check "health: the first failed recovery stops" 5 s3-a-safe FAKE_HEALTH_BAD=1
check "a held hang that is a hypothesis is measured" 0 s3-e1-ctl FAKE_RULES='--fault|hang'
grep -q 'e1-ta-read.*	hang	held' "$(KD s3-e1-ctl)/cases.tsv" && ok "  classified hang (hold message, no fault bit)" || bad "  hang class"
# review fix 3: the pre-job reset must succeed and leave no fault latched
check "the pre-job reset fails" 13 s3-a-safe FAKE_RESET_FAIL_FROM=2
FAKE_STATE_INIT='0x90008 0x3e000001 0x480 0x20000000' check "a fault latched before the job (snap 0)" 14 s3-e1-ctl FAKE_STUCK=1
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started over a latched fault" || ok "  no job started"
NOBINS=1 world
rc=$(runst "$P" s3-e1); [ "$rc" = 8 ] && ok "missing staged program (rc 8)" || bad "missing program: rc $rc"
# review fix 5: the laptop's freeze is the Mac's
world; rc=$(FSHA=0000 runst "$P" s3-a-safe)
[ "$rc" = 1 ] && grep -q "FROZEN.sha256 is not the Mac's" "$M/log/s3-a-safe.log" && [ ! -f "$M/fake/resets" ] && ok "a FROZEN.sha256 other than the Mac's: rc 1, nothing touched" || bad "frozen sha mismatch: rc $rc"
world; rc=$(FSHA=none runst "$P" s3-a-safe); [ "$rc" = 1 ] && ok "no frozen sha256 argument: rc 1" || bad "no sha argument: rc $rc"
# review fix 6: SIGPIPE / SIGHUP ignored, the output also in runner.log: a dropped ssh does not stop the stage
world
env $(envw) bash "$P/run/run_stage.sh" s3-e1-ctl "$(sha "$P/FROZEN.sha256")" "$ATT" 2>&1 | head -c 1 > /dev/null; rc=${PIPESTATUS[0]}
nc=$(( $(wc -l < "$(KD s3-e1-ctl)/cases.tsv") - 1 ))
[ "$rc" = 0 ] && [ "$nc" = 2 ] && grep -q '^## end' "$(KD s3-e1-ctl)/runner.log" && [ "$(cat "$M/fake/hold")" = N ] \
	&& ok "the reader of the runner's output goes away: the stage completes, runner.log has it all" || bad "closed pipe: rc $rc, rows $nc"
# review fix 7: one directory an attempt, never merged
world; rc=$(runst "$P" s3-a-safe); rc2=$(runst "$P" s3-a-safe)
[ "$rc" = 0 ] && [ "$rc2" = 1 ] && grep -q 'not empty' "$M/log/s3-a-safe.log" && ok "a second run into the same attempt directory is refused" || bad "attempt reuse: rc $rc then $rc2"
ATT=att-second; rc3=$(runst "$P" s3-a-safe)
[ "$rc3" = 0 ] && [ -f "$M/out/att-second/s3-a-safe/cases.tsv" ] && ok "a new attempt gets its own directory" || bad "new attempt: rc $rc3"

# 3. a copy of the tree: a changed table, an unknown knob, a group bound, a bare debugfs access
copytree() { C=$W/tree$N; mkdir -p "$C"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/stages.txt" "$P/FROZEN.sha256" "$P/PREDICTIONS.sha256" "$C/"; }
world; copytree
echo "x-extra|heldout|safe|stophang|-|tri" >> "$C/tables/s3-a-safe.txt"
rc=$(runst "$C" s3-a-safe)
[ "$rc" = 1 ] && grep -q 'not the frozen one' "$M/log/s3-a-safe.log" && ok "a table that is not the frozen one (rc 1)" || bad "changed table: rc $rc"
world; copytree
printf '#stage s3-mock\nm-1|heldout|risky|held hypo:g:1|-|tri --fault --wait-ms 20000\nm-2|heldout|risky|held hypo:g:1|-|tri --fault --wait-ms 20000\nm-3|heldout|risky|kregx|-|tri\n' > "$C/tables/s3-mock.txt"
(cd "$C" && run/freeze_s3.sh freeze > /dev/null)
rc=$(runst "$C" s3-mock)
grep -q 'm-2 skipped: group g reached its 1 events' "$M/log/s3-mock.log" && ok "hypo group: one fault measured, the next job of the group skipped" || bad "group bound"
[ "$rc" = 7 ] && ok "unknown knob stops (rc 7)" || bad "unknown knob: rc $rc"
world; copytree
printf '\nprobe_extra() { [ -e "$D/hold_recovery" ] || { echo "no hold_recovery"; exit 1; }; }\nprobe_extra\n' >> "$C/run/lib_s3.sh"
(cd "$C" && run/freeze_s3.sh freeze > /dev/null)
rc=$(runst "$C" s3-a-safe)
[ "$rc" = 1 ] && ok "a bare [ -e \"\$D/...\" ] fails against root-only debugfs (rc 1)" || bad "unprivileged access ran: rc $rc"
"$C/run/guard_s3.sh" "$C" > "$W/guard-bad.txt" 2>&1 && bad "guard missed the bare access" || { grep -q 'UNPRIVILEGED DEBUGFS ACCESS' "$W/guard-bad.txt" && ok "guard: finds the bare debugfs access"; }
for inj in 'echo 1 | sudo -n tee "$D/kregnow"' 'ls /sys/kernel/debug/dri/*/sgx' 'until false; do :; done' 'x=$(cat f | tail -1)' \
	'sudo -n tee "$D/reset" || true' 'sudo -n timeout 60 "$T" tri'; do
	copytree; printf '%s\n' "$inj" >> "$C/run/lib_s3.sh"
	"$C/run/guard_s3.sh" "$C" > /dev/null 2>&1 && bad "guard missed: $inj" || ok "guard: refuses $inj"
done
copytree; grep -v "^trap '' PIPE HUP" "$P/run/run_stage.sh" > "$C/run/run_stage.sh"
"$C/run/guard_s3.sh" "$C" > /dev/null 2>&1 && bad "guard missed a runner without trap '' PIPE HUP" || ok "guard: refuses a runner that does not ignore PIPE and HUP"
"$P/run/guard_s3.sh" && ok "guard: the real scripts are clean" || bad "guard on the real scripts"

# 4. the driver: dry run (bounded commands, gates, the frozen sha256 and the attempt) and numeric knob compare
d=$(S3_ATT=attX SGX_DRY_RUN=1 bash "$P/run/s3.sh" 2>&1)
fs=$(sha "$P/FROZEN.sha256")
echo "$d" | grep -q 'score_s3.py gate s3-a-fault' && echo "$d" | grep -q 'bounded 900 ssh' && echo "$d" | grep -q 'bounded 300 scp' \
	&& echo "$d" | grep -q "run_stage.sh s3-a-safe $fs attX" && echo "$d" | grep -q "s3-out/attX/s3-a-safe .*/out/attX/s3-a-safe" \
	&& echo "$d" | grep -q 'score_s3.py gate s3-xfer' \
	&& ok "driver dry run: gates, bounded ssh/scp, the frozen sha256 and one directory an attempt" || bad "driver dry run"
num_eq 0x00000000 0 && num_eq 0x00000422 0x422 && ! num_eq abc 0 && ok "numeric knob compare" || bad "num_eq"
bounded 1 sleep 5 2>/dev/null; [ $? = 142 ] && ok "bounded: the alarm ends a stuck command (142)" || bad "bounded"
echo "work dir (kept for inspection): $W"
exit $fail
