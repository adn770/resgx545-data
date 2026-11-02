# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q014: render command word 23 (cmd:23, the first of the background object's three PDS words)
# with bits 27, 28, 30 and 31 flipped, twice each, every pixel printed (--pixels); the same
# flip of bit 27 through the kernel poke of TA command dword 2 (ta:2), where the kernel puts
# the word; an unpoked control first. Root through sudo -n, for the kernel's debugfs.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
one() {
	name=$1; shift
	echo "== $name: tri $*"
	sudo -n "$T" tri --pixels "$@" 2>&1 | grep -E "^job|^target|^diff|^first|^row|renders ok|FAILED|#1: "
}
one control
for r in 1 2; do
	for b in 0x08000000 0x10000000 0x40000000 0x80000000; do
		one "cmd23-$b-r$r" --poke "cmd:23^=$b"
	done
done
one "ta2-0x08000000" --kpoke-render "1:ta:2^=0x08000000"
