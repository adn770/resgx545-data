# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q106: kept-owner-gone-context.sh with the DPM registers 0x0600-0x0750 read at every snapshot of
# the words (tri --words with --regs: before the first render (0), after it and before the close
# (101), after the close (201), after the second context's render (1); the open cases have 101
# between the renders only). Cases, two runs each: control; the first context's render flags
# flipped by 0x4 (bit 2), 0x8 and 0xc, the first context closed early; the same flips with it
# kept open. The words (dwords 20, 21 and 25) are printed for each snapshot and, for the
# registers, the first snapshot in full and the later ones as the registers that changed since the
# one before. Then regtimeline (a line at every change of the range) around the faulting case
# (0xc, the first closed early). The GPU is reset before each case. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1120}
R=$HOME/regtimeline
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.20) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$SRCV_FILE"
echo "## loaded module"; SRCV_LOADED=$(sudo -n cat /sys/module/gma500_gfx/srcversion); echo "$SRCV_LOADED"
[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
echo "## tool"; sha256sum "$T"
echo "## clock"; date
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
W=$(mktemp -d)
trap 'reset_gpu; rm -rf "$W"' EXIT
KEEP="^(job|diff|tri|tri2|kpoke)|failed|FAILED|cleanup|ta3dctl"
dw() { od -An -tx4 -v -j $((4 * $2)) -N 4 "$1" | tr -d ' '; }
PY=$(cat <<'PYEOF'
import re, sys
snap, prev, cur = None, {}, {}
order = []
def flush():
    global prev
    if snap is None:
        return
    if not prev:
        print("snapshot %s: %d registers, non-zero: %s" % (snap, len(cur), " ".join(
            "%s=%s" % (k, v) for k, v in cur.items() if v != "0x00000000")))
    else:
        ch = ["%s %s->%s" % (k, prev.get(k, "-"), v) for k, v in cur.items() if prev.get(k) != v]
        print("snapshot %s: %d registers changed: %s" % (snap, len(ch), "; ".join(ch)))
    prev = dict(cur)
for line in sys.stdin:
    m = re.match(r"tri: registers at snapshot (\d+)", line)
    if m:
        flush()
        snap, cur = m.group(1), {}
        order.append(snap)
        continue
    m = re.match(r"reg (0x[0-9a-f]+) (0x[0-9a-f]+)", line)
    if m and snap is not None:
        cur[m.group(1)] = m.group(2)
flush()
PYEOF
)
case_run() { # NAME ARGS...
	name=$1; shift
	between=--close-first-early
	[ "${name#open-}" != "$name" ] && between="--words-between"
	echo "== $name: tri -n 1 --ctx2 $between $*"
	reset_gpu
	n=$(sudo -n dmesg | wc -l)
	mkdir -p "$W/$name"
	sudo -n timeout 120 "$T" tri --wait-ms 5000 -n 1 --ctx2 $between --close-trace \
		--words "$W/$name" --regs 0x0600-0x0750 "$@" 2>&1 </dev/null > "$W/$name.out"
	grep -E "$KEEP" "$W/$name.out" | grep -v "us$" | cut -c1-170
	python3 -c "$PY" < "$W/$name.out"
	for k in 0 101 201 1; do
		f="$W/$name/ta3d.$k.bin"
		[ -f "$f" ] && echo "ta3d snapshot $k: dword20 0x$(dw $f 20) dword21 0x$(dw $f 21) dword25 0x$(dw $f 25)"
	done
	sudo -n dmesg | tail -n +$((n + 1)) | grep -iE "hang|reset|recover|timed out|fault|lost|cancel" |
		cut -c1-180 | head -6
}
for i in 1 2; do
	case_run "control-$i"
	for v in 0x4 0x8 0xc; do
		case_run "first-flip-$v-$i" --kpoke-render "1:ta:7^=$v"
	done
	for v in 0x4 0xc; do
		case_run "open-first-flip-$v-$i" --kpoke-render "1:ta:7^=$v"
	done
done
if [ -x "$R" ]; then
	for i in 1 2; do
		echo "== timeline-first-flip-0xc-$i: regtimeline 3.0 0.01 0x0600-0x0750 -- tri -n 1 --ctx2 --close-first-early"
		reset_gpu
		sudo -n timeout 120 "$R" 3.0 0.01 0x0600-0x0750 -- "$T" tri --wait-ms 5000 -n 1 --ctx2 \
			--close-first-early --kpoke-render 1:ta:7^=0xc 2>&1 </dev/null |
			grep -vE "^tri: (render context|words)|^layout:|us$" | cut -c1-200
	done
else
	echo "no $R: no timeline"
fi
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
