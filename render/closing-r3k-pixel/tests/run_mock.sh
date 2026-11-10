#!/bin/bash
# tests/run_mock.sh: the R3K runner end to end against a fake tool, a fake regtimeline and a fake debugfs whose directory is mode
# 000 (only the sudo shim reaches it: an unprivileged access fails, as on the laptop), then every stop rule, the guard, staging and
# the whole driver (k.sh) with fake ssh/scp/health.  Needs a current freeze (run/freeze_k.sh freeze).
# The fake kernel plays the watchdog (hold_recovery written N while a render fault is latched recovers it) and the BIF's
# kregnow rows (what clears: FAKE_BIF w1c | clr | rst | other).  Nothing is deleted: every run writes into a new mktemp
# directory, printed at the end.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
W=$(mktemp -d)
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
. "$P/run/lib_check.sh"
"$P/run/freeze_k.sh" verify > /dev/null || { echo "FAIL: not frozen (run/freeze_k.sh freeze)"; exit 1; }
N=0
# a fresh fake laptop: debugfs (mode 000) + its real files, the fake GPU state, the kernel log
world() {
	N=$((N + 1)); M=$W/w$N; ATT=att$N
	mkdir -p "$M/dbg" "$M/dbgreal" "$M/fake" "$M/stage" "$M/out" "$M/log" "$M/home"
	for f in reset regs render_param render_tadata kpoke kicker kregnow; do : > "$M/dbgreal/$f"; done
	echo N > "$M/dbgreal/hold_recovery"; echo 0x422 > "$M/dbgreal/render_pb_pages"; echo 0 > "$M/dbgreal/alias_skip"
	echo "${FAKE_RGN_INIT:-1}" > "$M/dbgreal/render_rgn_arrays"
	echo "${FAKE_HOLD_INIT:-N}" > "$M/fake/hold"; echo "${FAKE_STATE_INIT:-idle}" > "$M/fake/state"; echo 0 > "$M/fake/ctrl"
	echo MOCKSRCV > "$M/srcv"; echo fw > "$M/fw"; : > "$M/kmsg"
	[ -n "${NOBINS:-}" ] || cp "$P"/bins/*.bin "$M/stage/"
	chmod 000 "$M/dbg"
}
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh" SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh"
export K_TOOL_SHA=$(sha "$P/tests/fake_tool.sh") K_RT_SHA=$(sha "$P/tests/fake_rt.sh") K_SRCV_EXPECT=MOCKSRCV PY
# HOLD_READ must outlast the fake job's start, as on the laptop the 2.8 s outlast the fault
export RESET_WAIT=0 HEALTH_WAIT=0 HOLD_READ=0.5 HOLD_GAP=0.1 RT_LEAD=0 BIF_WATCH=0.1
envw() { echo "SGXFIVE_DEBUGFS=$M/dbg FAKE_DBGREAL=$M/dbgreal FAKE_DIR=$M/fake KMSG=$M/kmsg SRCV_PATH=$M/srcv FW_PATH=$M/fw SGXFIVE_PROBE_BINS=$M/stage FAKE_LOG=$M/fake.log K_OUT=$M/out HOME=$M/home"; }
KD() { echo "$M/out/$ATT/$1"; }
# runst DIR STAGE ENV...: run one stage in the current world with the driver's arguments; echoes the status.  FSHA overrides the
# sha256 of DIR's FROZEN.sha256 ("none": no argument).
runst() { local d=$1 st=$2; shift 2; local fs=${FSHA:-$(sha "$d/FROZEN.sha256")}
	if [ "$fs" = none ]; then env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" > "$M/log/$st.log" 2>&1
	else env $(envw) "$@" bash "$d/run/run_stage.sh" "$st" "$fs" "$ATT" > "$M/log/$st.log" 2>&1; fi; echo $?; }
rgn_file() { echo $(( $(cat "$M/dbgreal/render_rgn_arrays") )); }
ALLSTAGES="k-f4 k-pb0 k-pb k-bif"

# 1. every stage, the frozen tables, the default outcomes: every job runs and is kept
world
for st in $ALLSTAGES; do
	rc=$(runst "$P" "$st")
	t=$P/tables/$st.txt; n=$(grep -vc '^#' "$t"); k=$(KD "$st")
	got=$(grep -c '^== ' "$M/log/$st.log"); nc=$(( $(wc -l < "$k/cases.tsv") - 1 ))
	nheld=$(grep -v '^#' "$t" | grep -cE '\|held[ |]')
	nsnap=$(ls "$k" | grep -c 'snap[0-3]\.regs\.gz')
	nb=$(ls "$k" | grep -c 'snapb[0-5]\.regs\.gz'); nbif=$(grep -v '^#' "$t" | grep -cE '\|[^|]* bif|bif[ |]')
	nd=$(awk -F'\t' 'NR > 1 && $9 == "ok" && $7 ~ /--dump-render/' "$k/cases.tsv" | grep -c .); kd=$(ls "$k" | grep -c 'tadata\.bin\.gz')
	h=$(cat "$M/fake/hold")
	[ "$rc" = 0 ] && [ "$got" = "$n" ] && [ "$nc" = "$n" ] && [ "$h" = N ] && [ "$kd" = "$nd" ] && [ "$nsnap" -ge $((nheld * 4 + n - nheld)) ] \
		&& [ "$nb" = $((nbif * 6)) ] && grep -q '^## end' "$k/runner.log" && [ "$(rgn_file)" = 1 ] \
		&& ok "$st: $got of $n jobs, $nc rows, $nsnap snapshots, $nb BIF snapshots, $kd of $nd TA dumps kept, runner.log kept, hold N, render_rgn_arrays 1 at the end" \
		|| bad "$st: rc $rc, $got of $n jobs, rows $nc, snapshots $nsnap, bif snapshots $nb of $((nbif * 6)), dumps $kd of $nd, hold $h, knob $(rgn_file)"
done
cases=$(grep -c 'resgx545 case' "$M/kmsg"); holds=$(grep -c 'readback .* hold_recovery=Y' "$M/kmsg")
[ "$cases" = 24 ] && [ "$holds" = 5 ] && ok "kernel log: $cases case markers (24 jobs), $holds hold read-backs (c1 and the four held bif rows)" || bad "markers: $cases cases, $holds holds"
grep -q 'resgx545 r3k health f1-ta-read try [0-9]' "$M/kmsg" && ok "health triangles carry their own markers" || bad "health markers"
nkw=$(grep -c . "$M/fake/kregnow-writes"); okkw=$(grep -vcE '^(0x0c04=0x[0-9a-f]+|0x0c00\^=0x10)$' "$M/fake/kregnow-writes")
[ "$nkw" = 20 ] && [ "$okkw" = 0 ] && ok "kregnow: 20 writes (5 rows x 4), only the two allowed forms" || bad "kregnow writes: $nkw, outside the forms: $okkw ($(sort -u "$M/fake/kregnow-writes" | tr '\n' ' '))"
grep -q '^0x0c04=0x1$' "$M/fake/kregnow-writes" && grep -q '^0x0c04=0x10008$' "$M/fake/kregnow-writes" && grep -q '^0x0c04=0x10004$' "$M/fake/kregnow-writes" && grep -q '^0x0c04=0x10002$' "$M/fake/kregnow-writes" \
	&& ok "the set bits written are the fault word without bit 19 (0x10008, 0x10004, 0x10002)" || bad "set bits: $(grep 0x0c04 "$M/fake/kregnow-writes" | sort -u | tr '\n' ' ')"
sort -u "$M/fake/rgn-writes" | tr '\n' ' ' | grep -qE '^(1 4 |4 1 |4 |1 )$' && ok "render_rgn_arrays only ever written 1 or 4 ($(sort -u "$M/fake/rgn-writes" | tr '\n' ' '))" || bad "rgn writes: $(sort -u "$M/fake/rgn-writes" | tr '\n' ' ')"
[ "$(tail -n 1 "$M/fake/rgn-writes")" = 1 ] && ok "the last knob write of the session is the restore to 1" || bad "last knob write $(tail -n 1 "$M/fake/rgn-writes")"
grep -q 'resgx545 r3k rgn c1-288x144-k1 1' "$M/kmsg" && grep -q 'resgx545 r3k rgn h1-288x144-k4 4' "$M/kmsg" && ok "the knob value of each row is in the kernel log (c1 1, h1 4)" || bad "rgn markers"
awk -F'\t' 'NR > 1 && ($8 == "" || $9 == "") { x++ } END { exit x > 0 }' "$M"/out/"$ATT"/*/cases.tsv && ok "rc and class on every row" || bad "rc/class"
awk -F'\t' '$1 == "c1-288x144-k1" && $9 == "fault" && $10 == "held"' "$(KD k-f4)/cases.tsv" | grep -q . && ok "c1 (knob 1, 288x144) faulted held, as E729; every h row completed" || bad "c1 class"
[ "$(awk -F'\t' '$1 ~ /^h/ && $9 == "ok"' "$(KD k-f4)/cases.tsv" | wc -l | tr -d ' ')" = 8 ] && ok "  8 h rows class ok" || bad "h rows"
r=$(grep -n 'resgx545 r3k reset f1-ta-read ' "$M/kmsg" | cut -d: -f1); k1=$(grep -n 'resgx545 r3k kregnow f1-ta-read 1 ' "$M/kmsg" | cut -d: -f1); k4=$(grep -n 'resgx545 r3k kregnow f1-ta-read 4 ' "$M/kmsg" | cut -d: -f1); n1=$(grep -n 'readback f1-ta-read hold_recovery=N' "$M/kmsg" | cut -d: -f1)
[ -n "$r" ] && [ -n "$k1" ] && [ "$k1" -lt "$k4" ] && [ "$k4" -lt "$r" ] && [ "$r" -lt "$n1" ] && ok "bif row: the four writes come inside the hold, then the reset (hold still Y), then N read back" || bad "bif order: writes $k1-$k4, reset $r, N $n1"
grep -q 'SGX reset: after the fault clear BIF_FAULT' "$M/kmsg" && ok "the fake reset prints the new kernel lines the scorer reads" || bad "reset lines"
# the scorers on the mock output: FAKE_BIF=rst (default), FAKE_PB=old: the whole chain gives verdicts
MAIN=$M; MATT=$ATT
for st in $ALLSTAGES; do
	s=$("$PY" "$P/score/score_k.py" "$st" "$MAIN/out/$MATT/$st" | grep '^SUMMARY:')
	case "$st:$s" in
	k-f4:*"8 of 8 held-out rows complete"*|k-pb0:*"'pb-d0-te40': 'PASS'"*"'pb-p1-te40': 'PASS'"*|k-pb:*"Q285: H-OLD"*|k-bif:*"H-RST: 4 of 4 held rows agree"*) ok "scorer $st: ${s:0:130}" ;;
	*) bad "scorer $st: ${s:-no SUMMARY}" ;;
	esac
