# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q015: the library's triangle job with VDM state word 1 bits 11:9 = 7 (vdm:1^=0xa00), ten times
# without the pixel readback and ten times with it (--pixels), alternating; then bits 11:9 = 3 and
# = 5, ten times each with the readback, and the unpoked control ten times with it. Each job's
# lines, its time and the kernel log lines of its case (the driver's hang and reset lines). A
# reset runs the init script again. Root through sudo -n.
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
for r in $(seq 1 10); do
	go "seven-noread-r$r" --poke "vdm:1^=0xa00"
	go "seven-read-r$r" --poke "vdm:1^=0xa00" --pixels
done
for r in $(seq 1 10); do
	go "three-read-r$r" --poke "vdm:1^=0x200" --pixels
	go "five-read-r$r" --poke "vdm:1^=0xe00" --pixels
	go "control-read-r$r" --pixels
done
echo "## end"
