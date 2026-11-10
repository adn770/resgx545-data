#!/bin/bash
# tests/run_mock.sh: every table runs end to end through run_stage.sh against a fake tool, a plain-directory
# debugfs and shims for sudo/dmesg/timeout; checks job counts, markers, kept DUMPS (a fake that writes param,
# tadata, depth and words files: the runner must keep them), rc/class columns, knob restore, the stop rules.
# Needs a current freeze (run/freeze_s1.sh freeze): the runner compares its table and programs with FROZEN.sha256.
set -u
P=$(cd "$(dirname "$0")/.." && pwd)
W=$(mktemp -d)
mkdir -p "$W/dbg" "$W/stage" "$W/out"
export PATH="$P/tests/shims:$PATH" SGXFIVE_TEST="$P/tests/fake_tool.sh" SGXFIVE_DEBUGFS="$W/dbg" KMSG="$W/kmsg"
export SRCV_PATH="$W/srcv" SGXFIVE_REGTIMELINE="$P/tests/fake_rt.sh" SGXFIVE_PROBE_BINS="$W/stage"
export RESET_WAIT=0 HEALTH_WAIT=0 FAKE_LOG="$W/fake.log"
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
	# dumps: every job that asks for --dump-render, --depth-dump or --words must have its files kept
	nd=$(grep -v '^#' "$t" | grep -c -- '--dump-render'); kd=$(ls "$W/out/$name" | grep -c 'param\.bin\.gz')
	ne=$(grep -v '^#' "$t" | grep -c -- '--depth-dump'); ke=$(ls "$W/out/$name" | grep -c 'depth\.1\.bin\.gz')
	nc=$(( $(wc -l < "$W/out/$name/cases.tsv") - 1 ))
	[ "$rc" = 0 ] && [ "$got" = "$n" ] && [ "$kept" -ge "$n" ] && [ "$pb" = 0x00000422 ] && [ "$as" = 0x00000000 ] \
		&& [ "$kd" = "$nd" ] && [ "$ke" = "$ne" ] && [ "$nc" = "$n" ] \
		&& ok "$name: $got of $n jobs, $kept kept files, $kd param and $ke depth dumps kept, $nc rc rows, knobs back" \
		|| bad "$name: rc $rc, $got of $n jobs, kept $kept, param dumps $kd of $nd, depth dumps $ke of $ne, cases rows $nc, pb $pb alias_skip $as"
done
echo "case markers: $(grep -c 'resgx545 case' "$W/kmsg"), knob markers: $(grep -c 'resgx545 s1 readback' "$W/kmsg")"
awk -F'\t' 'NR>1 && $9 == "" {x++} END{exit x>0}' "$W/out/g-e1/cases.tsv" && ok "cases.tsv has an rc on every row" || bad "cases.tsv rc"
# stop rules
check() { # NAME EXPECTED_RC TABLE ENV...
	nm=$1; want=$2; tb=$3; shift 3
	rc=$(env "$@" bash -c "KEEP=$W/out/x$nm bash $P/run/run_stage.sh $tb > $W/out/x$nm.log 2>&1; echo \$?")
	[ "$rc" = "$want" ] && ok "$nm (rc $rc)" || bad "$nm: rc $rc, wanted $want"
}
check unexpected-hang 4 g-e1 FAKE_HANG=vertices
check fatal-kernel 3 g-e3 FAKE_FATAL=e3w-w2
check freeze 6 g-e4 FAKE_TIMEOUT=0x01000000
check unexplained-failure 4 g-e5 FAKE_DIFF=vtx-coords        # rc 1 with a diff line but no expectdiff: a failure
check expectdiff-needs-diff-line 4 g-e2a FAKE_NODIFF=geometry   # rc 1 WITHOUT a diff line is a failure
check expectdiff-with-diff-line 0 g-e2a FAKE_DIFF=geometry
# hypothesis groups: E4 flips may hang or fault; measured, at most two events a group, then the group is skipped
check hypo-hang-e4 0 g-e4 FAKE_HANG=0x01000000
check hypo-fault-e4 0 g-e4 FAKE_FAULT=0x01000000
grep -q "hang 2 of at most 2 in group ix-24" "$W/out/xhypo-hang-e4.log" && grep -q "ix-25-r1" "$W/out/xhypo-hang-e4.log" \
	&& ok "hypo group: two hangs measured, the next word still ran" || bad "hypo group log"
check hypo-fault-pd 0 p-d FAKE_FAULT=L3e3__0                    # HX: a fault at 64 pages is measured, not a stop
check unexpected-fault-pd 4 p-d FAKE_FAULT=tw128x32               # the control faulting is not a hypothesis
# health: the first failed recovery stops (the fake tool fails the plain triangle)
printf '#!/bin/sh\necho "job: failed"; exit 1\n' > "$W/badtool.sh"; chmod +x "$W/badtool.sh"
rc=$(SGXFIVE_TEST="$W/badtool.sh" bash -c "KEEP=$W/out/xb bash $P/run/run_stage.sh g-e4 > $W/out/xb.log 2>&1; echo \$?")
[ "$rc" = 5 ] && grep -q "first failed recovery" "$W/out/xb.log" && ok "the first failed health recovery stops (rc 5)" || bad "health stop rc $rc"
# numeric compare of knob values as the kernel prints them (the runner's read-back check uses the same arithmetic)
num_eq 0x00000000 0 && num_eq 0x0 0 && num_eq 0x00000422 0x422 && ! num_eq 0x6 0 && ! num_eq abc 0 \
	&& ok "numeric knob compare (the kernel prints 0x%08x)" || bad "num_eq"
# the scorers on the fake data: empty or meaningless data must give NODATA rows and "cannot tell", never a verdict
PY=${PY:-$P/../pixel-faults/.venv/bin/python}
for t in "$P"/tables/*.txt; do
	name=$(basename "$t" .txt)
	s=$("$PY" -c "import sys; sys.path.insert(0,'$P/score'); import score_s1; print(score_s1.run_stage('$name', '$W/out/$name'))" 2>&1 | grep '^SUMMARY:')
	case "$s" in *"cannot tell"*|*"METHOD BROKEN"*) ok "scorer $name on empty/fake data: ${s:0:70}" ;; *) bad "scorer $name gave: ${s:-no SUMMARY}" ;; esac
done
"$P/run/guard_s1.sh" && ok "guard" || bad "guard"
grep -nE '(^|[;&|[:space:]])(while|until)[[:space:]]' "$P"/run/*.sh | grep -v '^[^:]*:[0-9]*:[[:space:]]*#' | grep -v 'guard_s1.sh' && bad "a loop that waits"
echo "work dir (kept for inspection): $W"
exit $fail