done
"$PY" "$P/score/score_k.py" gate k-pb "$MAIN/out/$MATT" > /dev/null && ok "gate k-pb open on passing controls" || bad "gate"
v=$("$PY" "$P/score/score_k.py" verdict "$MAIN/out/$MATT")
case "$v" in *"Q140: k-f4: 8 of 8"*"Q285: H-OLD"*"Q003: H-RST"*) ok "verdict: Q140 8 of 8, Q285 H-OLD, Q003 H-RST" ;; *) bad "verdict: $v" ;; esac
# the other worlds of what clears and of the parameter buffer, through the runner and the scorer
for hyp in w1c clr; do
	world; rc=$(runst "$P" k-bif FAKE_BIF=$hyp)
	s=$("$PY" "$P/score/score_k.py" k-bif "$(KD k-bif)" | grep '^SUMMARY:')
	H=$(echo $hyp | tr a-z A-Z); [ "$hyp" = clr ] && H=H-CLR || H=H-W1C
	[ "$rc" = 0 ] && echo "$s" | grep -q "$H: 4 of 4 held rows agree" && ok "FAKE_BIF=$hyp: the runner and the scorer give $H" || bad "FAKE_BIF=$hyp: rc $rc $s"
done
world; rc=$(runst "$P" k-pb FAKE_PB=field); s=$("$PY" "$P/score/score_k.py" k-pb "$(KD k-pb)" | grep '^SUMMARY:')
[ "$rc" = 0 ] && echo "$s" | grep -q 'Q285: H-FIELD' && ok "FAKE_PB=field: H-FIELD" || bad "FAKE_PB=field: rc $rc $s"
world; rc=$(runst "$P" k-pb FAKE_PB=bothempty); s=$("$PY" "$P/score/score_k.py" k-pb "$(KD k-pb)" | grep '^SUMMARY:')
[ "$rc" = 0 ] && echo "$s" | grep -q 'Q030' && ok "FAKE_PB=bothempty: cannot tell, parked under Q030" || bad "FAKE_PB=bothempty: rc $rc $s"
world; rc=$(runst "$P" k-pb FAKE_NO_APPLY=1); s=$("$PY" "$P/score/score_k.py" k-pb "$(KD k-pb)" | grep '^SUMMARY:')
[ "$rc" = 0 ] && echo "$s" | grep -q 'cannot tell' && ok "pokes not applied (no kernel log line): cannot tell, not a verdict" || bad "no-apply: rc $rc $s"
world; rc=$(runst "$P" k-pb FAKE_PB_HANG_P4=1)
[ "$rc" = 4 ] && ok "a hang of a poked job is an unexpected stop (rc 4)" || bad "pb hang: rc $rc"

