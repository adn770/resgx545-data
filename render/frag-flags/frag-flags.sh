# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q041, FRAG_FLAGS.BIT10 and Q065: the EDM's TA/3D control block (debugfs buf09, TA3DCtl, the
# 59 dwords on one "ta3dctl:" line) and the last render-context cleanup (debugfs
# render_cleanup) after jobs whose render flags (TA command dword 7, kernel value 0x400) have
# bits 2, 3, 2 and 3, or 10 flipped through the kernel poke ta:7; after two renders on one
# context, the first with bits 2 and 3; after a scene of two kicks; and after jobs of one to
# four renders. The block is read after the tool's context is gone. Twice over. Root through
# sudo -n, for the kernel's debugfs.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
state() {
	echo "ta3dctl: $(sudo -n od -An -tx4 -v -w4 "$D/buf09" | tr -d ' ' | tr '\n' ' ')"
	sudo -n cat "$D/render_cleanup" | sed 's/^/cleanup: /'
}
one() {
	name=$1; shift
	echo "== $name: tri $*"
	sudo -n "$T" tri --keep-going "$@" 2>&1 |
		grep -E "^job|^diff|renders ok|FAILED|overflowed|#[0-9]+: [0-9]+ tri"
	state
}
for r in 1 2; do
	one "flags-none-r$r" -n 1
	for f in 0x4 0x8 0xc 0x400; do
		one "flags-$f-r$r" -n 1 --kpoke-render "1:ta:7^=$f"
	done
	one "two-renders-0xc-r$r" -n 2 --kpoke-render "1:ta:7^=0xc"
	one "two-kicks-r$r" -n 2 --geometry 1
	for n in 1 2 3 4; do
		one "renders-$n-r$r" -n "$n"
	done
done
