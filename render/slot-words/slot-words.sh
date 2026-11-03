# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q041: what the DPM slot words (TA/3D control block dwords 20 and 21, the RT data owning each
# DPM context slot; 25 the TA's RT data) and the access word (kw:0, which render details word
# 52 points at) hold around renders whose render flags (TA command dword 7, kernel value 0x400)
# have bits 2, 3 or both flipped through the kernel poke ta:7; two renders, the first with
# both; a render on a new context after a context whose render had both, against one after a
# plain render, with the DPM registers 0x0600-0x0750 (--regs, read-only); then, with debugfs
# rtds_keep off and on (renders leave the RT data set's size words and out-of-memory counters
# as the previous job left them), a scene of two kicks, two renders the first with both bits,
# and two renders with the set's out-of-memory count (rtds:3) poked to 5 at the first. Words
# by tri --words (as in pending-counts.sh). rtds_keep goes back to N. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1110}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.10) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
W=$(mktemp -d)
# the snapshots tri --words saved in $W/$1, in render order, and the control block
words() {
	n=0
	while [ -f "$W/$1/words.$n.txt" ]; do
		echo "#### words $n"; cat "$W/$1/words.$n.txt"; echo "#### end"
		echo "ta3d $n: $(od -An -tx4 -v -w4 "$W/$1/ta3d.$n.bin" | tr -d ' ' | tr '\n' ' ')"
		n=$((n + 1))
	done
}
ta3d_after() {
	echo "ta3d after: $(sudo -n od -An -tx4 -v -w4 "$D/buf09" | tr -d ' ' | tr '\n' ' ')"
}
cleanup() { sudo -n cat "$D/render_cleanup" | sed 's/^/cleanup: /'; }
TOOL_LINES="^job|^diff|renders ok|FAILED|overflowed|#[0-9]+: [0-9]+ tri|kpoke before|geometry only"
TOOL_LINES="$TOOL_LINES|failed|^reg 0x"
one() {
	name=$1; shift
	mkdir -p "$W/$name"
	echo "== $name: tri $*"
	sudo -n "$T" tri --keep-going --words "$W/$name" "$@" 2>&1 | grep -E "$TOOL_LINES"
	words "$name"
	ta3d_after
	cleanup
}
keep() { echo "$1" | sudo -n tee "$D/rtds_keep" >/dev/null; echo "rtds_keep: $1"; }
trap 'keep N' EXIT
for f in 0x4 0x8 0xc; do
	one "flags-$f" -n 1 --kpoke-render "1:ta:7^=$f"
done
one two-renders-0xc -n 2 --kpoke-render "1:ta:7^=0xc"
one plain -n 1
one next-after-plain -n 1 --regs 0x0600-0x0750
one keep-0xc -n 1 --kpoke-render "1:ta:7^=0xc"
one next-after-0xc -n 1 --regs 0x0600-0x0750
for k in N Y; do
	keep "$k"
	one "keep$k-scene" -n 2 --geometry 1
	one "keep$k-renders-0xc" -n 2 --kpoke-render "1:ta:7^=0xc"
	one "keep$k-oom-word" -n 2 --kpoke-render "1:rtds:3=0x5"
done
keep N
sudo -n rm -rf "$W"
