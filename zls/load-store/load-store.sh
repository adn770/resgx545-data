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

load_compare() (
# The loaded depth against the triangle: control 0x11700a (load only), the scratch buffer
# filled with 0.25f, the triangle at z 0.5 (default) or z 0.1 (blk:10 = 0x3dcccccd), depth
# test less (blk:1 0x00400200) or greater (0x01000200), with the load base (rd:12) on the
# scratch buffer or on the target (0xdeadbeef before the render) and the store base (rd:13) on
# either. Each case prints the triangle count of the job.
kp() { printf '%s\n' clear "$@" | sudo -n tee "$D/kpoke" >/dev/null; }
run() { name=$1 poke=$2; shift 2
	kp "$@"
	printf '%-58s ' "$name"
	sudo -n "$T" tri --scratch 16 $poke 2>&1 | grep -E "#1: [0-9]+ tri|^job: f" | cut -c1-40 | tr '\n' ' '
	echo
	kp
}
Z="ta:7^=0x80 rd:1=0x3e000000 rd:11=0x11700a"
LESS5="--poke blk:1=0x00400200"
LESS1="--poke blk:1=0x00400200 --poke blk:10=0x3dcccccd"
GRT1="--poke blk:1=0x01000200 --poke blk:10=0x3dcccccd"
for r in 1 2; do
	run "z.5 less, both scratch"            "$LESS5" $Z rd:12=0x1000 rd:13=0x9000
	run "z.5 less, 0484 scratch 0488 target" "$LESS5" $Z rd:12=0x1000 rd:13=0x11000
	run "z.5 less, 0484 target 0488 scratch" "$LESS5" $Z rd:12=0x11000 rd:13=0x1000
	run "z.1 less, 0484 scratch 0488 target" "$LESS1" $Z rd:12=0x1000 rd:13=0x11000
	run "z.1 greater, no load"               "$GRT1" ta:7^=0x80
	run "z.1 greater, both scratch"          "$GRT1" $Z rd:12=0x1000 rd:13=0x9000
	run "z.1 greater, 0484 scratch 0488 target" "$GRT1" $Z rd:12=0x1000 rd:13=0x11000
	run "z.1 greater, 0484 target 0488 scratch" "$GRT1" $Z rd:12=0x11000 rd:13=0x1000
done
)

stencil_bases() (
# The stencil bases (rd:14 0x048c, rd:15 0x0490) with the depth store of control 0x17100c
# (rd:12 0x11000, rd:13 0xd000) into the scratch buffer: ta:7 bit 8 (FRAG_FLAGS.STENCIL_BUFFER)
# set with bit 7, and with bit 7 only; bit 31 of each base set and clear, 0x048c on page 0 and
# 0x0490 on page 4 and the other way round. Each case prints the job and the scratch pages the
# render changed.
kp() { printf '%s\n' clear "$@" | sudo -n tee "$D/kpoke" >/dev/null; }
run() { name=$1; shift
	kp "$@"
	echo "== $name"
	sudo -n "$T" tri --scratch 16 --poke blk:1=0x00400200 2>&1 |
		grep -E "^job|^scratch|#1: [0-9]+ tri" | cut -c1-90
	kp
}
S="ta:7^=0x180 rd:1=0x3e000000 rd:11=0x17100c rd:12=0x11000 rd:13=0xd000"
run "store, 048c page 0, 0490 page 4" $S rd:14=0x80001000 rd:15=0x80005000
run "store, 048c page 4, 0490 page 0" $S rd:14=0x80005000 rd:15=0x80001000
run "store, no bit 31: 048c page 0, 0490 page 4" $S rd:14=0x1000 rd:15=0x5000
run "bit 31 on 048c only" $S rd:14=0x80001000 rd:15=0x5000
run "bit 31 on 0490 only" $S rd:14=0x1000 rd:15=0x80005000
run "both, flag bit 8 off" ta:7^=0x80 rd:1=0x3e000000 rd:11=0x17100c rd:12=0x11000 rd:13=0xd000 \
	rd:14=0x80001000 rd:15=0x80005000
)

store_load_bases() (
# The ZLS bases into the job's 16-page scratch buffer (tri --scratch 16: every dword 0.25f
# before the render, the dwords the render changed reported page by page). Render flags ta:7
# bit 7 (FRAG_FLAGS.DEPTH_BUFFER), rd:1 the ZLS base 0x3e000000; the triangle writes depth
# (blk:1 0x00400200, depth test less). Control 0x17100c (a clearing frame, stores) and 0x11700a
# (keeps the previous depth, stores nothing) with the load base (rd:12, 0x0484) and the store
# base (rd:13, 0x0488) on scratch pages 0 and 8 either way round, and at the target; the BIF
# fault lines of the kernel log at the end.
kp() { printf '%s\n' clear "$@" | sudo -n tee "$D/kpoke" >/dev/null; }
run() { name=$1; shift
	kp "$@"
	echo "== $name"
	sudo -n "$T" tri --scratch 16 --poke blk:1=0x00400200 2>&1 |
		grep -E "^job|^diff|^outside|^scratch|#1: [0-9]+ tri"
	kp
}
Z="ta:7^=0x80 rd:1=0x3e000000"
for r in 1 2; do
	run "flag only" ta:7^=0x80
	for ctl in 0x17100c 0x11700a; do
		run "ctl $ctl, 0x0484 page 0, 0x0488 page 8" $Z rd:11=$ctl rd:12=0x1000 rd:13=0x9000
		run "ctl $ctl, 0x0484 page 8, 0x0488 page 0" $Z rd:11=$ctl rd:12=0x9000 rd:13=0x1000
	done
	Z2="$Z rd:11=0x11700a"
	run "no load (flag only)" ta:7^=0x80
	run "0x0484 scratch, 0x0488 target" $Z2 rd:12=0x1000 rd:13=0x11000
	run "0x0484 target, 0x0488 scratch" $Z2 rd:12=0x11000 rd:13=0x1000
done
sudo -n dmesg | grep -i "bif fault" | tail -4
)
echo "#### load-compare"
load_compare
echo "## exit $?"
echo "#### stencil-bases"
stencil_bases
echo "## exit $?"
echo "#### store-load-bases"
store_load_bases
echo "## exit $?"
