#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# p1141/tex isp-b-depth (Q200): the depth plane per tile corner: classes with exact, non-dyadic and tie steps
# Draft, written without laptop access; nothing here has run on hardware. Run on the laptop after
# stage-p1141tex.sh has put the programs in ~/sgxprobes-stage-1141tex; the tool is ~/sgxfive-test-1138b
# (SGXFIVE_TEST overrides). Raw outputs are KEPT: every job's whole tool output gzipped (mtime 0) in
# $KEEP/NAME.txt.gz with its raw size and sha256 printed ("kept ..."), every file a job dumps (depth, render
# parameter buffer, TA data) as $KEEP/NAME.FILE.gz, the case table in $KEEP/cases.tsv and the kernel log of
# the run in $KEEP/journal-k.txt.gz; the tool's standard error is kept apart (NAME.err.gz). A fill prints the
# sha256 of its 2048 pixels (raster order, 8 hex digits comma joined); nothing is judged here:
# recompute/recompute_p1141tex.py recomputes everything from the kept dumps. A marker line goes to
# /dev/kmsg before each job. No clock-gate register and no register at all is written by this script (no
# kreg, no kregnow, no /dev/mem write; --regs reads); the only writes are debugfs reset and /dev/kmsg.
# Root: sudo -n. Three failed recoveries of the health triangle stop the script.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1138b}
S=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage-1141tex}
KEEP=${KEEP:-$HOME/p1141tex-dumps/isp-b-depth}
EVERY=0
ONLY=${ONLY:-}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build the 11.38 tool (deploy1138b.sh) on the laptop first"; exit 1; }
[ -n "$D" ] || { echo "no sgx debugfs directory (debug option off?)"; exit 1; }
mkdir -p "$KEEP"
START=$(date +%s)
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$SRCV_FILE"
echo "## loaded module"; SRCV_LOADED=$(sudo -n cat /sys/module/gma500_gfx/srcversion); echo "$SRCV_LOADED"
[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
echo "## tool"; sha256sum "$T"
echo "## clock"; date
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep "${RESET_WAIT:-3}"; }
mark() { printf "resgx545 p1141tex case %s %s\n" "$1" "$RUN" | sudo -n tee /dev/kmsg >/dev/null; }
RUN=$(date +%s)-$$
W=$(mktemp -d)
journal() { sudo -n journalctl -k --since "@$START" --no-pager 2>&1 | gzip -n -6 > "$KEEP/journal-k.txt.gz"
	echo "## journalctl -k: $(gzip -dc "$KEEP/journal-k.txt.gz" | wc -l | tr -d ' ') lines, $(gzip -dc "$KEEP/journal-k.txt.gz" | grep -ci 'sgxfive\|bif fault\|recovery' | tr -d ' ') naming sgxfive, a BIF fault or a recovery"; }