# 2. stop rules: check NAME WANTED_RC STAGE ENV...
check() { local nm=$1 want=$2 st=$3; shift 3; world; local rc; rc=$(runst "$P" "$st" "$@")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || { bad "$nm: rc $rc, wanted $want"; grep -E 'STOP|abort|^##' "$M/log/$st.log" | head -5 | sed 's/^/     /'; }; }
FAKE_HOLD_INIT=Y check "preflight: hold_recovery Y at the start" 1 k-f4; FAKE_HOLD_INIT=N
[ "$(cat "$M/fake/hold")" = Y ] && [ ! -f "$M/fake/resets" ] && [ ! -f "$M/fake/rgn-writes" ] && ok "  another session's hold left as it was: no knob write, no reset" || bad "  the failed preflight touched the GPU"
FAKE_RGN_INIT=4 check "preflight: render_rgn_arrays not 1 at the start (another session's value)" 1 k-f4; FAKE_RGN_INIT=1
[ "$(rgn_file)" = 4 ] && [ ! -f "$M/fake/rgn-writes" ] && [ ! -f "$M/fake/resets" ] && ok "  the knob left as it was (4): nothing written, no reset" || bad "  the failed preflight wrote the knob"
world; echo OTHERSRCV > "$M/srcv"; rc=$(runst "$P" k-f4)
[ "$rc" = 1 ] && grep -q 'the loaded module is not the installed one' "$M/log/k-f4.log" && [ ! -f "$M/fake/resets" ] && ok "srcversion of the loaded module differs from the installed one: rc 1, nothing touched" || bad "srcversion check: rc $rc"
world; rc=$(K_SRCV_EXPECT=230E0EF50FFFD606C53AE3C runst "$P" k-f4)
[ "$rc" = 1 ] && grep -q 'is not the expected build (230E0EF50FFFD606C53AE3C)' "$M/log/k-f4.log" && [ ! -f "$M/fake/resets" ] && ok "installed = loaded but not the expected build: rc 1, nothing touched" || bad "expected build check: rc $rc"
grep -q '^SRCV_EXPECT=230E0EF50FFFD606C53AE3C$' "$P/run/k.env" && ok "k.env pins the new module's srcversion 230E0EF50FFFD606C53AE3C" || bad "k.env srcversion pin"
for df in hold_recovery regs alias_skip render_param render_tadata render_pb_pages reset render_rgn_arrays kregnow kpoke kicker; do
	world; mv "$M/dbgreal/$df" "$M/dbgreal/$df.gone"; rc=$(runst "$P" k-f4)
	[ "$rc" = 1 ] && grep -q "has no debugfs $df" "$M/log/k-f4.log" && [ ! -f "$M/fake/resets" ] && ok "preflight: no debugfs $df: rc 1, nothing touched" || bad "preflight without $df: rc $rc"
