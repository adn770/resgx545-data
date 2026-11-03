# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# render_uapi.md section 13's follow-up on the pending count a recovery reset sets (linux fork
# commit 30): render jobs queued on other contexts while a faulting render is held, so the
# reset that ends the hold runs them again. With debugfs hold_recovery set, a render faulting
# on its unmapped stream page (tri --fault, 30 s wait) in the background; 3 s in, three more
# tri processes, each its own context, started 1 s apart with a 30 s wait and --words (debugfs
# render_words and buf09 saved before the first render and after each): one render whose
# render flag bit 10 is cleared (kernel poke ta:7^=0x400), one render, and a scene of three
# kicks (the first two geometry only, so only the first is queued at the reset). 2 s later
# debugfs reset is written while the hold is set, then the hold goes back to N. render_words
# shows the newest render context, so the round runs twice: the render without bit 10
# started last (replay-a), then the scene (replay-b); a case's snapshots are its own only
# when it is the newest. Each process's lines, words and control blocks follow, in the 11.10
# scripts' format (render_words.py report), and the driver's lines since each round's mark
# (render_words.py log). The three without a hold close the table. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1110}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.10) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
W=$(mktemp -d)
RUN=$(date +%s)-$$	# the cases' marks are this run's
TOOL_LINES="^job|^diff|renders ok|FAILED|failed|#[0-9]+: [0-9]+ tri|kpoke before|geometry only"
hold() { echo "$1" | sudo -n tee "$D/hold_recovery" >/dev/null; echo "hold_recovery: $1"; }
mark() { printf 'resgx545 case %s %s\n' "$1" "$RUN" | sudo -n tee /dev/kmsg >/dev/null; }
lines() {
	echo "## lines $1"
	sudo -n dmesg | awk -v m="resgx545 case $1 $RUN" 'index($0, m) {on = 1; next}
		on && /sgxfive|SGX/ {print "kline: " $0}'
}
words() {
	n=0
	while [ -f "$W/$1/words.$n.txt" ]; do
		echo "#### words $n"; cat "$W/$1/words.$n.txt"; echo "#### end"
		echo "ta3d $n: $(od -An -tx4 -v -w4 "$W/$1/ta3d.$n.bin" | tr -d ' ' | tr '\n' ' ')"
		n=$((n + 1))
	done
}
reset_gpu() {
	s=$(date +%s%N)
	echo 1 | sudo -n tee "$D/reset" >/dev/null
	echo "reset: ret $?, $(( ($(date +%s%N) - s) / 1000 )) us"
}
BIT10="-n 1 --kpoke-render 1:ta:7^=0x400"
ONE="-n 1"
SCENE="-n 3 --geometry 1 --geometry 2 --move 2:12,12 --move 3:24,0"
# start the three queued jobs' processes in the order given, PREFIX naming their cases
start() {
	prefix=$1; shift
	for c in "$@"; do
		case $c in bit10-clear) a=$BIT10 ;; one-render) a=$ONE ;; *) a=$SCENE ;; esac
		name=$prefix-$c
		mkdir -p "$W/$name"
		# shellcheck disable=SC2086
		sudo -n "$T" tri --keep-going --wait-ms 30000 --words "$W/$name" $a \
			> "$W/$name.out" 2>&1 &
		echo "$name $a" >> "$W/cases"
		sleep 1
	done
}
show() {
	while read -r name args; do
		echo "== $name: tri $args"
		grep -E "$TOOL_LINES" "$W/$name.out"
		words "$name"
	done < "$W/cases"
	: > "$W/cases"
}
trap 'hold N' EXIT
: > "$W/cases"
# a held round: the faulting render, then the three in the order given, the reset
round() {
	r=$1; shift
	mark "$r"
	hold Y
	sudo -n "$T" tri --fault --wait-ms 30000 > "$W/fault.out" 2>&1 &
	sleep 3
	start "$r" "$@"
	sleep 2
	reset_gpu
	hold N
	wait
	echo "== $r-fault: tri --fault (held, then reset)"
	grep -E "$TOOL_LINES" "$W/fault.out"
	show
	lines "$r"
}
round replay-a one-render three-kicks bit10-clear
round replay-b bit10-clear one-render three-kicks
mark control
start control bit10-clear one-render three-kicks
wait
show
lines control
sudo -n rm -rf "$W"
