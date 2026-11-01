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

042c_bit31_dumps() (
# The 4x multisampling words with 0x042c bit 31 set and clear (cmd:13), each render's memory
# dumped into $HOME/msaa31/VALUE.
P="--poke cmd:16=0xeaa26e26 --poke cmd:10=0xeaa26e26"
for v in 0x80000002 0x00000002; do
	mkdir -p "$HOME/msaa31/$v"
	echo "== cmd:13=$v"
	sudo -n "$T" tri -n 1 --keep-going $P --poke cmd:13=$v --dump-render "$HOME/msaa31/$v" 2>&1 |
		grep -E "^job|#1: [0-9]|render memory"
done
)

042c_modes() (
# 0x042c bits 1:0 at 0-3 (cmd:13 = 0x8000000N) with the sample positions in cmd:16 and cmd:10
# (0xeaa26e26 in both), without and with the TE anti-aliasing bits (cmd:1 = 0xe0000000): the
# triangle's pixels each time, to see how many samples each mode stores per pixel.
P="--poke cmd:16=0xeaa26e26 --poke cmd:10=0xeaa26e26"
for te in 0 1; do
	for m in 0 1 2 3; do
		TE=""
		[ $te = 1 ] && TE="--poke cmd:1=0xe0000000"
		echo "== mode $m te $te"
		# shellcheck disable=SC2086
		sudo -n "$T" tri --keep-going --pixels $P --poke "cmd:13=0x8000000$m" $TE 2>&1 |
			grep -E "^job|^row |^tri 64x64 #1: [0-9]"
	done
done
)

closed_words_step_by_step() (
# 4x multisampling on the triangle, the words added one step at a time: the sample positions
# 0xeaa26e26 in 0x04c8 (cmd:16) and 0x0230 (cmd:10), 0x042c bit 1 (cmd:13 = 0x80000002), the TE
# anti-aliasing bits 31:30 (cmd:1 = 0xe0000000), and the macrotile words through kernel pokes
# of the first render (ta:143, ta:144 = 0x802002, ta:146 = 0x4).
kp() { printf '%s\n' clear "$@" | sudo -n tee "$D/kpoke" >/dev/null; }
run() { name=$1; shift
	kp
	echo "== $name"
	sudo -n "$T" tri --keep-going "$@" 2>&1 | grep -E "^job|^tri 64x64 #1: [0-9]|^target|^diff"
	echo "kpoke left: $(sudo -n cat "$D/kpoke" | tr '\n' ' ')"
	kp
}
P="--poke cmd:16=0xeaa26e26 --poke cmd:10=0xeaa26e26"
MT="--kpoke-render 1:ta:143=0x802002 --kpoke-render 1:ta:144=0x802002 --kpoke-render 1:ta:146=0x4"
run "control"
run "sample positions" $P
run "+ 0x042c bit 1" $P --poke cmd:13=0x80000002
run "+ TE AA" $P --poke cmd:13=0x80000002 --poke cmd:1=0xe0000000
run "+ macrotiles" $P --poke cmd:13=0x80000002 --poke cmd:1=0xe0000000 $MT
run "+ 0x042c bit 31 clear" $P --poke cmd:13=0x00000002 --poke cmd:1=0xe0000000 $MT
run "0x042c bit 31 clear alone" --poke cmd:13=0
)
echo "#### 042c-bit31-dumps"
042c_bit31_dumps
echo "## exit $?"
echo "#### 042c-modes"
042c_modes
echo "## exit $?"
echo "#### closed-words-step-by-step"
closed_words_step_by_step
echo "## exit $?"