done
world; rc=$(FAKE_KREGNOW_OLD=1 runst "$P" k-f4)
[ "$rc" = 1 ] && grep -q 'lists no 0x0c00 and 0x0c04 rows' "$M/log/k-f4.log" && ok "preflight: kregnow without the BIF rows (the old module): rc 1" || bad "kregnow rows check: rc $rc"
world; rc=$(K_TOOL_SHA=0000 runst "$P" k-f4)
[ "$rc" = 1 ] && grep -q "the tool is not R1's" "$M/log/k-f4.log" && ok "preflight: a tool that is not R1's build (rc 1)" || bad "tool sha: rc $rc"
check "fatal kernel message in a 4x row" 3 k-f4 FAKE_RULES='--width 288 --height 144 --max-width 288|fatal'
[ "$(rgn_file)" = 1 ] && grep -q 'render_rgn_arrays=0x00000001' "$M/log/k-f4.log" && ok "  after the fatal stop the knob is restored to 1 (and printed)" || bad "  knob after fatal stop: $(rgn_file)"
check "a 4x row does not return (freeze)" 6 k-f4 FAKE_RULES='--width 256 --height 288|timeout'
[ "$(rgn_file)" = 1 ] && ok "  after the freeze stop the knob is restored to 1" || bad "  knob after freeze stop: $(rgn_file)"
check "an h row that faults is measured (a hypothesis), the stage goes on" 0 k-f4 FAKE_RULES='--width 384 --height 288|fault:0x90004:0x20008062:0x480
--width 384 --height 384|fault:0x90004:0x20008062:0x480'
grep -c 'class fault' "$M/log/k-f4.log" | grep -q '^[1-9]' && ok "  the fault was recorded and the health triangle ran" || bad "  fault class lines"
check "two h faults end the h rows (the group bound), c1 still runs" 0 k-f4 FAKE_RULES='--width 256 --height 288|fault:0x90004:0x20006062:0x480
--width 384 --height 384|fault:0x90004:0x20008062:0x480'
grep -q 'skipped: group h4 reached its 2 events' "$M/log/k-f4.log" && grep -q '^c1-288x144-k1' "$(KD k-f4)/cases.tsv" && ok "  h4's later rows skipped, c1 ran last" || bad "  group bound"
check "unexplained failure (rc 1, no diff line) in an h row" 4 k-f4 FAKE_RULES='--width 320 --height 160|nodiff'
check "a parameter-buffer overflow in h8 is class fail (the tool says it): stop, knob restored" 4 k-f4 FAKE_RULES='--width 1024|overflow'
[ "$(rgn_file)" = 1 ] && ok "  knob restored after the stop" || bad "  knob $(rgn_file)"
check "render_rgn_arrays does not read back 4 (writes ignored)" 19 k-f4 FAKE_RGN_STUCK=1
grep -q '^c3-64x64-k1' "$(KD k-f4)/cases.tsv" && ! grep -q '^c2-64x64-k4' "$(KD k-f4)/cases.tsv" && ok "  c3 ran, c2 did not run (its knob did not read back)" || bad "  rows after rc 19"
check "the pre-job reset fails" 13 k-f4 FAKE_RESET_FAIL_FROM=2
check "health: the first failed recovery stops" 5 k-f4 FAKE_HEALTH_BAD=1
check "a held fault that does not clear: two resets, then stop" 10 k-bif FAKE_STUCK=1
check "hold_recovery does not read back N" 11 k-bif FAKE_HOLD_STUCK=1
check "hold_recovery does not read back Y (job not started)" 9 k-bif FAKE_HOLD_NOY=1
check "registers unreadable" 12 k-bif FAKE_SNAP_FAIL=1
FAKE_STATE_INIT='0x90008 0x3e000001 0x480 0x20000000' check "a fault latched before the job (snap 0)" 14 k-bif FAKE_STUCK=1
grep -q 'resgx545 case' "$M/kmsg" && bad "  a job started over a latched fault" || ok "  no job started"
check "the laptop does not answer after a BIF write (E317): stop, rc 18" 18 k-bif FAKE_KW_STALL=1
[ "$(rgn_file)" = 1 ] && [ "$(cat "$M/fake/hold")" = N ] && [ "$(grep -c . "$M/fake/kregnow-writes")" = 1 ] && [ "$(grep -c . "$M/fake/resets")" = 2 ] && ok "  one write only, no more writes, no reset after the stall (the 2 resets are the session's start and the pre-job one); hold N and the knob restored" || bad "  after the stall: writes $(grep -c . "$M/fake/kregnow-writes"), resets $(grep -c . "$M/fake/resets" 2>/dev/null)"
check "regs do not answer after a BIF write (E317): stop, rc 18" 18 k-bif FAKE_REGS_STALL=1
check "kregnow refused (EBUSY): recorded, the stage goes on" 0 k-bif FAKE_KW_EBUSY=1
gzip -dc "$(KD k-bif)/f1-ta-read.kw.txt.gz" | grep -q '1 0x0c04=0x1 rc 1' && ok "  the refused status is in the kw file" || bad "  kw file"
s=$("$PY" "$P/score/score_k.py" k-bif "$(KD k-bif)" | grep '^SUMMARY:'); echo "$s" | grep -q 'cannot tell' && ok "  the scorer: refused writes are NODATA, never 'nothing clears'" || bad "  scorer: $s"
NOBINS=1 world
rc=$(runst "$P" k-bif); [ "$rc" = 8 ] && ok "missing staged program (rc 8)" || bad "missing program: rc $rc"
world; rc=$(FSHA=0000 runst "$P" k-f4)
[ "$rc" = 1 ] && grep -q "FROZEN.sha256 is not the Mac's" "$M/log/k-f4.log" && [ ! -f "$M/fake/resets" ] && ok "a FROZEN.sha256 other than the Mac's: rc 1, nothing touched" || bad "frozen sha mismatch: rc $rc"
world; rc=$(FSHA=none runst "$P" k-f4); [ "$rc" = 1 ] && ok "no frozen sha256 argument: rc 1" || bad "no sha argument: rc $rc"
# SIGPIPE / SIGHUP ignored, the output also in runner.log: a dropped ssh does not stop the stage
world
env $(envw) bash "$P/run/run_stage.sh" k-pb0 "$(sha "$P/FROZEN.sha256")" "$ATT" 2>&1 | head -c 1 > /dev/null; rc=${PIPESTATUS[0]}
nc=$(( $(wc -l < "$(KD k-pb0)/cases.tsv") - 1 ))
[ "$rc" = 0 ] && [ "$nc" = 3 ] && grep -q '^## end' "$(KD k-pb0)/runner.log" && [ "$(cat "$M/fake/hold")" = N ] \
	&& ok "the reader of the runner's output goes away: the stage completes, runner.log has it all" || bad "closed pipe: rc $rc, rows $nc"