trap 'journal; rm -rf "$W"' EXIT
keep() { # NAME FILE: gzip the whole raw output, print its sizes and the raw sha256
	raw=$(wc -c < "$2" | tr -d ' ')
	sha=$(sha256sum "$2" | cut -d' ' -f1)
	gzip -n -6 -c "$2" > "$KEEP/$1.txt.gz"
	echo "  kept $1: $raw bytes raw, $(wc -c < "$KEEP/$1.txt.gz" | tr -d ' ') gz, raw sha256 $sha"
}
keepbin() { # NAME FILE: the same for a binary dump
	raw=$(wc -c < "$2" | tr -d ' ')
	sha=$(sha256sum "$2" | cut -d' ' -f1)
	gzip -n -6 -c "$2" > "$KEEP/$1.gz"
	echo "  kept $1: $raw bytes raw, $(wc -c < "$KEEP/$1.gz" | tr -d ' ') gz, raw sha256 $sha"
}
BAD=0
health() { # a plain triangle must still draw exactly; three failed recoveries stop the script
	sleep "${HEALTH_WAIT:-3}"
	if sudo -n timeout 60 "$T" tri 2>&1 </dev/null | grep -q "^diff: 0 of 4096"; then BAD=0; echo "  health: ok"; return 0; fi
	reset_gpu; sleep "${HEALTH_WAIT:-3}"
	if sudo -n timeout 60 "$T" tri 2>&1 </dev/null | grep -q "^diff: 0 of 4096"; then BAD=0; echo "  health: ok after a reset"; return 0; fi
	sleep "${HEALTH_WAIT:-3}"
	if sudo -n timeout 60 "$T" tri 2>&1 </dev/null | grep -q "^diff: 0 of 4096"; then BAD=0; echo "  health: recovered on the retry"; return 0; fi
	BAD=$((BAD + 1)); echo "  health: the plain triangle does not draw ($BAD)"
	[ "$BAD" -ge 3 ] && { echo "## abort: the GPU did not recover three times"; exit 1; }
	return 1
}
health
PY=$(cat <<'PYEOF'
import collections, hashlib, re, sys
want = sys.argv[1] if len(sys.argv) > 1 else "-"
expect = int(sys.argv[2]) if len(sys.argv) > 2 else 2048
c = collections.Counter()
vals = []
for line in sys.stdin:
    m = re.search(r"row (\d+): (.*)$", line)
    if not m:
        continue
    for v in m.group(2).split():
        v = v[2:] if v.startswith("0x") else v
        vals.append(v.rjust(8, "0"))
        c[v] += 1
sha = hashlib.sha256(",".join(vals).encode()).hexdigest()
top = " ".join("%s x%d" % kv for kv in c.most_common(3))
res = "" if want == "-" else ("  MATCH" if want == sha else "  MISMATCH (declared %s)" % want[:16])
print("  pixels %d: %d distinct; commonest %s" % (len(vals), len(c), top))
print("  pix sha256 %s%s" % (sha, res))
if len(vals) != expect:
    print("  PIXELS %d, not %d" % (len(vals), expect))
PYEOF
)


