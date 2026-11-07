# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q001: 0x0810, 0x0814 and 0x0818 (kreg) narrowed while jobs of growing load run. Each run is
# one process of the tool (a fresh context) after the registers are written, with the job's
# lines kept (job, target hash, diff, outside, the job's time, the triangle's times) and the
# process's wall time, its exit status and the driver's new log lines that name a fault, a hang,
# a recovery or a reset. Cases: the init values, then 0x0814 at 0x1ffff, 0x7fff, 0x3ff, 0xff,
# 0xf, 0x1 and 0, 0x0818 at 0x3ff, 0xff, 0xf, 0x1 and 0, 0x0810 at 0, and all three at 0; each
# case runs every workload, the whole matrix three times (REPEATS), the registers written back
# and read after every run. Last: with 0x0814 and 0x0818 narrowed a reset is written to debugfs
# and the registers read after it, to see whether the reset restores them.
# Workloads: fill, copy and triangle at their default targets (64x32, 64x32, 64x64) and at
# 1024x1024 (1024 tiles), the triangle at 2048x2048 (4096 tiles), eight back-to-back renders,
# sixty-four chained dummy transfers, and fills whose pixel program loops 1000, 400000 and 1250000
# times (staged as $SGXFIVE_PROBE_BINS). Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1115}
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes-stage}
REPEATS=${REPEATS:-3}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.15) for the laptop first"; exit 1; }
for n in 1000 400000 1250000; do
	[ -f "$B/loop-$n.bin" ] || { echo "no $B/loop-$n.bin: stage the loops"; exit 1; }
done
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
put() { printf '%s\n' "$2" | sudo -n tee "$D/$1" >/dev/null; }
reg() { sudo -n cat "$D/kreg" | awk -v o="$1" '$1 == o { print $2 }'; }
regs() { echo "0810=$(reg 0x0810) 0814=$(reg 0x0814) 0818=$(reg 0x0818)"; }
INIT="0x0810=0x1 0x0814=0xffff 0x0818=0x7ff"
setregs() { for kv in $1; do put kreg "$kv" || echo "kreg $kv not written"; done; }
KEEP="^(job|target|diff|outside|fill|copy|dummy|tri [0-9]+x[0-9]+ #[0-9]+: [0-9]+ us|tri: |probe .*(job time|failed|o0)|sgxfive-test)"
KLOG="fault|hang|recover|reset|timeout|firmware"
run() { # CASE WORKLOAD ARGS...
	rep=$1 case=$2 wl=$3; shift 3
	l0=$(sudo -n dmesg | wc -l)
	s=$(date +%s%N)
	out=$(sudo -n timeout 120 "$T" "$@" 2>&1 </dev/null); rc=$?
	ms=$(( ($(date +%s%N) - s) / 1000000 ))
	echo "== run $rep $case $wl: rc $rc wall $ms ms"
	echo "$out" | grep -E "$KEEP"
	sudo -n dmesg | tail -n +$((l0 + 1)) | grep -i -E "$KLOG" | cut -c1-160 | sed 's/^/klog: /'
}
workloads() { # prints name|args
	cat <<EOF
fill-64x32|fill
copy-64x32|copy
tri-64x64|tri
fill-1024x1024|fill --width 1024 --height 1024 --stride 4096
copy-1024x1024|copy --width 1024 --height 1024 --src-stride 4096 --dst-stride 4096
tri-1024x1024|tri --width 1024 --height 1024 --max-width 1024 --max-height 1024
tri-2048x2048|tri --width 2048 --height 2048 --max-width 2048 --max-height 2048
tri-256x256-n8|tri --width 256 --height 256 -n 8
dummy-64|dummy -n 64
loop-1000|probe $B/loop-1000.bin
loop-400000|probe $B/loop-400000.bin
loop-1250000|probe $B/loop-1250000.bin
EOF
}
CASES="init|$INIT
r0814=0x1ffff|0x0814=0x1ffff
r0814=0x7fff|0x0814=0x7fff
r0814=0x3ff|0x0814=0x3ff
r0814=0xff|0x0814=0xff
r0814=0xf|0x0814=0xf
r0814=0x1|0x0814=0x1
r0814=0|0x0814=0x0
r0818=0x3ff|0x0818=0x3ff
r0818=0xff|0x0818=0xff
r0818=0xf|0x0818=0xf
r0818=0x1|0x0818=0x1
r0818=0|0x0818=0x0
r0810=0|0x0810=0x0
all=0|0x0810=0x0 0x0814=0x0 0x0818=0x0"
trap 'setregs "$INIT"' EXIT
echo "## start: $(regs)"
for rep in $(seq 1 "$REPEATS"); do
	echo "$CASES" | while IFS='|' read -r name vals; do
		setregs "$INIT"
		setregs "$vals"
		echo "## case $rep $name: set $vals reads $(regs)"
		workloads | while IFS='|' read -r wl args; do
			run "$rep" "$name" "$wl" $args
		done
		echo "## case $rep $name: after the jobs $(regs)"
		setregs "$INIT"
		echo "## case $rep $name: restored $(regs)"
	done
done
echo "## reset"
setregs "0x0814=0x3ff 0x0818=0xff 0x0810=0x0"
echo "before the reset: $(regs)"
put reset 1; echo "reset: ret $?"
sleep 2
echo "after the reset: $(regs)"
run 0 after-reset fill-64x32 fill
run 0 after-reset tri-64x64 tri
setregs "$INIT"
echo "## end: $(regs)"