# one directory an attempt, never merged
world; rc=$(runst "$P" k-pb0); rc2=$(runst "$P" k-pb0)
[ "$rc" = 0 ] && [ "$rc2" = 1 ] && grep -q 'not empty' "$M/log/k-pb0.log" && ok "a second run into the same attempt directory is refused" || bad "attempt reuse: rc $rc then $rc2"
ATT=att-second; rc3=$(runst "$P" k-pb0)
[ "$rc3" = 0 ] && [ -f "$M/out/att-second/k-pb0/cases.tsv" ] && ok "a new attempt gets its own directory" || bad "new attempt: rc $rc3"

# 3. a copy of the tree: a changed table, an unknown knob, a tri row without expectdiff, a bare debugfs access, a forbidden write
copytree() { C=$W/tree$N; mkdir -p "$C"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/gen" "$P/stages.txt" "$P/conditional.txt" "$P/TABLES.md" "$P/FROZEN.sha256" "$P/PREDICTIONS.sha256" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$C/"; }
world; copytree
echo "x-extra|heldout|safe|expectdiff|-|probe" >> "$C/tables/k-bif.txt"
rc=$(runst "$C" k-bif)
[ "$rc" = 1 ] && grep -q 'not the frozen one' "$M/log/k-bif.log" && ok "a table that is not the frozen one (rc 1)" || bad "changed table: rc $rc"
world; copytree
printf '#stage k-mock\nm-1|heldout|risky|kregx|-|tri\n' > "$C/tables/k-mock.txt"
(cd "$C" && run/freeze_k.sh freeze > /dev/null)
rc=$(runst "$C" k-mock)
[ "$rc" = 7 ] && ok "unknown knob stops (rc 7)" || bad "unknown knob: rc $rc"
world; copytree
printf '#stage k-mock\nm-1|heldout|risky|rgn:3 expectdiff|-|tri --keep-going --width 64 --height 64\n' > "$C/tables/k-mock.txt"
(cd "$C" && run/freeze_k.sh freeze > /dev/null)
rc=$(runst "$C" k-mock)
[ "$rc" = 7 ] && ok "a rgn knob other than 1 or 4 stops (rc 7)" || bad "rgn:3: rc $rc"
world; copytree
printf '#stage k-mock\nm-1|heldout|risky|stophang|-|tri --keep-going --width 64 --height 64\n' > "$C/tables/k-mock.txt"
(cd "$C" && run/freeze_k.sh freeze > /dev/null)
rc=$(runst "$C" k-mock)
[ "$rc" = 1 ] && grep -q 'a tri row without expectdiff' "$M/log/k-mock.log" && [ ! -f "$M/fake/resets" ] && ok "a tri row without expectdiff is refused before anything runs (rc 1)" || bad "missing expectdiff: rc $rc"
# the allow-lists of lib_k.sh at run time: a forbidden kregnow spec and a forbidden debugfs name stop at once (rc 7)
world; copytree
printf '\nbif_write x 9 "0x0114=0x40"\n' >> "$C/run/lib_k.sh"
(cd "$C" && run/freeze_k.sh freeze > /dev/null); rc=$(runst "$C" k-f4)
[ "$rc" = 7 ] && grep -q 'bif_write: 0x0114=0x40 is not allowed' "$M/log/k-f4.log" && [ ! -f "$M/fake/kregnow-writes" ] && ok "bif_write refuses 0x0114=0x40 (a clear register): rc 7, nothing written" || bad "bif_write allow-list: rc $rc"
world; copytree
printf '\nbif_write x 9 "0x0c04=0x80000"\n' >> "$C/run/lib_k.sh"
(cd "$C" && run/freeze_k.sh freeze > /dev/null); rc=$(runst "$C" k-f4)
[ "$rc" = 7 ] && grep -q 'has bit 19' "$M/log/k-f4.log" && ok "bif_write refuses an INT_STAT value with bit 19: rc 7" || bad "bit 19: rc $rc"
world; copytree
printf '\ndbg_write kregnow 0x0c04=0x1\n' >> "$C/run/lib_k.sh"
(cd "$C" && run/freeze_k.sh freeze > /dev/null); rc=$(runst "$C" k-f4)
[ "$rc" = 7 ] && grep -q 'dbg_write: kregnow is not allowed' "$M/log/k-f4.log" && ok "dbg_write refuses kregnow: rc 7" || bad "dbg_write kregnow: rc $rc"
world; copytree
printf '\ndbg_write render_rgn_arrays 2\n' >> "$C/run/lib_k.sh"
(cd "$C" && run/freeze_k.sh freeze > /dev/null); rc=$(runst "$C" k-f4)
[ "$rc" = 7 ] && grep -q 'render_rgn_arrays 2 is not 1 or 4' "$M/log/k-f4.log" && ok "dbg_write refuses render_rgn_arrays 2: rc 7" || bad "rgn 2: rc $rc"
world; copytree
printf '\nprobe_extra() { [ -e "$D/hold_recovery" ] || { echo "no hold_recovery"; exit 1; }; }\nprobe_extra\n' >> "$C/run/lib_k.sh"
(cd "$C" && run/freeze_k.sh freeze > /dev/null)
rc=$(runst "$C" k-f4)
[ "$rc" = 1 ] && ok "a bare [ -e \"\$D/...\" ] fails against root-only debugfs (rc 1)" || bad "unprivileged access ran: rc $rc"
"$C/run/guard_k.sh" "$C" > "$W/guard-bad.txt" 2>&1 && bad "guard missed the bare access" || { grep -q 'UNPRIVILEGED DEBUGFS ACCESS' "$W/guard-bad.txt" && ok "guard: finds the bare debugfs access"; }
for inj in 'echo 1 | sudo -n tee "$D/kreg"' 'echo 1 | sudo -n tee "$D/kregnow"' 'echo 1 | sudo -n tee "$D/kpoke"' 'ls /sys/kernel/debug/dri/*/sgx' 'until false; do :; done' 'x=$(cat f | tail -1)' \
	'sudo -n tee "$D/reset" || true' 'sudo -n timeout 60 "$T" tri' 'set -f' 'echo > /dev/mem' 'cat "$D/regs"' 'dbg_write alias_skip 1' 'dbg_write kregnow 0x0c04=1' 'echo 4 | sudo -n tee "$D/render_pb_pages"'; do
	copytree; printf '%s\n' "$inj" >> "$C/run/lib_k.sh"
	"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed: $inj" || ok "guard: refuses $inj"
