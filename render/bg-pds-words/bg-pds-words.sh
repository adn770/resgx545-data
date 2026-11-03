# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q014: the background object's three PDS words (render command words 23 to 25) with a high
# bit flipped (sgxfive-test tri --poke cmd:N^=BIT), on 64x32 and 128x128 targets, three runs
# each for word 23's bits 27, 28, 30 and 31, and once each on 64x64 for words 24 and 25's
# bits 27 and 31. Per case: the job's lines, each row's count of pixels other than the tool's
# sentinel 0xdeadbeef (rows with none left out) and the driver's fault lines since the case's
# mark ("resgx545 case", the bus fault's address among them). Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1110}
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.10) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
RUN=$(date +%s)-$$
mark() { printf 'resgx545 case %s %s\n' "$1" "$RUN" | sudo -n tee /dev/kmsg >/dev/null; }
lines() {
	sudo -n dmesg | awk -v m="resgx545 case $1 $RUN" 'index($0, m) {on = 1; next}
		on && /BIF fault|hung|SGX reset/ {print "kline: " $0}'
}
one() {
	name=$1; shift
	mark "$name"
	echo "== $name: tri $*"
	sudo -n "$T" tri --pixels "$@" 2>&1 | awk '
		/^row / {n = 0; for (i = 3; i <= NF; i++) if ($i != "0xdeadbeef") n++
			if (n) s = s " " substr($2, 1, length($2) - 1) ":" n; next}
		/^(job|diff)|renders ok|FAILED|#1: / {print}
		END {print "rows:" s}'
	lines "$name"
}
for size in 64x32 128x128; do
	S="--width ${size%x*} --height ${size#*x}"
	# shellcheck disable=SC2086
	one "control-$size" $S
	for r in 1 2 3; do
		for b in 0x08000000 0x10000000 0x40000000 0x80000000; do
			# shellcheck disable=SC2086
			one "cmd23-$b-$size-r$r" $S --poke "cmd:23^=$b"
		done
	done
done
for w in 24 25; do
	for b in 0x08000000 0x80000000; do
		one "cmd$w-$b-64x64" --poke "cmd:$w^=$b"
	done
done
