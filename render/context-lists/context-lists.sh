# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q083: TA/3D control block dword 49 and the bus interface's directory lists with many render
# contexts alive at once. After a debugfs reset (the dword back to 0), N tri processes, each
# its own VM and context, are started one at a time: each renders a 128x128 triangle and then
# waits, its context alive, writing its every pixel (--pixels) into a pipe read only once all
# are started. After each first render: the control block's dword 49, CR_BIF_DIR_LIST_BASE0
# (0x0c84) and BASE1 to BASE15 (0x0c38-0x0c70) through debugfs regs, and the context's page
# directory (render_words ctx:2, saved by --words after the render, while it is the newest
# context). Then all go on to a second render on their live context and report it. N = 14
# (no two contexts on one list if the dword picks a list), then 16 (the 16th first kick after
# the wrap). Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1110}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.10) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
W=$(mktemp -d)
KEEP="^job|^diff|renders ok|FAILED|failed|#[0-9]+: [0-9]+ tri"
d49() { sudo -n od -An -tx4 -v -w4 -j 196 -N 4 "$D/buf09" | tr -d ' '; }
lists() {
	sudo -n cat "$D/regs" | awk '$1 == "reg" && ($2 == "0x0c84" || ($2 >= "0x0c38" &&
		$2 <= "0x0c70")) {printf "%s=%s ", $2, $3} END {print ""}'
}
alive() {
	n=$1 r=$W/r$1
	mkdir -p "$r"
	echo 1 | sudo -n tee "$D/reset" >/dev/null
	echo "## $n alive: after the reset dword 49 $(d49)"
	echo "lists: $(lists)"
	for i in $(seq 1 "$n"); do
		mkdir -p "$r/$i"
		sudo -n "$T" tri -n 2 --width 128 --height 128 --pixels --words "$r/$i" 2>&1 |
			(while [ ! -e "$r/go" ]; do sleep 0.1; done; grep -E "$KEEP") > "$r/$i.out" &
		k=0
		while [ ! -f "$r/$i/words.1.txt" ] && [ $k -lt 100 ]; do sleep 0.05; k=$((k + 1)); done
		pd=$(grep '^ctx:2=' "$r/$i/words.1.txt" 2>/dev/null | cut -d= -f2)
		echo "context $i: pd ${pd:-?} dword 49 $(d49)"
		echo "lists: $(lists)"
	done
	touch "$r/go"
	wait
	for i in $(seq 1 "$n"); do
		echo "== alive-$n-context-$i: tri -n 2 --width 128 --height 128"
		cat "$r/$i.out"
	done
	echo "## $n alive: at the end dword 49 $(d49)"
	echo "lists: $(lists)"
}
alive 14
alive 16
sudo -n dmesg | tail -n 5 | sed 's/^/dmesg: /'
sudo -n rm -rf "$W"
