# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Hand-run experiments: sgxfive-test (SGXFIVE_TEST, default ~/sgxfive-test) and regtimeline
# (SGXFIVE_REGTIMELINE, default ~/regtimeline) run each case; every output is kept and nothing
# is judged here. Root through sudo -n, for the kernel's debugfs.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test}
RT=${SGXFIVE_REGTIMELINE:-$HOME/regtimeline}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## module"; modinfo -F srcversion gma500_gfx 2>/dev/null

0800_pixel_time() (
# CR_REG_0800 bits 5:0 as a pixel task limit: a 1024x1024 render of the probe tri-long-pixel
# (case 0: 150 dependent fmads per pixel, case 1: the store alone; programs built into
# $SGXFIVE_PROBE_BINS, default $HOME/sgxprobes), 0x0800 poked through rd:22. The wall time is
# the CPU's setup and readback; the render's own time is taken from CR_CLKGATESTATUS (0x0008)
# sampled by regtimeline (about every 8 us): the time the ISP's clock (bit 0) is on, in us.
# Five times per value, with the probe's summary.
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes}
run() { poke=$1 bin=$2
	printf '%s\n' clear $poke | sudo -n tee "$D/kpoke" >/dev/null
	t0=$(date +%s%N)
	r=$(sudo -n "$RT" 0 0 0x0008 -- "$T" probe --temps 4 --pixels --tri \
		pixel --width 1024 --height 1024 "$B/tri-long-pixel__$bin.bin" 2>&1)
	isp=$(echo "$r" | awk '/^tl /{ if (on) sum += $2 - pt; on = and(strtonum("0x" $3), 1); pt = $2 }
		END { printf "%d", sum / 1000 }')
	t1=$(date +%s%N)
	echo "${poke:-base} case $bin $(( (t1 - t0) / 1000000 )) ms, ISP on $isp us: $(echo "$r" |
		grep -E "o0 mixed|o0 0x|failed" | sed 's/^probe [^:]*: //') | left: $(sudo -n cat "$D/kpoke" | tr '\n' ' ')"
	printf 'clear\n' | sudo -n tee "$D/kpoke" >/dev/null
}
for r in 1 2 3 4 5; do
	for b in 0 1; do
		run "" $b
		for v in 0x30 0x1 0x2 0x4 0x8 0x10 0x20 0x3f 0x0; do run rd:22=$v $b; done
	done
done
)

0abc_per_data_master() (
# CR_PDS_REG_0ABC bits 4:1 (the firmware's init value 0xe) against each kind of job: with the
# bits cleared (kreg 0x0abc=0x0), a fill (a transfer), then a geometry-only render (the TA
# alone), then a whole render (TA and 3D); the register restored to 0xe and the SGX checked
# with a fill after each. A hang recovers the SGX, which runs the init script again.
kset() { printf '%s\n' "$1" | sudo -n tee "$D/kreg" >/dev/null
	echo "kreg $1: $(sudo -n cat "$D/kreg" | grep 0x0abc)"; }
check() { echo "  after: $(sudo -n "$T" fill 2>&1 | grep -E '^job|^diff' | tr '\n' ' ')"; }
for job in "fill" "tri -n 2 --geometry 1 --keep-going" "tri -n 1"; do
	echo "== $job"
	kset 0x0abc=0x0
	# shellcheck disable=SC2086
	sudo -n "$T" $job 2>&1 | grep -E "^job|geometry only|renders ok|FAILED|^diff" | tr '\n' ' '
	echo
	kset 0x0abc=0xe
	check
done
)

kick_time() (
# The time of a 256x256 render (six renders, the average of the last five from each render's
# own "us" line) with CR_PDS_REG_0ABC (init value 0xe) at 0x02 to 0x3e and CR_PDS_REG_0A78 (init
# value 0x2c) at 0x00 to 0x3f, written through kreg between runs; each register restored after
# its series.
put() { printf '%s\n' "$1" | sudo -n tee "$D/kreg" >/dev/null; }
t() { sudo -n "$T" tri --width 256 --height 256 -n 6 2>&1 |
	awk '/ us$/ {n++; if (n>1) s+=$(NF-1)} /renders ok/ {ok=1}
		END {printf "%6d us avg of 5 %s", s/5, ok ? "ok" : "FAIL"}'; }
for v in 0x02 0x04 0x06 0x08 0x0a 0x0c 0x0e 0x10 0x14 0x18 0x1e 0x3e; do
	put 0x0abc=$v; echo "0x0abc=$v: $(t)"
done
put 0x0abc=0x0000000e
for v in 0x00 0x01 0x08 0x10 0x20 0x2c 0x3f; do
	put 0x0a78=$v; echo "0x0a78=$v: $(t)"
done
put 0x0a78=0x0000002c
)
echo "#### 0800-pixel-time"
0800_pixel_time
echo "## exit $?"
echo "#### 0abc-per-data-master"
0abc_per_data_master
echo "## exit $?"
echo "#### kick-time"
kick_time
echo "## exit $?"
