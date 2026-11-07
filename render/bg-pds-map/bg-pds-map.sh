# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q014: render command word 23 (cmd:23, the first of the background object's three PDS words) with
# bit 27 or 28 (the fetch faults at page 0x0001f000) or bit 30 or 31 (at 0x2e001000, the pixel PDS
# heap's second page) flipped, at 64x32 and 128x128, three runs each, as E363 ran them, with that
# page mapped to the render's context holding 0xd1d1d1d1 in every dword (tri --scratch 1
# --scratch-at, vm_low on for the low page) and, for comparison, unmapped; and the same with the page
# holding 0 and 0xffffffff. Every pixel printed. Root through sudo -n, for the kernel's debugfs.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1116}
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.16) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
one() {
	name=$1; shift
	echo "== $name: tri $*"
	sudo -n timeout 90 "$T" tri --pixels "$@" 2>&1 </dev/null | grep -E "^scratch|^job|^target|^diff|^first|^row|renders ok|FAILED|#1: |failed"
}
for geo in "64 32" "128 128"; do
	set -- $geo; G="--width $1 --height $2"
	for r in 1 2 3; do
		one "control-$1x$2-r$r" $G
		for b in 0x08000000 0x10000000; do
			one "bit$b-unmapped-$1x$2-r$r" $G --poke "cmd:23^=$b"
			for fill in 0xd1d1d1d1 0x00000000 0xffffffff; do
				one "bit$b-low-$fill-$1x$2-r$r" $G --poke "cmd:23^=$b" --scratch 1 --scratch-at 0x1f000 --scratch-fill $fill
			done
		done
		for b in 0x40000000 0x80000000; do
			one "bit$b-unmapped-$1x$2-r$r" $G --poke "cmd:23^=$b"
			for fill in 0xd1d1d1d1 0x00000000 0xffffffff; do
				one "bit$b-heap-$fill-$1x$2-r$r" $G --poke "cmd:23^=$b" --scratch 1 --scratch-at 0x2e001000 --scratch-fill $fill
			done
		done
	done
done
echo "## end"
