# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# lib1135.sh: what every 11.35 script shares (sourced, never run). The script sets SCRIPT_NAME
# first. Nothing here writes a register: debugfs kreg and kregnow are never used, so no clock-gate
# register can be written by any script of this batch. Writes: debugfs kpoke (cleared after each
# job), tadata_fill, render_keep (armed once, cleared), reset, hold_recovery (put back),
# render_pb_pages (put back). Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1126}
S=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage-1135}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
KEEP=${KEEP:-$HOME/p1135-dumps/$SCRIPT_NAME}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: the 11.26 tool is ~/sgxfive-test-1126 (deploy1126.sh)"; exit 1; }
[ -n "$D" ] || { echo "no sgx debugfs directory (debug option off?)"; exit 1; }
mkdir -p "$KEEP"
START=$(date +%s)
preflight() {
	echo "## script $SCRIPT_NAME"; echo "## uname"; uname -r
	echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
	echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$SRCV_FILE"
	echo "## loaded module"; SRCV_LOADED=$(sudo -n cat /sys/module/gma500_gfx/srcversion); echo "$SRCV_LOADED"
	[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
	echo "## tool"; sha256sum "$T"
	echo "## clock"; date
	echo "## clock-gate registers written by this script: none"
}
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 3; }
kp_clear() { printf 'clear\n' | sudo -n tee "$D/kpoke" >/dev/null; }
mark() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee /dev/kmsg >/dev/null; }
set_knob() { echo "$2" | sudo -n tee "$D/$1" >/dev/null; }
rd() { sudo -n cat "$D/regs" | awk -v r="$1" '$1 == "reg" && $2 == r { print $3 }'; }
RUN=$(date +%s)-$$
W=$(mktemp -d)
cleanup() { kp_clear; set_knob hold_recovery N; set_knob render_keep 0; set_knob alias_skip 0; printf "clear\n" | sudo -n tee "$D/tadata_fill" >/dev/null 2>&1; [ -n "${PB_RESTORE:-}" ] && set_knob render_pb_pages "$PB_RESTORE"; reset_gpu; rm -rf "${W:?}"; finish_log; }
trap cleanup EXIT
finish_log() { # journalctl -k holds what the short ring buffer lost (11.26: every case marker)
	sudo -n journalctl -k --since "@$START" --no-pager > "$KEEP/kernel.log" 2>&1 || sudo -n dmesg > "$KEEP/kernel.log" 2>&1
	echo "## kernel log: $(grep -c 'resgx545 case' "$KEEP/kernel.log" | tr -d ' ') case markers kept in $KEEP/kernel.log"
}
keep() { # NAME FILE [SUFFIX]: gzip the whole raw file (mtime 0), print its sizes and raw sha256
	raw=$(wc -c < "$2" | tr -d ' ')
	sha=$(sha256sum "$2" | cut -d' ' -f1)
	gzip -n -6 -c "$2" > "$KEEP/$1${3:-.txt}.gz"
	echo "  kept $1${3:-.txt}: $raw bytes raw, $(wc -c < "$KEEP/$1${3:-.txt}.gz" | tr -d ' ') gz, raw sha256 $sha"
}
BAD=0
tri_ok() { sudo -n timeout 60 "$T" tri 2>&1 </dev/null | grep -q "^diff: 0 of 4096"; }
health() { # a plain 64x64 triangle must draw exactly; the recovery path of the 11.26 resume
	sleep 3
	if tri_ok; then BAD=0; return 0; fi
	reset_gpu; sleep 5
	if tri_ok; then BAD=0; return 0; fi
	sleep 5
	if tri_ok; then BAD=0; echo "  health: recovered on the retry"; return 0; fi
	BAD=$((BAD + 1)); echo "  health: the plain triangle does not draw ($BAD)"
	[ "$BAD" -ge 3 ] && { echo "## abort: the GPU did not recover three times"; exit 1; }
	return 1
}
# pixel reduction: counts of the known colours and the box of the green pixels
PIXPY=$(cat <<'PYEOF'
import re, sys
G, B, BL, SENT = "ff00ff00", "ff203040", "ff0000ff", "deadbeef"
n = {"green": 0, "background": 0, "blue": 0, "sentinel": 0, "other": 0}
x0 = y0 = 10**9; x1 = y1 = -1; rows = 0
for line in sys.stdin:
    m = re.search(r"row (\d+): (.*)$", line)
    if not m:
        continue
    rows += 1
    y = int(m.group(1))
    for x, v in enumerate(m.group(2).split()):
        v = v[2:] if v.startswith("0x") else v
        k = {G: "green", B: "background", BL: "blue", SENT: "sentinel"}.get(v, "other")
        n[k] += 1
        if k == "green":
            x0, x1, y0, y1 = min(x0, x), max(x1, x), min(y0, y), max(y1, y)
if not rows:
    print("  no pixel rows")
else:
    box = "green box x %d-%d y %d-%d" % (x0, x1, y0, y1) if x1 >= 0 else "no green"
    print("  pixels: " + " ".join("%s %d" % kv for kv in n.items()) + "; " + box)
PYEOF
)
run_job() { # NAME SET W H TOOL_ARGS...: one tool run, whole output and dumps kept, a recovery if it failed
	name=$1 set=$2 w=$3 h=$4; shift 4
	printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$name" "$SCRIPT_NAME" "$set" "$w" "$h" "$*" >> "$KEEP/cases.tsv"
	echo "== $name set=$set ${w}x${h}"
	echo "  cmd: $T $*"
	mark "$name"
	rm -rf "${W:?}/dump"; mkdir -p "${W:?}/dump"
	sudo -n timeout "${JOB_TIMEOUT:-120}" "$T" "$@" > "$W/$name.out" 2>&1 </dev/null
	rc=$?
	echo "  rc $rc $(grep -E '^(job|tri)' "$W/$name.out" | head -1 | cut -c1-110) $(grep -E '^diff' "$W/$name.out" | head -1)"
	grep -q "row [0-9]*:" "$W/$name.out" && python3 -c "$PIXPY" < "$W/$name.out"
	keep "$name" "$W/$name.out"
	for f in "$W/dump"/*.param.bin; do [ -f "$f" ] && keep "$name" "$f" .param.bin; done
	for f in "$W/dump"/*.tadata.bin; do [ -f "$f" ] && keep "$name" "$f" .tadata.bin; done
	kp_clear
	if grep -qE "failed|faulted|hung|rejected|overflowed" "$W/$name.out" || [ "$rc" -ne 0 ]; then
		reset_gpu; health </dev/null || true
	fi
	rm -f "${W:?}/${name:?}.out"
}
run_table() { # TABLE_TEXT: lines "name|set|W|H|args" (args may name $S, $W/dump); each one a job
	while IFS='|' read -r name set w h args; do
		[ -z "$name" ] && continue
		eval "set -- $args"
		run_job "$name" "$set" "$w" "$h" "$@"
	done <<< "$1"
}
begin() { printf 'name\tscript\tset\tW\tH\targs\n' > "$KEEP/cases.tsv"; preflight; health; }
