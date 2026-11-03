# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q029: what the RT data set's cleanup compares. One render, its words read with tri --words
# (as in pending-counts.sh); then one render each with the kernel's pending count (kw:1, which
# the set's word 0 points at) poked to 2 and to 0 after the kernel's own write (1), and with it
# at 2 and the set's word 0 pointed at the set's executed count (word 1) instead; the RT data
# set's address is render details word 54 of the first render. A cleanup that fails makes the
# kernel reset the GPU. Root through sudo -n.
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
one control -n 1
R=$(sed -n 's/^rd:54=//p' "$W/control/words.1.txt")
echo "rtds: $R"
one pending-plus-one -n 1 --kpoke-render "1:kw:1=2"
one pending-minus-one -n 1 --kpoke-render "1:kw:1=0"
one pointer-to-executed -n 1 --kpoke-render "1:kw:1=2" \
	--kpoke-render "1:rtds:0=$(printf 0x%08x $((R + 4)))"
one control-after -n 1
sudo -n rm -rf "$W"
