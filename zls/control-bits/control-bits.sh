# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q071, Q088: CR_ISP_ZLSCTL (render details dword 11, rd:11) on a render with depth and stencil
# buffers. A) the store setup of load-store.sh (control 0x17100c, load base 0x11000, store base
# 0xd000, stencil bases on scratch pages 0 and 4) with each bit of the control flipped, twice:
# the job's lines and the scratch pages the render changed; B) bits 1, 13 and 14 of the closed
# driver's later renders in every combination added to 0x17100c and to the load-only control
# 0x11700a, in a store arrangement and in a load arrangement (the triangle at z 0.5, depth test
# less, the scratch filled with 0.25f: a loaded depth removes it), twice. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1115}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
D=$(sudo -n sh -c "ls -d /sys/kernel/debug/dri/*/sgx" | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.15) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
RUN=$(date +%s)-$$
mark() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee /dev/kmsg >/dev/null; }
LINES="^job|^diff|^reg |^target|#1: [0-9]+ us|^tri [0-9x]+ #[0-9]+: [0-9]+ us|^tri:|failed|FAILED|^scratch"
one() { # NAME ARGS...: one tool run, the lines of its result and its exit status
	name=$1; shift
	mark "$name"
	echo "== $name: tri $*"
	out=$(sudo -n timeout 90 "$T" tri "$@" 2>&1 </dev/null); rc=$?
	echo "$out" | grep -E "$LINES"
	echo "rc $rc"
}
kp() { printf '%s\n' clear "$@" | sudo -n tee "$D/kpoke" >/dev/null; }
# run NAME POKES... : the kernel poke words armed, the job with a 16-page scratch buffer (every
# dword 0.25f before the render) and depth test less, its lines, then the poke cleared
run() {
	name=$1; shift
	kp "$@"
	one "$name" --scratch 16 --poke blk:1=0x00400200
	kp
}
trap 'kp' EXIT
Z="ta:7^=0x180 rd:1=0x3e000000"
S="rd:12=0x11000 rd:13=0xd000 rd:14=0x80001000 rd:15=0x80005000"
L="rd:12=0x1000 rd:13=0x11000"
echo "## A each bit of 0x17100c"
for r in 1 2; do
	run "ctl-r$r" $Z rd:11=0x17100c $S
	for b in $(seq 0 31); do
		run "bit$b-r$r" $Z rd:11=$(printf 0x%x $((0x17100c ^ (1 << b)))) $S
	done
done
echo "## B bits 1, 13 and 14"
for r in 1 2; do
	for base in 0x17100c 0x11700a; do
		for add in 0 2 0x2000 0x4000 0x2002 0x4002 0x6000 0x6002; do
			v=$(printf 0x%x $((base | add)))
			run "store-$v-r$r" $Z rd:11=$v $S
			run "load-$v-r$r" $Z rd:11=$v $L
		done
	done
done
echo "## end"
