# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# 11.6's kick-objects scenes (E288) again on the kernel that counts each kick in the RT data
# set's pending count: one scene over one, two and three TA kicks (geometry jobs, the later
# triangles moved), each scene's parameter buffer and TA data dumped after its closing render
# (--dump-render) and printed as gzip in base64 between "#### param NAME" or "#### tadata
# NAME" and "#### end", and the context's cleanup trace (debugfs render_cleanup) after each.
# Once. Root through sudo -n.
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
for s in "1:-n 1" "2:-n 2 --geometry 1 --move 2:12,12" \
	"3:-n 3 --geometry 1 --geometry 2 --move 2:12,12 --move 3:24,0"; do
	k=${s%%:*}; a=${s#*:}
	mkdir -p "$W/k$k"
	echo "== kicks-$k: tri $a"
	# shellcheck disable=SC2086
	sudo -n "$T" tri $a --keep-going --dump-render "$W/k$k" 2>&1 |
		grep -E "renders ok|FAILED|render memory|#[0-9]+: "
	cleanup
	for f in param tadata; do
		echo "#### $f kicks$k"
		sudo -n gzip -c "$W/k$k/tri.$f.bin" | base64 -w 76
		echo "#### end"
	done
done
sudo -n rm -rf "$W"
