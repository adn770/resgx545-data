# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q001: for each value V of 0x0818 made of bits 10:8 in every combination (0 to 7) and a low byte
# of 0x00, 0x7f and 0xff (24 values), and each pair of triangle sizes (96, 128) and (128, 96): the
# register written, the two triangles, the register back at 0x7ff; "value V A B: first DIFF,
# second DIFF" (the tool's diff line without its tail). Three times. Each triangle is one process of
# the tool (a fresh context) with --max-width and --max-height at its size.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1115}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.15) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
put() { printf '%s\n' "$2" | sudo -n tee "$D/$1" >/dev/null; }
trap 'put kreg 0x0818=0x7ff' EXIT
tri() { # SIZE
	sudo -n timeout 60 "$T" tri --width "$1" --height "$1" --max-width "$1" --max-height "$1" \
		2>&1 </dev/null | grep -E "^diff:" | sed 's/ pixels.*//; s/diff: //'
}
VALUES=""
for hi in $(seq 0 7); do
	for lo in 0 127 255; do VALUES="$VALUES $(printf '0x%x' $(( (hi << 8) | lo )))"; done
done
echo "## values: $VALUES"
for rep in 1 2 3; do
	for v in $VALUES; do
		for pair in "96 128" "128 96"; do
			set -- $pair
			put kreg 0x0818=$v
			f=$(tri "$1"); s=$(tri "$2")
			put kreg 0x0818=0x7ff
			echo "value $rep $v $1 $2: first $f, second $s"
		done
	done
done
echo "## end: $(sudo -n cat "$D/kreg" | grep 0x0818)"