done
copytree; grep -v "^trap '' PIPE HUP" "$P/run/run_stage.sh" > "$C/run/run_stage.sh"
"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed a runner without trap '' PIPE HUP" || ok "guard: refuses a runner that does not ignore PIPE and HUP"
copytree; grep -v 'modinfo -F srcversion' "$P/run/lib_k.sh" > "$C/run/lib_k.sh"
"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed a runner without the srcversion check" || ok "guard: refuses a runner without the srcversion check"
copytree; grep -v 'dbg_write render_rgn_arrays 1' "$P/run/lib_k.sh" > "$C/run/lib_k.sh"
"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed a runner that does not restore the knob" || ok "guard: refuses a runner that does not restore render_rgn_arrays at its exit"
copytree; printf 'm-9|heldout|risky|expectdiff|-|tri --kreg x --keep-going\n' >> "$C/tables/k-f4.txt"
"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed a forbidden table option" || ok "guard: refuses a forbidden table option"
copytree; printf 'm-9|heldout|risky|expectdiff|-|tri --keep-going --kpoke-render 2:par:11=0x1\n' >> "$C/tables/k-f4.txt"
"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed a --kpoke-render outside k-pb" || ok "guard: refuses --kpoke-render outside k-pb"
copytree; printf 'm-9|heldout|risky|expectdiff|-|tri --keep-going --kpoke-render 1:ctx:3=0x1\n' >> "$C/tables/k-pb.txt"
"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed a non-par kpoke" || ok "guard: refuses a kpoke that is not 2:par:INDEX=0xVALUE"
copytree; printf 'm-9|heldout|risky|expectdiff|-|tri --keep-going --geometry 2\n' >> "$C/tables/k-pb.txt"
"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed --geometry 2" || ok "guard: refuses --geometry other than 1"
copytree; printf 'm-9|heldout|risky|expectdiff|-|tri --keep-going --geometry 1\n' >> "$C/tables/k-f4.txt"
"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed --geometry outside k-pb0/k-pb" || ok "guard: refuses --geometry outside k-pb0 and k-pb"
copytree; printf 'm-9|heldout|risky|rgn:2 expectdiff|-|tri --keep-going\n' >> "$C/tables/k-f4.txt"
"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed rgn:2" || ok "guard: refuses a rgn knob that is not 1 or 4"
copytree; printf 'm-9|heldout|risky|bif|-|-\n' >> "$C/tables/k-f4.txt"
"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed the bif knob outside k-bif" || ok "guard: refuses the bif knob outside k-bif"
copytree; printf '%s\n' 'echo 1 | sudo -n timeout -k 3 10 tee "$D/kregnow"' >> "$C/run/lib_k.sh"
"$C/run/guard_k.sh" "$C" > /dev/null 2>&1 && bad "guard missed a second kregnow write" || ok "guard: refuses a second place that writes kregnow"
"$P/run/guard_k.sh" && ok "guard: the real scripts and tables are clean" || bad "guard on the real scripts"

