# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q003: with debugfs hold_recovery set, a render that faults is held (three kinds of fault: the TA's
# read of an unmapped stream page, tri --fault; the EDM's write to the read-only TA/3D control block,
# alias_ta3d_ro; a background program fetched from the pixel PDS heap, tri --pixels --poke
# cmd:23^=0x08000000). Two seconds in, the event registers are read and the host event enables
# (CR_EVENT_HOST_ENABLE 0x0130, CR_EVENT_HOST_ENABLE2 0x0110, written through debugfs kregnow) are
# set: first every bit of both, then, for each bit that reads set in the status registers (so that
# the bit is alone), a fault of its own with that bit and the EDM's own event enabled. kregnow
# reports the host interrupts (all, and those with no SW_EVENT) and the status of the last. An idle
# control enables every bit with no job. The fault is cleared by debugfs reset after each case.
# Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1117}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.17) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null
echo "## tool"; sha256sum "$T"
W=$(mktemp -d)
rd() { sudo -n cat "$D/regs" | awk -v r="$1" '$1 == "reg" && $2 == r { print $3 }'; }
kn() { sudo -n cat "$D/kregnow" | tail -n 1; }
set_knob() { echo "$2" | sudo -n tee "$D/$1" >/dev/null; }
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
trap 'set_knob hold_recovery N; set_knob alias_ta3d_ro N; reset_gpu; rm -rf "$W"' EXIT
start() { # KIND: the faulting job, in the background
	case $1 in
	ta) sudo -n "$T" tri --fault --wait-ms 20000 >"$W/job.out" 2>&1 & ;;
	ta3d) sudo -n "$T" tri --wait-ms 20000 >"$W/job.out" 2>&1 & ;;
	pds) sudo -n "$T" tri --pixels --poke cmd:23^=0x08000000 --wait-ms 20000 >"$W/job.out" 2>&1 & ;;
	esac
}
ST1=0; ST2=0
case_run() { # NAME KIND VALUE1 VALUE2 (the enables to write; empty: none)
	name=$1 kind=$2 v1=${3:-} v2=${4:-}
	reset_gpu
	set_knob hold_recovery Y
	[ "$kind" = ta3d ] && set_knob alias_ta3d_ro Y
	start "$kind"
	sleep 2.5
	ST1=$(rd 0x012c); ST2=$(rd 0x0118)
	echo "== $name"
	echo "before: status $ST1 $ST2 bif_int $(rd 0x0c04) bif_fault $(rd 0x0c08) enable $(rd 0x0130)"
	echo "kregnow before: $(kn)"
	[ -n "$v1" ] && echo "write 0x0130=$v1" && echo "0x0130=$v1" | sudo -n tee "$D/kregnow" >/dev/null
	[ -n "$v2" ] && echo "write 0x0110=$v2" && echo "0x0110=$v2" | sudo -n tee "$D/kregnow" >/dev/null
	sleep 1
	echo "after: status $(rd 0x012c) $(rd 0x0118) bif_int $(rd 0x0c04) enable $(rd 0x0130)"
	echo "kregnow after: $(kn)"
	echo "kernel: $(sudo -n dmesg | tail -n 6 | grep -E 'kregnow|host interrupt' | sed 's/^\[[ 0-9.]*\] //' | tr '\n' ';')"
	set_knob hold_recovery N
	[ "$kind" = ta3d ] && set_knob alias_ta3d_ro N
	reset_gpu
	wait
	grep -E "^job|failed" "$W/job.out" | head -n 2 | sed 's/^/job: /'
}
echo "#### idle control"
reset_gpu
echo "kregnow: $(kn)"
echo "write 0x0130=0xffffffff 0x0110=0xffffffff"
echo "0x0130=0xffffffff" | sudo -n tee "$D/kregnow" >/dev/null
echo "0x0110=0xffffffff" | sudo -n tee "$D/kregnow" >/dev/null
sleep 1
echo "kregnow: $(kn)"
reset_gpu
echo "#### an unfaulted fill after the control"
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
for kind in ta ta3d pds; do
	echo "#### fault $kind"
	case_run "$kind-none" "$kind"
	case_run "$kind-all" "$kind" 0xffffffff 0xffffffff
	s1=$ST1 s2=$ST2
	for i in $(seq 0 31); do
		if [ $(( (s1 >> i) & 1 )) -eq 1 ] && [ "$i" -ne 14 ]; then
			case_run "$kind-enable-bit$i" "$kind" "$(printf '0x%x' $(( 0x4000 | (1 << i) )))"
		fi
	done
	for i in $(seq 0 31); do
		if [ $(( (s2 >> i) & 1 )) -eq 1 ]; then
			case_run "$kind-enable2-bit$i" "$kind" "" "$(printf '0x%x' $(( 1 << i )))"
		fi
	done
done
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
