# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q015 again: state1-hang.sh alternated the jobs with and without the readback, and every hang
# of bits 11:9 = 7 followed a job of the same word that completed. So each series here runs one
# kind of job in a row: A) ten jobs of 7 without readback in a row, B) ten with readback in a
# row, C) 7 then the unpoked control, ten times (no readback), D) ten of 3 and ten of 5 with
# readback in a row, E) the control three times then 7 without readback, five times. Each job's
# lines, its time and the kernel log lines of its case. Root through sudo -n.
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
klines() {
	sudo -n dmesg | awk -v m="resgx545 case $1 $RUN" 'index($0, m) {on = 1; next}
		on && /BIF fault|hung|reset|recover/ {print "kline: " $0}'
}
go() { one "$@"; klines "$1"; }
echo "## A seven, no readback, in a row"
for r in $(seq 1 10); do go "A-seven-noread-r$r" --poke "vdm:1^=0xa00"; done
echo "## B seven, readback, in a row"
for r in $(seq 1 10); do go "B-seven-read-r$r" --poke "vdm:1^=0xa00" --pixels; done
echo "## C seven then control"
for r in $(seq 1 10); do
	go "C-seven-r$r" --poke "vdm:1^=0xa00"
	go "C-control-r$r"
done
echo "## D three and five in a row"
for r in $(seq 1 10); do go "D-three-read-r$r" --poke "vdm:1^=0x200" --pixels; done
for r in $(seq 1 10); do go "D-five-read-r$r" --poke "vdm:1^=0xe00" --pixels; done
echo "## E control x3 then seven"
for r in 1 2 3 4 5; do
	go "E-control1-r$r"; go "E-control2-r$r"; go "E-control3-r$r"
	go "E-seven-r$r" --poke "vdm:1^=0xa00"
done
echo "## end"
