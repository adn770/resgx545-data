# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q001: for each value V of 0x0818 (0x3ff, then the init value 0x7ff) and each ordered pair of
# triangle sizes (A, B) from 64, 96, 128, 160 and 256: the register written, a triangle of size A,
# one of size B, the register back at 0x7ff; "pair V A B: first DIFF, second DIFF". Then the same
# with the register written between the jobs (first at 0x7ff, second at V). Twice. Each triangle
# is one process of the tool (a fresh context) with --max-width and --max-height at its size.
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
SIZES="64 96 128 160 256"
for rep in 1 2; do
	for v in 0x3ff 0x7ff; do
		for a in $SIZES; do
			for b in $SIZES; do
				put kreg 0x0818=$v
				f=$(tri "$a"); s=$(tri "$b")
				put kreg 0x0818=0x7ff
				echo "pair $rep $v $a $b: first $f, second $s"
			done
		done
		for a in $SIZES; do
			for b in $SIZES; do
				put kreg 0x0818=0x7ff
				f=$(tri "$a")
				put kreg 0x0818=$v
				s=$(tri "$b")
				put kreg 0x0818=0x7ff
				echo "written-between $rep $v $a $b: first $f, second $s"
			done
		done
	done
done
echo "## end: $(sudo -n cat "$D/kreg" | grep 0x0818)"