# 4. the driver: dry run (bounded commands, gate, the frozen sha256, the attempt) and numeric knob compare
d=$(K_ATT=attX SGX_DRY_RUN=1 bash "$P/run/k.sh" 2>&1)
fs=$(sha "$P/FROZEN.sha256")
echo "$d" | grep -q 'score_k.py gate k-pb' && echo "$d" | grep -q 'bounded 900 ssh' && echo "$d" | grep -q 'bounded 300 scp' \
	&& echo "$d" | grep -q "run_stage.sh k-f4 $fs attX" && echo "$d" | grep -q "r3kpx-out/attX/k-bif .*/out/attX/k-bif" && echo "$d" | grep -q 'K_FAULTS_PRIOR=0' \
	&& ok "driver dry run: the k-pb gate, bounded ssh/scp, the frozen sha256, one directory an attempt, the per-stage fault limit" || bad "driver dry run"
[ "$(echo "$d" | grep '^#### ' | awk '{print $2}' | tr '\n' ' ')" = "k-f4 k-pb0 k-pb k-bif " ] && ok "driver order: k-f4, k-pb0, k-pb, k-bif (the riskiest stage last)" || bad "driver order: $(echo "$d" | grep '^####')"
num_eq 0x00000000 0 && num_eq 0x00000422 0x422 && num_eq 0x00000001 1 && ! num_eq 0x00000004 1 && ! num_eq abc 0 && ok "numeric knob compare" || bad "num_eq"
bounded 1 sleep 5 2>/dev/null; [ $? = 142 ] && ok "bounded: the alarm ends a stuck command (142)" || bad "bounded"

# 5. the whole driver and the staging against fake ssh / scp / health (the laptop is a directory)
mkdir -p "$W/bringup"
cat > "$W/bringup/health.sh" <<'EOF'
#!/bin/bash
echo "diff: 0 of 2048 pixels"; echo "diff: 0 of 4096 pixels"
echo "hold_recovery=N rtds_keep=N alias_ta3d_ro=N render_pb_pages=0x00000422 render_ctx_flags=0x00000000"
EOF
chmod +x "$W/bringup/health.sh"
export RESGX545_BRINGUP=$W/bringup SGX_LOCAL_ENV=/nonexistent SGX_TARGET_HOST=u@fake SGX_TARGET_SSH_OPTS=
# a copy of the tree whose k.env names the fake tool and regtimeline (the real hashes are R1's binaries)
dtree() { D2T=$W/drv$N; mkdir -p "$D2T"
	cp -R "$P/run" "$P/tables" "$P/score" "$P/predictions" "$P/bins" "$P/gen" "$P/stages.txt" "$P/conditional.txt" "$P/TABLES.md" "$P/TOOL.sha256" "$P/TOOLSRC.sha256" "$D2T/"
	sed -e "s/^TOOL_SHA=.*/TOOL_SHA=$K_TOOL_SHA/" -e "s/^RT_SHA=.*/RT_SHA=$K_RT_SHA/" "$P/run/k.env" > "$D2T/run/k.env"
	# the tool pin of the copy is the fake's: the freeze compares k.env with TOOL.sha256
	printf '%s  /home/jtorra/sgxfive-test-r1\n' "$K_TOOL_SHA" > "$D2T/TOOL.sha256"
	(cd "$D2T" && run/freeze_k.sh freeze > /dev/null); }
