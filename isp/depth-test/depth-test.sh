# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Hand-run experiments: sgxfive-test (SGXFIVE_TEST, default ~/sgxfive-test) and regtimeline
# (SGXFIVE_REGTIMELINE, default ~/regtimeline) run each case; every output is kept and nothing
# is judged here. Root through sudo -n, for the kernel's debugfs.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null

depth_precision() (
# 0x0418 (rd:26) as a depth precision mode: a loaded depth of 0.5 plus n ulp, depth test less
# (the triangle, at depth 0.5, is drawn when 0.5 is below the loaded value). The depth is
# loaded through the ZLS: ta:7 bit 7, rd:1 the ZLS base 0x3e000000, load control 0x11700a with
# rd:12 (load base) at the scratch buffer (filled with the loaded value) and rd:13 beside it.
kp() { printf '%s\n' clear "$@" | sudo -n tee "$D/kpoke" >/dev/null; }
run() { name=$1; fill=$2; shift 2
	kp "$@"
	echo "== $name"
	sudo -n "$RT" 0 0 0x0494-0x04b4 -- "$T" tri --scratch 16 \
		--scratch-fill "$fill" --poke blk:1=0x00400200 2>&1 |
		grep -E "^job|^diff|^scratch|^timeline|^tl|#1: [0-9]+ tri"
	echo "kpoke left: $(sudo -n cat "$D/kpoke" | tr '\n' ' ')"
	kp
}
LOAD="ta:7^=0x80 rd:1=0x3e000000 rd:11=0x11700a rd:12=0x1000 rd:13=0x11000"
for r26 in 0 1; do
	for v in 0x3f000000 0x3f000001 0x3f000002 0x3f000004 0x3f000008 0x3f000010 \
		 0x3f000020 0x3f000040 0x3f000080 0x3f000100 0x3f000200; do
		run "0418=$r26 loaded $v" $v $LOAD rd:26=$r26
	done
done
)

polygon_offset_clamp() (
# 0x0424 (rd:7) as the polygon offset's clamp, with the ISP1 polygon-offset flag (blk:2 bit 23)
# set and then clear. Depth goes through the ZLS: ta:7 bit 7 (FRAG_FLAGS.DEPTH_BUFFER), rd:1 the
# ZLS base 0x3e000000, store control 0x17100c with rd:13 (store base) at the scratch buffer.
# The triangle is flat at z 0 (depth 0.5), depth less and written (blk:1 0x00400200). Each
# case prints the job, the scratch dwords the render changed (the stored depth) and the
# register timeline over 0x0494-0x04b4.
kp() { printf '%s\n' clear "$@" | sudo -n tee "$D/kpoke" >/dev/null; }
run() { name=$1; fill=$2; shift 2
	kp "$@"
	echo "== $name"
	sudo -n "$RT" 0 0 0x0494-0x04b4 -- "$T" tri --scratch 16 \
		--scratch-fill "$fill" --poke blk:1=0x00400200 $UPOKE 2>&1 |
		grep -E "^job|^diff|^scratch|^timeline|^tl|#1: [0-9]+ tri"
	echo "kpoke left: $(sudo -n cat "$D/kpoke" | tr '\n' ' ')"
	kp
}
STORE="ta:7^=0x80 rd:1=0x3e000000 rd:11=0x17100c rd:13=0x1000"
echo "### polygon offset: units x clamp, the stored depth"
UPOKE="--poke blk:2^=0x800000"
for units in 0 1 16 4096 1048576; do
	for clamp in 0 0x3c23d70a 0xbc23d70a 0x3f800000 0x00000010; do
		run "units $units clamp $clamp" 0x3f800000 $STORE rd:5=$units rd:7=$clamp
	done
done
echo "### polygon offset: factor 4.0 on the flat triangle (no slope), clamp 0"
run "factor 4 units 0" 0x3f800000 $STORE rd:6=0x40800000
UPOKE=""
echo "### without the polygon-offset flag, units 4096"
run "no flag units 4096" 0x3f800000 $STORE rd:5=4096
)
echo "#### depth-precision"
depth_precision
echo "## exit $?"
echo "#### polygon-offset-clamp"
polygon_offset_clamp
echo "## exit $?"
