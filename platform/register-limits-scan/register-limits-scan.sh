# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q001: after register-limits found 0x0818 = 0x3ff drawing wrong at 128x128 and up (not at 64x64,
# 96x96): A) the triangle at 32 to 512 in steps of 16, 0x0818 at 0x7ff and at 0x3ff, twice;
# B) every fourth value of 0x0818, 0 to 0x7ff, and every value with bit 8 set and bit 10 clear,
# around a 256x256 triangle (one run each: 896 values); C) the single
# bits and their complements (within the implemented bits) of 0x0814 (17 bits) and 0x0810 (bit 0),
# and 0x0818's, around the same; D) every value B found drawing wrong, three more times at
# 256x256 and at 128x128 (the first 60 when there are more). Each run: the registers written,
# one tool process (a fresh context),
# a line "run SET REG=VALUE SIZE: rc N diff: ... hash ... ms". The registers go back to their
# init values after every run and at the end. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1115}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.15) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
put() { printf '%s\n' "$2" | sudo -n tee "$D/$1" >/dev/null; }
reg() { sudo -n cat "$D/kreg" | awk -v o="$1" '$1 == o { print $2 }'; }
INIT="0x0810=0x1 0x0814=0xffff 0x0818=0x7ff"
setregs() { for kv in $1; do put kreg "$kv" || echo "kreg $kv not written"; done; }
trap 'setregs "$INIT"' EXIT
tri() { # GROUP REG VALUE SIZE
	grp=$1 reg=$2 val=$3 size=$4
	setregs "$reg=$val"
	got=$(reg "$reg")
	s=$(date +%s%N)
	out=$(sudo -n timeout 60 "$T" tri --width "$size" --height "$size" --max-width "$size" \
		--max-height "$size" 2>&1 </dev/null); rc=$?
	ms=$(( ($(date +%s%N) - s) / 1000000 ))
	d=$(echo "$out" | grep -E "^diff:" | cut -c1-80)
	h=$(echo "$out" | grep -E "^target:" | sed 's/.*hash //')
	us=$(echo "$out" | grep -E "^tri [0-9]+x[0-9]+ #1: [0-9]+ us" | sed 's/.*: //')
	echo "run $grp $reg=$val (reads $got) ${size}x${size}: rc $rc $d hash $h time $us wall $ms ms"
	case "$rc $d" in "0 diff: 0 of "*) ;; *) bad="$bad $val" ;; esac
	for kv in $INIT; do [ "${kv%%=*}" = "$reg" ] && put kreg "$kv"; done
}
echo "## A sizes"
for r in 1 2; do
	for size in $(seq 32 16 512); do
		tri A 0x0818 0x7ff "$size"
		tri A 0x0818 0x3ff "$size"
	done
done
echo "## B 0x0818: every fourth value and every value with bit 8 set and bit 10 clear"
bad=""
for v in $(seq 0 2047); do
	[ $((v % 4)) -eq 0 ] || { [ $((v & 0x100)) -ne 0 ] && [ $((v & 0x400)) -eq 0 ]; } || continue
	tri B 0x0818 "$(printf '0x%x' "$v")" 256
done
echo "## B drew wrong:$bad"
badB=$(echo $bad | tr ' ' '\n' | head -n 60)
echo "## C single bits and complements"
for b in $(seq 0 16); do
	v=$((1 << b)); c=$((0x1ffff ^ v))
	tri C 0x0814 "$(printf '0x%x' "$v")" 256
	tri C 0x0814 "$(printf '0x%x' "$c")" 256
done
tri C 0x0810 0x0 256
tri C 0x0810 0x1 256
for b in $(seq 0 10); do
	v=$((1 << b)); c=$((0x7ff ^ v))
	tri C 0x0818 "$(printf '0x%x' "$v")" 256
	tri C 0x0818 "$(printf '0x%x' "$c")" 256
done
echo "## D the values B found wrong, again"
for r in 1 2 3; do
	for v in $badB; do
		tri D 0x0818 "$v" 256
		tri D 0x0818 "$v" 128
	done
done
echo "## end: 0810=$(reg 0x0810) 0814=$(reg 0x0814) 0818=$(reg 0x0818)"
