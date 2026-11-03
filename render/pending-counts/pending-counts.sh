# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q029: the RT data set's counts, read while the context lives. sgxfive-test tri --words saves
# the kernel's debugfs render_words (the HW render context, the RT data set, the PB
# descriptor, the kernel's words and the render details, a kpoke line each) and buf09 (the
# TA/3D control block) before the first render and after each; the kernel's pending count is
# kw:1, the firmware's executed count rtds:1. One render, scenes of two and three kicks (the
# first ones geometry only), two renders, two scenes of two kicks, a render with render flag
# bit 10 (0x400) cleared and a scene of two kicks whose closing render has it cleared; after
# each the control block once the context is gone and the cleanup's trace (debugfs
# render_cleanup). Root through sudo -n.
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
one one-render -n 1
one two-kicks -n 2 --geometry 1
one three-kicks -n 3 --geometry 1 --geometry 2
one two-renders -n 2
one two-scenes-of-two -n 4 --geometry 1 --geometry 3
one bit10-clear -n 1 --kpoke-render "1:ta:7^=0x400"
one bit10-clear-two-kicks -n 2 --geometry 1 --kpoke-render "2:ta:7^=0x400"
one one-render-after -n 1
sudo -n rm -rf "$W"