fakehome() { # the laptop of this world: tool and regtimeline where the staging looks
	cp "$P/tests/fake_tool.sh" "$M/home/sgxfive-test-r1"; cp "$P/tests/fake_rt.sh" "$M/home/regtimeline"; }
drvenv() { echo "$(envw) K_OUT=$M/home/r3kpx-out FAKE_P=$P FAKE_HOME=$M/home SGXFIVE_TEST=$M/home/sgxfive-test-r1 SGXFIVE_REGTIMELINE=$M/home/regtimeline SGXFIVE_PROBE_BINS=$M/home/r3kpx-stage"; }
world; dtree; fakehome
out=$(env $(drvenv) bash "$D2T/run/stage_k.sh" 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'staged: runner, tables, programs' && ok "staging: copies, compares every file with the Mac's, checks the tool and regtimeline hashes" || { bad "staging: rc $rc"; echo "$out" | tail -5 | sed 's/^/     /'; }
world; fakehome; out=$(env $(drvenv) bash "$P/run/stage_k.sh" 2>&1); rc=$?
[ $rc != 0 ] && echo "$out" | grep -q "the laptop's tool is not R1's" && ok "staging refuses a laptop whose tool is not R1's build" || bad "staging with a foreign tool: rc $rc"
# the full session in the mock: every stage, the gate, the scorer after each stage, health between, the verdict
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
out=$(env $(drvenv) K_ATT=full FAKE_BIF=clr bash "$D2T/run/k.sh" 2>&1); rc=$?
nst=$(echo "$out" | grep -c '^stage k-.* done, health ok, render_rgn_arrays 0x00000001')
[ $rc = 0 ] && [ "$nst" = 4 ] && echo "$out" | grep -q '^R3K-pixel done:' && ok "driver, whole session in the mock: 4 stages done with health and the knob read back as 1" \
	|| { bad "driver full run: rc $rc, $nst stages"; echo "$out" | tail -8 | sed 's/^/     /'; }
v=$("$PY" "$D2T/score/score_k.py" verdict "$D2T/out/full" 2>&1)
case "$v" in *"Q140: k-f4: 8 of 8"*"Q285: H-OLD"*"Q003: H-CLR"*) ok "  the verdict of the kept session: Q140 8 of 8, Q285 H-OLD, Q003 H-CLR" ;; *) bad "  verdict: $v" ;; esac
[ -f "$D2T/out/full/score-k-bif.txt" ] && grep -q SUMMARY "$D2T/out/full/score-k-bif.txt" && ok "  the scorer ran after each stage (one SUMMARY kept)" || bad "  no score file"
# a stage that leaves the knob at another value stops the session (rc 42) with the command to restore it
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
out=$(env $(drvenv) K_ATT=leak FAKE_KNOB_LEAK=1 bash "$D2T/run/k.sh" --only k-f4 2>&1); rc=$?
[ $rc = 42 ] && echo "$out" | grep -q 'render_rgn_arrays is 0x00000004 after k-f4' && ok "the knob read as 4 after a stage stops the driver (rc 42)" || { bad "knob after stage: rc $rc"; echo "$out" | tail -3 | sed 's/^/     /'; }
# a closed gate skips k-pb cleanly and the session goes on with k-bif
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
mkdir -p "$D2T/out/prior"; "$PY" -c "
import sys; sys.path.insert(0, '$P/tests'); import worlds as W; W.pb0_world('$D2T/out/prior/k-pb0', 'p0empty')"
out=$(env $(drvenv) K_ATT=gate1 bash "$D2T/run/k.sh" --only k-pb k-bif 2>&1); rc=$?
[ $rc = 0 ] && echo "$out" | grep -q 'SKIPPED: k-pb' && echo "$out" | grep -q 'stage k-bif done' && echo "$out" | grep -q 'R3K-pixel done (skipped: k-pb)' && ok "a failed k-pb0 control closes the gate: k-pb is skipped cleanly (rc 0) and k-bif runs" || { bad "gate skip: rc $rc"; echo "$out" | tail -6 | sed 's/^/     /'; }
# a stage stop prints the knob and how to continue
world; dtree; fakehome
env $(drvenv) bash "$D2T/run/stage_k.sh" > /dev/null 2>&1
out=$(env $(drvenv) K_ATT=stop1 FAKE_RULES='--width 288 --height 144 --max-width 288|fatal' bash "$D2T/run/k.sh" 2>&1); rc=$?
[ $rc = 3 ] && echo "$out" | grep -q 'knobs after the stop' && echo "$out" | grep -q 'run/k.sh --from k-f4' && ok "a fatal kernel message stops the driver (rc 3), prints the knobs and how to continue" || { bad "stage stop: rc $rc"; echo "$out" | tail -4 | sed 's/^/     /'; }
out=$(env $(drvenv) bash "$D2T/run/stage_k.sh" 2>&1); rc=$?
[ $rc = 0 ] && ok "restaging after a stop works (nothing on the laptop is a gate)" || bad "restage: rc $rc"
echo "work dir (kept for inspection): $W"
exit $fail