job() { # NAME KIND BIN PRED [OPTION...]: one job, kept whole; KIND probe (a 64 x 32 fill) or tri (a render)
	name=$1; kind=$2; bin=$3; pred=$4; shift 4
	if [ -n "$ONLY" ] && [ "$ONLY" != "$name" ]; then return 0; fi
	[ "$kind" = probe ] && { [ -f "$S/$bin" ] || { echo "no $S/$bin: run stage-p1141tex.sh and copy"; exit 1; }; }
	echo "== $name ($kind $bin)"
	mark "$name"
	JD="$W/$name.d"; mkdir -p "$JD"
	args=()
	for a in "$@"; do a=${a//@D@/$JD}; args+=("$a"); done
	if [ "$kind" = probe ]; then
		sudo -n timeout 120 "$T" probe --temps 32 --coords --pixels ${args[@]+"${args[@]}"} "$S/$bin" > "$W/$name.out" 2> "$W/$name.err" </dev/null
	else
		sudo -n timeout 300 "$T" tri ${args[@]+"${args[@]}"} > "$W/$name.out" 2> "$W/$name.err" </dev/null
	fi
	rc=$?
	cat "$W/$name.err" "$W/$name.out" > "$W/$name.out.chk"
	echo "  rc $rc $(grep -E 'failed|FAILED|faulted|hung' "$W/$name.out.chk" | head -1 | cut -c1-100)"
	if [ "$kind" = probe ]; then
		python3 -c "$PY" "$pred" < "$W/$name.out" | tee "$W/$name.red"
	else
		grep -E "^diff|^tri [0-9]+x[0-9]+ #1: [0-9]+ tri|^reg 0x04|^tri:" "$W/$name.out" | cut -c1-140 | head -12
	fi
	keep "$name" "$W/$name.out"
	[ -s "$W/$name.err" ] && keep "$name.err" "$W/$name.err"
	for f in "$JD"/*; do [ -f "$f" ] && keepbin "$name.$(basename "$f")" "$f"; done
	if [ "$EVERY" = 1 ] || grep -qE "failed|faulted|hung" "$W/$name.out.chk" || [ "$rc" -ge 2 ]; then
		reset_gpu; health </dev/null || true
	fi
	rm -rf "$JD" "$W/$name.out" "$W/$name.err" "$W/$name.out.chk" "$W/$name.red"
}

printf 'name\tkind\tbin\tset\trisk\toptions\n' > "$KEEP/cases.tsv"
CASES=$(cat <<'TABLE'
dp-ax-b0	tri	-	-	control	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,131072,0,0,131072 --tri-z 0.5,0.5625,0.5 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-ay-b0	tri	-	-	control	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,131072,0,0,131072 --tri-z 0.5,0.5,0.5625 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-bx-b0	tri	-	-	heldout	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,102400,0,0,102400 --tri-z 0.5,0.5625,0.5 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-by-b0	tri	-	-	heldout	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,102400,0,0,102400 --tri-z 0.5,0.5,0.5625 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-cx-b0	tri	-	-	heldout	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,131072,0,0,131072 --tri-z 0.5,0.500002384185791,0.5 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-cy-b0	tri	-	-	heldout	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,131072,0,0,131072 --tri-z 0.5,0.5,0.500004768371582 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-ax-b1	tri	-	-	control	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,131072,0,0,131072 --tri-z 0.25,0.3125,0.25 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-ay-b1	tri	-	-	control	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,131072,0,0,131072 --tri-z 0.25,0.25,0.3125 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-bx-b1	tri	-	-	heldout	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,102400,0,0,102400 --tri-z 0.25,0.3125,0.25 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-by-b1	tri	-	-	heldout	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,102400,0,0,102400 --tri-z 0.25,0.25,0.3125 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-cx-b1	tri	-	-	heldout	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,131072,0,0,131072 --tri-z 0.25,0.2500011920928955,0.25 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-cy-b1	tri	-	-	heldout	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,131072,0,0,131072 --tri-z 0.25,0.25,0.250002384185791 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-ax-b2	tri	-	-	control	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,131072,0,0,131072 --tri-z 0.125,0.1875,0.125 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-ay-b2	tri	-	-	control	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,131072,0,0,131072 --tri-z 0.125,0.125,0.1875 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-bx-b2	tri	-	-	heldout	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,102400,0,0,102400 --tri-z 0.125,0.1875,0.125 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-by-b2	tri	-	-	heldout	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,102400,0,0,102400 --tri-z 0.125,0.125,0.1875 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-cx-b2	tri	-	-	heldout	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,131072,0,0,131072 --tri-z 0.125,0.12500059604644775,0.125 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-cy-b2	tri	-	-	heldout	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,131072,0,0,131072 --tri-z 0.125,0.125,0.1250011920928955 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-bx-b0-p1	tri	-	-	heldout	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 102400,0,0,102400,0,0 --tri-z 0.5625,0.5,0.5 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-bx-b0-p2	tri	-	-	heldout	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,102400,0,0,102400,0 --tri-z 0.5,0.5,0.5625 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
dp-bx-b0-r	tri	-	-	heldout	safe	--keep-overflow --wait-ms 20000 --width 256 --height 128 --tri-v 0,0,0,102400,102400,0 --tri-z 0.5,0.5,0.5625 --depth --depth-ctl 0x17103c --depth-fill 0xdeadbeef --depth-dump @D@ --depth-pages 48 --poke blk:1=0x00400200 --pixels
TABLE
)
while IFS=$'\t' read -r name kind bin pred st risk opts; do
	[ "$opts" = "-" ] && opts=""
	opts=${opts//@S@/$S}
	printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$kind" "$bin" "$st" "$risk" "$opts" >> "$KEEP/cases.tsv"
	# shellcheck disable=SC2086
	job "$name" "$kind" "$bin" "$pred" $opts
done < <(echo "$CASES")
health </dev/null || true
echo "## end"
