# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q034: whether the EDM's TA pick starts a context's TA command whose syncs are incomplete when
# no other context is queued. A scene of two kicks (the first geometry only, which completes at
# its TA's finish) on one render context; its first TA command poked through the kernel poke:
# one source sync (count, dword 33, = 1; dwords 34 to 37 its read and write pending values
# 0x5a5a5a5a and both complete addresses a zero word of the context's kernel page, 0x280 past
# the HW render context, whose address is ctx:4 less 0x100 in the control run's words), and,
# as the positive control, the transfer-queue sync (dword 25 = 0x5a5a5a5a, dword 26 the same
# word), which the pick checks whatever the queue. A command the pick never starts hangs its
# job and the kernel recovers. Words by tri --words (as in render/pending-counts.sh). Root
# through sudo -n.
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
one control -n 2 --geometry 1
C=$(sed -n 's/^ctx:4=//p' "$W/control/words.1.txt")
X=$(printf 0x%08x $((C - 0x100 + 0x280)))
echo "sync word: $X (the context page, 0x280)"
one src-sync -n 2 --geometry 1 --kpoke-render "1:ta:33=1" --kpoke-render "1:ta:34=0x5a5a5a5a" \
	--kpoke-render "1:ta:35=$X" --kpoke-render "1:ta:36=0x5a5a5a5a" --kpoke-render "1:ta:37=$X"
one tq-sync -n 2 --geometry 1 --kpoke-render "1:ta:25=0x5a5a5a5a" --kpoke-render "1:ta:26=$X"
one control-after -n 2 --geometry 1
sudo -n rm -rf "$W"
