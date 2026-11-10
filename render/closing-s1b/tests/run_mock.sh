#!/bin/bash
# tests/run_mock.sh (S1b): every table runs end to end through run_stage.sh against a fake tool, a plain-directory
# debugfs and shims for sudo/dmesg/timeout; checks job counts, markers, kept DUMPS (a fake that writes param,
# tadata, depth and words files: the runner must keep them), rc/class/hypothesis columns, knob restore, the stop
# rules, the table rules (hypothesis rows last, --keep-going on multi-render tri jobs), the staged-tool check, the
# guard (including unprivileged debugfs access), and the scorers on fake data (cannot tell, never a verdict).
# Needs a current freeze (run/freeze_s1.sh freeze): the runner compares its table and programs with FROZEN.sha256.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
W=$(mktemp -d)
mkdir -p "$W/dbg" "$W/stage" "$W/out"
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh" SGXFIVE_DEBUGFS="$W/dbg" KMSG="$W/kmsg"
export SRCV_PATH="$W/srcv" SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh" SGXFIVE_PROBE_BINS="$W/stage"
export RESET_WAIT=0 HEALTH_WAIT=0 FAKE_LOG="$W/fake.log" TOOL_SHA_FILE="$W/TOOL.sha256" PYTHONDONTWRITEBYTECODE=1
shasum -a 256 "$P/tests/fake_tool.sh" > "$W/TOOL.sha256"
echo MOCKSRCV > "$W/srcv"; : > "$W/kmsg"
for f in reset render_pb_pages alias_skip regs buf09 render_param render_tadata; do : > "$W/dbg/$f"; done
echo 0x00000422 > "$W/dbg/render_pb_pages"; echo 0x00000000 > "$W/dbg/alias_skip"
cp "$P"/bins/*.bin "$W/stage/"
. "$P/run/lib_check.sh"
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
runst() { KEEP="$W/out/$1$2" bash "$P/run/run_stage.sh" "$1" > "$W/out/$1$2.log" 2>&1; echo $?; }
for t in "$P"/tables/*.txt; do
	name=$(basename "$t" .txt)
	n=$(grep -vc '^#' "$t")
	rc=$(runst "$name" "")
	got=$(grep -c '^== ' "$W/out/$name.log"); kept=$(wc -l < "$W/out/$name/raw.sha256" | tr -d ' ')
	pb=$(cat "$W/dbg/render_pb_pages"); as=$(cat "$W/dbg/alias_skip")
	nd=$(grep -v '^#' "$t" | grep -c -- '--dump-render'); kd=$(ls "$W/out/$name" | grep -c 'param\.bin\.gz')
	ne=$(grep -v '^#' "$t" | grep -c -- '--depth-dump'); ke=$(ls "$W/out/$name" | grep -c 'depth\.1\.bin\.gz')
	nc=$(( $(wc -l < "$W/out/$name/cases.tsv") - 1 ))
	cols=$(awk -F'\t' 'NR>1 && (NF != 11 || $9 == "" || $10 == "" || $11 == "") {x++} END{print x+0}' "$W/out/$name/cases.tsv")
	[ "$rc" = 0 ] && [ "$got" = "$n" ] && [ "$kept" -ge "$n" ] && [ "$pb" = 0x00000422 ] && [ "$as" = 0x00000000 ] \
		&& [ "$kd" = "$nd" ] && [ "$ke" = "$ne" ] && [ "$nc" = "$n" ] && [ "$cols" = 0 ] \
		&& ok "$name: $got of $n jobs, $kept kept files, $kd param and $ke depth dumps kept, $nc rows with rc/class/hypo, knobs back" \
		|| bad "$name: rc $rc, $got of $n jobs, kept $kept, param dumps $kd of $nd, depth dumps $ke of $ne, cases rows $nc (bad cols $cols), pb $pb alias_skip $as"
done
echo "case markers: $(grep -c 'resgx545 case' "$W/kmsg"), knob markers: $(grep -c 'resgx545 s1b readback' "$W/kmsg")"
[ "$(grep -c 'no reset before (noreset)' "$W/out/g-e5.log")" = 3 ] && ok "g-e5: the three a8 runs without a reset" || bad "noreset count"
# stop rules
check() { # NAME EXPECTED_RC TABLE ENV...
	nm=$1; want=$2; tb=$3; shift 3
	rc=$(env "$@" bash -c "KEEP=$W/out/x$nm bash $P/run/run_stage.sh $tb > $W/out/x$nm.log 2>&1; echo \$?")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || bad "$nm: rc $rc, wanted $want"
}
check unexpected-hang 4 g-e1 FAKE_HANG=vertices
check fatal-kernel 3 g-e3 FAKE_FATAL=e3i-w3
check freeze 6 g-e4w FAKE_TIMEOUT=index-width
check unexplained-failure 4 g-e5 FAKE_DIFF=vtx-coords        # rc 1 with a diff line but no expectdiff: a failure
check expectdiff-with-diff-line 0 p-b2 FAKE_DIFF=0,0,114688  # d-L448: a held-out geometry, expectdiff
check expectdiff-needs-diff-line 4 p-b2 FAKE_NODIFF=0,0,114688
check control-without-expectdiff 4 p-b2 FAKE_DIFF=0,0,131072,0,0,131072   # d-ctl (and d-tall...) must pass rc 0
# hypothesis groups: measured, at most MAX events a group, then the group is skipped
check hypo-fault-e4w 0 g-e4w FAKE_FAULT=index-width
L=$W/out/xhypo-fault-e4w.log; C=$W/out/xhypo-fault-e4w/cases.tsv
grep -q "fault 1 of at most 1 in group ix32-n" "$L" && grep -q "== ix32-n-r2 skipped: group ix32-n" "$L" \
	&& grep -q "== ix32-25-r1 " "$L" && ok "hypo group gate trips: one fault, the group's replicate skipped, the next group ran" \
	|| bad "hypo group gate log"
grep -q "== ix-25 skipped: the stage reached 3 hang/fault events" "$L" \
	&& [ "$(awk -F'\t' '$10 == "fault"' "$C" | wc -l | tr -d ' ')" = 3 ] \
	&& ok "stage gate trips: after 3 hang/fault events the remaining hypothesis rows are skipped" || bad "stage gate"
awk -F'\t' '$1 == "ix32-25-r1" && $10 == "fault" && $11 == "ix32-25" {f=1} END{exit !f}' "$C" \
	&& awk -F'\t' '$1 == "ix-25" && $9 == "-" && $10 == "skipped" {f=1} END{exit !f}' "$C" \
	&& ok "cases.tsv records class fault, the group, and the skipped rows (rc -, class skipped)" || bad "cases.tsv hypo/skipped rows"
# every hypothesis group's limit is below its row count (a group of one row: 1)
for t in "$P"/tables/*.txt; do
	awk -F'|' '!/^#/ && NF >= 7 { n = split($5, k, " "); for (i = 1; i <= n; i++) if (k[i] ~ /^hypo:/) { split(k[i], p, ":"); rows[p[2]]++; lim[p[2]] = p[3] } }
		END { for (q in rows) if (!(lim[q] + 0 < rows[q] || (rows[q] == 1 && lim[q] == 1))) { print q, lim[q], rows[q]; bad = 1 } exit bad }' "$t" \
		|| bad "$(basename "$t"): a hypothesis limit not below its row count"
done
ok "hypothesis limits below row counts checked in every table"
# preflight: the kmsg marker must arrive (KMSG to nowhere: the shim's dmesg shows nothing)
rc=$(KMSG=/dev/null KEEP=$W/out/xm bash "$P/run/run_stage.sh" p-f > "$W/out/xm.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "kmsg marker did not arrive" "$W/out/xm.log" && ok "preflight refuses when its kmsg marker does not arrive" || bad "kmsg marker rc $rc"
check hypo-fault-pd 0 p-d FAKE_FAULT=scratch-pages\ 1         # 16 to 19 pages: HB-end / the control's fault, measured
check unexpected-fault-pd 4 p-d FAKE_FAULT=l0e2               # d-ok-64, a plain control, faulting is not a hypothesis
check hypo-fault-pf 0 p-f 'FAKE_FAULT=6000$'                  # f-ctl0 (its command ends there): a hypothesis row
check unexpected-fault-pf 4 p-f FAKE_FAULT=1024                # f-dpm-0, the plain control, faulting stops the stage
# the table rules and the staged tool (a copy of the runner and tables in a scratch tree)
mkdir -p "$W/tree/run" "$W/tree/tables"; cp "$P"/run/*.sh "$W/tree/run/"; cp "$P/FROZEN.sha256" "$W/tree/"
grep -v '^ix-c|' "$P/tables/g-e4w.txt" > "$W/tree/tables/g-e4w.txt"; grep '^ix-c|' "$P/tables/g-e4w.txt" >> "$W/tree/tables/g-e4w.txt"
rc=$(KEEP=$W/out/xo bash "$W/tree/run/run_stage.sh" g-e4w > "$W/out/xo.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "hypothesis rows must be last" "$W/out/xo.log" && ok "a plain row after a hypothesis row is refused" || bad "order rule rc $rc"
sed 's/ --keep-going//' "$P/tables/p-f.txt" > "$W/tree/tables/p-f.txt"
rc=$(KEEP=$W/out/xk bash "$W/tree/run/run_stage.sh" p-f > "$W/out/xk.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "without --keep-going" "$W/out/xk.log" && ok "a multi-render tri job without --keep-going is refused" || bad "keep-going rule rc $rc"
echo "0000 x" > "$W/TOOL.bad"
rc=$(TOOL_SHA_FILE=$W/TOOL.bad KEEP=$W/out/xt bash "$P/run/run_stage.sh" p-f > "$W/out/xt.log" 2>&1; echo $?)
[ "$rc" = 1 ] && grep -q "not the staged one" "$W/out/xt.log" && ok "a tool that is not the staged binary is refused" || bad "tool sha rc $rc"
# health: the first failed recovery stops (the fake tool fails the plain triangle)
printf '#!/bin/sh\necho "job: failed"; exit 1\n' > "$W/badtool.sh"; chmod +x "$W/badtool.sh"; shasum -a 256 "$W/badtool.sh" > "$W/TOOL.badtool"
rc=$(SGXFIVE_TEST="$W/badtool.sh" TOOL_SHA_FILE="$W/TOOL.badtool" bash -c "KEEP=$W/out/xb bash $P/run/run_stage.sh g-e4w > $W/out/xb.log 2>&1; echo \$?")
[ "$rc" = 5 ] && grep -q "first failed recovery" "$W/out/xb.log" && ok "the first failed health recovery stops (rc 5)" || bad "health stop rc $rc"
num_eq 0x00000000 0 && num_eq 0x0 0 && num_eq 0x00000422 0x422 && ! num_eq 0x6 0 && ! num_eq abc 0 \
	&& ok "numeric knob compare (the kernel prints 0x%08x)" || bad "num_eq"
# the scorers on the fake data: empty or meaningless data must give NODATA rows and "cannot tell", never a verdict
PY=${PY:-$HOME/src/scratch/resgx545/closing/pixel-faults/.venv/bin/python}
for t in "$P"/tables/*.txt; do
	name=$(basename "$t" .txt)
	s=$("$PY" -c "import sys; sys.path.insert(0,'$P/score'); import score_s1; print(score_s1.run_stage('$name', '$W/out/$name'))" 2>&1 | grep '^SUMMARY:')
	case "$s" in *"cannot tell"*|*"METHOD BROKEN"*) ok "scorer $name on fake data: ${s:0:70}" ;; *) bad "scorer $name gave: ${s:-no SUMMARY}" ;; esac
done
"$P/run/guard_s1.sh" > "$W/out/guard.log" 2>&1 && ok "guard" || { bad "guard"; cat "$W/out/guard.log"; }
cp "$P/run/guard_s1.sh" "$W/tree/run/"; cp "$P"/tables/*.txt "$W/tree/tables/"
printf '\tcat "$D/regs" > "$W/regs.txt"\n' >> "$W/tree/run/lib_s1.sh"
"$W/tree/run/guard_s1.sh" > "$W/out/guard2.log" 2>&1; g=$?
[ $g = 1 ] && grep -q "UNPRIVILEGED DEBUGFS ACCESS" "$W/out/guard2.log" && ok "the guard refuses an unprivileged debugfs read" || bad "guard sudo rule"
grep -nE '(^|[;&|[:space:]])(while|until)[[:space:]]' "$P"/run/*.sh | grep -v '^[^:]*:[0-9]*:[[:space:]]*#' | grep -v 'guard_s1.sh' && bad "a loop that waits"
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/s1.sh" > "$W/out/dry.log" 2>&1; d=$?
[ $d = 0 ] && [ "$(grep -c 'bounded' "$W/out/dry.log")" -ge "$(( 3 * $(wc -l < "$P/stages.txt") ))" ] \
	&& ok "s1.sh dry run: every ssh/scp/health bounded by an alarm" || bad "s1.sh dry run status $d"
# staging: the deploy inputs of --src must hash to the frozen TOOLSRC.sha256 (dry run: nothing leaves the Mac)
WT=${TOOL_SRC:-$HOME/src/resgx545/.claude/worktrees/agent-aed0242cfe8ab4e23}
grep -q '  TOOLSRC.sha256$' "$P/FROZEN.sha256" && ok "the freeze covers TOOLSRC.sha256" || bad "TOOLSRC.sha256 not frozen"
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/stage_s1.sh" --src "$WT" > "$W/out/st1.log" 2>&1; s=$?
[ $s = 0 ] && grep -q "deploy inputs match the freeze" "$W/out/st1.log" && ok "stage: the frozen source stages" || bad "stage frozen src status $s"
mkdir -p "$W/src"; cp -R "$WT/userspace" "$WT/include" "$W/src/"; mkdir -p "$W/src/tools/bringup"
cp "$WT/tools/gen_tri_progs.py" "$W/src/tools/"; cp "$WT/tools/bringup/deploy-tool.sh" "$W/src/tools/bringup/"
printf '/* changed */\n' >> "$W/src/userspace/libsgxfive/src/render.c"
SGX_DRY_RUN=1 SGX_LOCAL_ENV=/dev/null bash "$P/run/stage_s1.sh" --src "$W/src" > "$W/out/st2.log" 2>&1; s=$?
[ $s = 1 ] && grep -q "deploy inputs differ from the freeze" "$W/out/st2.log" && grep -q "render.c" "$W/out/st2.log" \
	&& ok "stage: a changed source refuses to stage (and names the file)" || bad "stage changed src status $s"
echo "work dir (kept for inspection): $W"
exit $fail
