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

register_readback() (
# The TA command's zero words (ta:155-168) loaded with ~0, the registers they go to read back
# after the job (--regs): the bits each register implements, next to the register after an
# ordinary job.
for w in 155:0x0a04 156:0x0aa0 158:0x02b0 159:0x02d4 160:0x02d0 161:0x02b4 162:0x0324 163:0x0368 164:0x0364 165:0x0370 166:0x0374 168:0x02a8; do
	n=${w%%:*}; r=${w#*:}
	v=$(sudo -n "$T" tri -n 1 --keep-going --kpoke-render "1:ta:$n=0xffffffff" --regs "$r-$r" 2>&1 |
		grep -iE "^reg|$r" | tail -1)
	b=$(sudo -n "$T" tri -n 1 --keep-going --regs "$r-$r" 2>&1 | grep -iE "^reg|$r" | tail -1)
	echo "ta:$n -> $r: ~0 gives [$v], baseline [$b]"
done
)

value_dumps() (
# The TA command's words that are zero in the usual job (ta:152-168: the registers loaded for
# the TA, 0x0240, 0x0244, 0x0a04, 0x0aa0, 0x02b0, 0x02d4, 0x02d0, 0x02b4, 0x0324, 0x0368, 0x0364,
# 0x0370, 0x0374, 0x074c, 0x02a8) at 1, 0x80000000 and ~0 through the kernel pokes, the
# triangle's render memory dumped after each render (--dump-render) into $HOME/tawords/NAME,
# with two baselines first to tell the dumps' own variation. The dumps compare with
# tools/usse-asm/pbdump.py.
out=$HOME/tawords
rm -rf "$out"
mkdir -p "$out"
one() {
	name=$1; shift
	mkdir -p "$out/$name"
	r=$(sudo -n "$T" tri -n 1 --keep-going "$@" --dump-render "$out/$name" 2>&1 |
		grep -E "^job|render memory|renders ok|FAILED" | tr '\n' ' ')
	echo "$name: $r"
}
one base1
one base2
for w in 152 153 155 156 158 159 160 161 162 163 164 165 166 167 168; do
	for v in 0x1 0x80000000 0xffffffff; do
		one "ta$w-$v" --kpoke-render "1:ta:$w=$v"
	done
done
)
echo "#### register-readback"
register_readback
echo "## exit $?"
echo "#### value-dumps"
value_dumps
echo "## exit $?"
