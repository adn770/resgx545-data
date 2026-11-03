# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q005: what asking the firmware for its identity costs right after a boot. Three times: debugfs
# reset (the kernel stops the core, rebuilds the firmware's buffers and boots it in place),
# timed from the shell; then GETMISCINFO through debugfs miscinfo twice, each read timed from
# the shell and the kernel's own "answered after" line kept; the driver's last kernel lines.
# Then the triangle, and GETMISCINFO once more. Root through sudo -n.
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
mi() {
	s=$(date +%s%N)
	m=$(sudo -n cat "$D/miscinfo" 2>&1 | head -n 1)
	echo "miscinfo $1: $(( ($(date +%s%N) - s) / 1000 )) us: $m"
}
for i in 1 2 3; do
	echo "== reset-$i"
	s=$(date +%s%N)
	echo 1 | sudo -n tee "$D/reset" >/dev/null
	echo "reset: ret $?, $(( ($(date +%s%N) - s) / 1000 )) us"
	mi first
	mi second
	sudo -n dmesg | tail -n 3 | sed 's/^/dmesg: /'
done
echo "== after: tri"
sudo -n "$T" tri 2>&1 | grep -E "^diff|renders ok|FAILED"
mi after
sudo -n rm -rf "$W"
