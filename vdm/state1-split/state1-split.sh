# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q015 split: the sweep's case `vdm:1^=0xa00` (VDM state word 1 bits 11:9 = 7) on the
# library's triangle job (sgxfive-test tri), alone, with every pixel read back (--pixels) and
# with the render memory dumped (--dump-render), after an unpoked control; the probe jobs of
# the same table run the word on the probe's triangle. Each job's result lines are kept; the
# dump is printed as gzip in base64 between "#### param NAME" or "#### tadata NAME" and
# "#### end" (isp_words.py unpack). Root through sudo -n, for the kernel's debugfs.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
W=$(mktemp -d)
one() {
	name=$1; shift
	echo "== $name: tri $*"
	# shellcheck disable=SC2086
	sudo -n "$T" tri "$@" 2>&1 | grep -E "^job|^target|^diff|^first|^row|renders ok|FAILED|render memory|#1: "
}
one control
one plain --poke "vdm:1^=0xa00"
one pixels --poke "vdm:1^=0xa00" --pixels
mkdir -p "$W/d"
one dump --poke "vdm:1^=0xa00" --dump-render "$W/d"
for f in param tadata; do
	if sudo -n test -f "$W/d/tri.$f.bin"; then
		echo "#### $f state1-split-dump"
		sudo -n gzip -c "$W/d/tri.$f.bin" | base64 -w 76
		echo "#### end"
	fi
done
sudo -n rm -rf "$W"
