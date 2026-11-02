# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Which pointer the firmware counts a scene's renders through: the kernel puts its RT data set
# in TA command dword 16 (ta:16) and render details dword 54 (rd:54), words no EDM path is
# typed for. Each is moved by 0x8 or 0xc through the kernel poke, within the RT data set: a
# count through it then lands in dword 3 (out-of-memory signals, which the kernel ignores) or
# dword 4 (partial renders, which the kernel reads after the job and reports as a parameter
# buffer overflow). One render, and a scene of two kicks (the first geometry only), poked on
# its first job; the controls unpoked; the cleanup trace after each. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
one() {
	name=$1; shift
	echo "== $name: tri $*"
	sudo -n "$T" tri --keep-going "$@" 2>&1 |
		grep -E "^job|^diff|renders ok|FAILED|overflowed|#[0-9]+: [0-9]+ tri"
	sudo -n cat "$D/render_cleanup" | sed 's/^/cleanup: /'
}
one control-one -n 1
one control-two -n 2 --geometry 1
for w in rd:54 ta:16; do
	for m in 0x8 0xc; do
		one "one-$w-$m" -n 1 --kpoke-render "1:$w^=$m"
		one "two-$w-$m" -n 2 --geometry 1 --kpoke-render "1:$w^=$m"
	done
done
one control-after -n 1
