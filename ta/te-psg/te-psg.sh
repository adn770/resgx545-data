# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q064: CR_TE_PSG (0x0218) and CR_DPM_STATE_CONTEXT_ID (0x0630) read back after jobs (--regs,
# read-only): one render, two renders, a scene of two kicks; then the TA command's te_psg word
# (ta:147, the kernel's 0x00400000 on a scene's last kick) with bit 24, bit 21 or both already
# set, and at 0, the TA's output of each dumped (--dump-render, printed as gzip in base64
# between "#### param NAME" or "#### tadata NAME" and "#### end"). Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
W=$(mktemp -d)
one() {
	name=$1; regs=$2; shift 2
	echo "== $name: tri --regs $regs $*"
	sudo -n "$T" tri --keep-going --regs "$regs" "$@" 2>&1 |
		grep -E "^job|^diff|^reg |renders ok|FAILED|#[0-9]+: [0-9]+ tri"
}
dumped() {
	name=$1; shift
	mkdir -p "$W/$name"
	one "$name" 0x0218-0x0218 "$@" --dump-render "$W/$name"
	for f in param tadata; do
		if sudo -n test -f "$W/$name/tri.$f.bin"; then
			echo "#### $f te-psg-$name"
			sudo -n gzip -c "$W/$name/tri.$f.bin" | base64 -w 76
			echo "#### end"
		fi
	done
}
one psg-one 0x0218-0x0218 -n 1
one psg-two 0x0218-0x0218 -n 2
one psg-kicks 0x0218-0x0218 -n 2 --geometry 1
one ctx-one 0x0630-0x0630 -n 1
one ctx-two 0x0630-0x0630 -n 2
one ctx-kicks 0x0630-0x0630 -n 2 --geometry 1
dumped control -n 1
dumped bit24 -n 1 --kpoke-render "1:ta:147=0x01400000"
dumped bit21 -n 1 --kpoke-render "1:ta:147=0x00600000"
dumped both -n 1 --kpoke-render "1:ta:147=0x01600000"
dumped zero -n 1 --kpoke-render "1:ta:147=0x0"
sudo -n rm -rf "$W"
