# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q066: the three background-object words the 3D kick builds from render details dwords 69, 76 and
# 77 (rd:69, rd:76, rd:77), as the control leaves them after the triangle job (tri --words), then
# each bit flipped, one job each, every pixel summarised by the job's own diff line and hash, at
# 64x64, with the control before and after. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1115}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
D=$(sudo -n sh -c "ls -d /sys/kernel/debug/dri/*/sgx" | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.15) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
RUN=$(date +%s)-$$
mark() { printf "resgx545 case %s %s\n" "$1" "$RUN" | sudo -n tee /dev/kmsg >/dev/null; }
LINES="^job|^diff|^reg |^target|#1: [0-9]+ us|^tri [0-9x]+ #[0-9]+: [0-9]+ us|^tri:|failed|FAILED|^scratch"
one() { # NAME ARGS...: one tool run, the lines of its result and its exit status
	name=$1; shift
	mark "$name"
	echo "== $name: tri $*"
	out=$(sudo -n timeout 90 "$T" tri "$@" 2>&1 </dev/null); rc=$?
	echo "$out" | grep -E "$LINES"
	echo "rc $rc"
}
W=$(mktemp -d)
sudo -n "$T" tri --words "$W" >/dev/null 2>&1 </dev/null
for r in 69 76 77; do
	v=$(grep -h "^rd:$r=" "$W/words.1.txt" | head -n 1 | cut -d= -f2)
	eval "V$r=\${v:-0x0}"
done
echo "control words: rd:69=$V69 rd:76=$V76 rd:77=$V77"
one control
for r in 69 76 77; do
	eval "v=\$V$r"
	for b in $(seq 0 31); do
		one "rd$r-b$b" --kpoke-render "1:rd:$r=$(printf 0x%08x $(( v ^ (1 << b) )))"
	done
	one "rd$r-zero" --kpoke-render "1:rd:$r=0x0"
	one "rd$r-ones" --kpoke-render "1:rd:$r=0xffffffff"
done
one control-after
sudo -n rm -rf "$W"
