# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q043: render details dword 9, the word the 3D kick loads into CR_REG_0148, at 0 (the kernel's
# value, the control), 0xffffffff and each bit alone, through the kernel poke rd:9, the
# register read back after each job (--regs, read-only); the five-copy probes of the same
# table run 0 and 0xffffffff on more geometry. Root through sudo -n, for the kernel's debugfs.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
one() {
	name=$1; shift
	echo "== $name: tri $*"
	sudo -n "$T" tri --regs 0x0148-0x0148 "$@" 2>&1 |
		grep -E "^job|^target|^diff|^reg |renders ok|FAILED|#1: [0-9]+ tri"
}
one control
one "rd9-0xffffffff" --kpoke-render "1:rd:9=0xffffffff"
for b in $(seq 0 31); do
	v=$(printf "0x%08x" $((1 << b)))
	one "rd9-$v" --kpoke-render "1:rd:9=$v"
done
one control-after
