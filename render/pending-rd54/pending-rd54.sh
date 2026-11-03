# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q029: render details word 54 (the RT data set the firmware counts in) moved by 0x8 through
# the kernel poke, on one render and on the geometry kick of a scene of two kicks, the counts
# read with tri --words (render_words and buf09 before the first render and after each, as in
# pending-counts.sh); then a render unpoked. A cleanup that fails makes the kernel reset the
# GPU. Root through sudo -n.
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
one one-rd54-0x8 -n 1 --kpoke-render "1:rd:54^=0x8"
one two-rd54-0x8 -n 2 --geometry 1 --kpoke-render "1:rd:54^=0x8"
one control-after -n 1
sudo -n rm -rf "$W"
