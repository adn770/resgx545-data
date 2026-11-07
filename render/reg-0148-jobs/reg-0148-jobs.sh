# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q043: render details dword 9 (rd:9, CR_REG_0148) at 0 and 1 in the jobs the earlier runs did not
# cover: a render with depth and stencil stored (the store setup of zls/control-bits.sh), 4x
# multisampled renders (CR_ISP_MSAA modes 1 and 2 with the closed driver's sample words and TE
# bits, cmd:1, cmd:10, cmd:13, cmd:16), and the plain triangle at 1024x768 for the time; each
# three times, the job's lines, its time and the scratch pages the render changed. Root through
# sudo -n.
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
Z="ta:7^=0x180 rd:1=0x3e000000 rd:11=0x17100c rd:12=0x11000 rd:13=0xd000 rd:14=0x80001000 rd:15=0x80005000"
POS=0xeaa26e26
for r in 1 2 3; do
	for v in 0 1; do
		run "depth-stencil-rd9-$v-r$r" $Z rd:9=$v
		for n in 1 2; do
			kp "rd:9=$v"
			one "msaa$n-rd9-$v-r$r" --poke cmd:1=0xe0000000 --poke cmd:10=$POS \
				--poke cmd:13=$((0x80000000 | n)) --poke cmd:16=$POS
			kp
		done
		kp "rd:9=$v"
		one "big-rd9-$v-r$r" --width 1024 --height 768 --max-width 1024 --max-height 768
		kp
	done
done
echo "## end"
