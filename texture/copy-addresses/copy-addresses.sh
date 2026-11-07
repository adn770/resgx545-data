# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q007: where the copy's buffers lie, and what the page before the source holds. The 64x32 copy over
# the plain and the every-value source, as built and with the source 4 rows down (--sy 4) and
# with the target 16 rows long, each with --print-addrs (the source's and destination's
# addresses) and --page-before (the source's buffer has a page of counting dwords, 0xB0000000 | i,
# before the source), with T2 (tex:2) as built and with bits 12, 13 and 14 flipped, and bits 12 and 13 together (the source's
# address less 4 KiB when the buffer's address has bit 12 clear and bit 13 set); three runs. Every
# pixel read back. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1116}
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.16) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
cp() { echo "#### $1"; shift; sudo -n timeout 60 "$T" copy --print-addrs --page-before --pixels "$@" 2>&1; echo "## exit $?"; }
for run in 1 2 3; do
	for src in plain every; do
		E=""
		[ $src = every ] && E=--every-value
		for at in "" "--sy 4" "--height 16"; do
			for flip in none 0x1000 0x2000 0x3000 0x4000; do
				P=""
				[ $flip = none ] || P="--poke tex:2^=$flip"
				cp "run $run $src ${at:-as built}: tex:2 $flip" $E $at $P
			done
		done
	done
done
echo "## end"
