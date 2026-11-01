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

depth_scenes() (
# Five overlapping objects (the probes isp-depth-test-always, -less, -translucent,
# -translucent-nowrite and -punch: five copies of the triangle at clip z 0, 1/16 .. 4/16, each
# pixel coloured with the z of the copy that won it) with every implemented bit of the
# render-only registers flipped through the kernel's rd pokes (rd:26 0x0418, rd:21 0x04dc,
# rd:51 0x04e8, rd:19 0x0520, rd:22 0x0800), and 0 and ~0 of each. A case prints only when its
# pixels differ from the scene's baseline (taken twice first).
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes}
for sc in always:0x01D00200 less:0x00400200 translucent:0x02400200 translucent-nowrite:0x03D00200 punch:0x08400200; do
	n=${sc%%:*}; isp0=${sc#*:}
	P="$T probe --tri pixpds:12 --width 64 --height 64 --vertices 15 --copy-depth --vtx-coords 2 --blk 1=$isp0 --pixels --slot pixel=$B/pix_pa0.bin --slot vtxuse=$B/vtx_z.bin $B/isp-depth-test-${n}__0.bin"
	printf "clear\n" | sudo -n tee "$D/kpoke" >/dev/null
	base=$(sudo -n $P 2>&1 | grep -vE "scratch at|scratch unchanged" | md5sum | cut -c1-8)
	again=$(sudo -n $P 2>&1 | grep -vE "scratch at|scratch unchanged" | md5sum | cut -c1-8)
	echo "== $n baseline $base $again"
	one() { printf "clear\n" | sudo -n tee "$D/kpoke" >/dev/null
		printf "%s\n" "$1" | sudo -n tee "$D/kpoke" >/dev/null || echo "$1 REFUSED"
		out=$(sudo -n $P 2>&1 | grep -vE "scratch at|scratch unchanged")
		m=$(echo "$out" | md5sum | cut -c1-8)
		[ "$m" != "$base" ] && echo "$1 CHANGED $(echo "$out" | grep -oE "o0 mixed.*|failed.*" | head -1 | cut -c1-100)"
	}
	one "rd:26^=0x1"
	for b in 0x1 0x2 0x4; do one "rd:21^=$b"; done
	for b in 0x1 0x100; do one "rd:51^=$b"; done
	i=0; while [ $i -lt 32 ]; do one "rd:19^=$(printf 0x%x $((1 << i)))"; i=$((i + 1)); done
	for i in 0 1 2 3 4 5 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23; do
		one "rd:22^=$(printf 0x%x $((1 << i)))"
	done
	for r in 26 21 51 19 22; do one "rd:$r=0"; one "rd:$r=0xffffffff"; done
done
printf "clear\n" | sudo -n tee "$D/kpoke" >/dev/null
echo done
)

many_triangles() (
# The render-only ISP registers under 42 overlapping triangles per tile (the probes
# isp-render-only-registers-many-opaque and isp-render-only-registers-many-less; the programs built with tools/usse-asm/probe.py build into
# $SGXFIVE_PROBE_BINS, default $HOME/sgxprobes). In a render these registers load from the
# render details, so each value goes in through a kernel poke (rd:22 0x0800, rd:51 0x04e8,
# rd:21 0x04dc, rd:26 0x0418, rd:19 0x0520); "left" is empty when the job took it. Each case
# prints the probe's summary and the job's wall time.
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes}
run() { poke=$1
	for p in isp-render-only-registers-many-opaque isp-render-only-registers-many-less; do
		extra=""; [ $p = isp-render-only-registers-many-less ] && extra="--blk 1=0x00400200"
		printf '%s\n' clear $poke | sudo -n tee "$D/kpoke" >/dev/null
		t0=$(date +%s%N)
		r=$(sudo -n "$T" probe --temps 32 --pixels --tri pixel --width 64 --height 64 \
			--vertices 126 $extra "$B/${p}__0.bin" 2>&1)
		t1=$(date +%s%N)
		echo "${poke:-base} $p $(( (t1 - t0) / 1000000 )) ms: $(echo "$r" |
			grep -E "o0 mixed|o0 0x|failed|usage" | sed 's/^probe [^:]*: //') | left: $(sudo -n cat "$D/kpoke" | tr '\n' ' ')"
		printf 'clear\n' | sudo -n tee "$D/kpoke" >/dev/null
	done
}
for r in 1 2; do
	run ""
	for v in 0 0x1 0x2 0x4 0x8 0x10 0x20 0x3f 0x130 0xffff30; do run rd:22=$v; done
	for v in 0 0x1 0x101; do run rd:51=$v; done
	for v in 0x1 0x2 0x4; do run rd:21=$v; done
	run rd:26=0
	run rd:19=0xffffffff
done
)

textured_triangle() (
# The same flips and values of the render-only registers on a textured 3D triangle (the
# probe texture-fetch-tex-fetch: sampling, wrap and the twiddled fetch): a case prints only
# when its pixels differ from the baseline (taken twice first).
B=${SGXFIVE_PROBE_BINS:-$HOME/sgxprobes}
P="$T probe --tri pixpds:12 --width 64 --height 64 --vtx-coords 2 --pixels --slot pixel=$B/pix_pa0.bin --slot vtxuse=$B/vtx_coords.bin $B/texture-fetch-tex-fetch__0.bin"
h() { sudo -n $P 2>&1 | grep -vE "scratch at|scratch unchanged" | md5sum | cut -c1-8; }
printf "clear\n" | sudo -n tee "$D/kpoke" >/dev/null
base=$(h); base2=$(h); echo "baseline $base $base2"
one() { printf "clear\n%s\n" "$1" | sudo -n tee "$D/kpoke" >/dev/null
	r=$(sudo -n $P 2>&1 | grep -vE "scratch at|scratch unchanged")
	printf "clear\n" | sudo -n tee "$D/kpoke" >/dev/null
	m=$(echo "$r" | md5sum | cut -c1-8)
	[ "$m" != "$base" ] && echo "$1 CHANGED $(echo "$r" | grep -oE "o0 mixed.*|failed.*" | head -1 | cut -c1-90)"
}
one "rd:26^=0x1"
for b in 1 2 4; do one "rd:21^=$b"; done
for b in 0x1 0x100; do one "rd:51^=$b"; done
i=0; while [ $i -lt 32 ]; do one "rd:19^=$(printf 0x%x $((1 << i)))"; i=$((i + 1)); done
for i in 0 1 2 3 4 5 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23; do
	one "rd:22^=$(printf 0x%x $((1 << i)))"
done
for r in 26 21 51 19 22; do one "rd:$r=0"; one "rd:$r=0xffffffff"; done
echo done
)
echo "#### depth-scenes"
depth_scenes
echo "## exit $?"
echo "#### many-triangles"
many_triangles
echo "## exit $?"
echo "#### textured-triangle"
textured_triangle
echo "## exit $?"
