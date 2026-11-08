# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q045: what the fields of register 0x0740 (bits 17:9 and 8:0, which the TA kick of a first kick
# or of command flag 0x8 turns into a DPM store task and a load task when not zero) do. The GPU
# is reset, 0x0740 written through debugfs kregnow (it holds until the next reset), and the
# triangle rendered; after it the registers 0x0700-0x0750 (/dev/mem, the tool's --regs), TA3DCtl
# (debugfs buf09) dwords 20, 21 and 25, and for the partial renders (1024x768 on a PB of 0x23
# pages, --keep-going: the image loses macrotiles, E311) the non-zero dwords of the TA data's
# control, OTPM and state pages (0x4000, 0x5000 and 0x6000 of the render dump). Parts: A one
# context, 64x64, two renders, 0x0740 = 0 (control), 0x200, 0x400, 0x1000, 0x3fe00 (the 17:9
# field full), 0x1ff (8:0 full), 0x3ffff; B two contexts alternating (tri -n 2 --ctx2), the same
# values written before the first kick, and 0x0740 changed between the kicks with --kreg-render
# 2:... and --kreg-render2 1:...; C the partial renders, -n 1 and -n 2, 0, 0x200 and 0x3fe00 (the
# tool reports an overflowing scene as a failed job and dumps nothing); D the write beside 300
# renders. Two runs of each. render_pb_pages is put back at the end. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1119}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.19) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## installed module"; SRCV_FILE=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$SRCV_FILE"
echo "## loaded module"; SRCV_LOADED=$(sudo -n cat /sys/module/gma500_gfx/srcversion); echo "$SRCV_LOADED"
[ -n "$SRCV_FILE" ] && [ "$SRCV_FILE" = "$SRCV_LOADED" ] || { echo "the loaded module is not the installed one"; exit 1; }
echo "## tool"; sha256sum "$T"
echo "## clock"; date
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
pb() { sudo -n sh -c "echo $1 > $D/render_pb_pages"; }
W=$(mktemp -d)
trap 'pb 0x422; reset_gpu; rm -rf "$W"' EXIT
KEEP="^(job|diff|tri|tri2|regs|reg 0x07)|FAILED|failed|renders ok"
dw() { od -An -tx4 -v -j $((4 * $2)) -N 4 "$1" | tr -d ' '; }
pages() { # DUMP: the non-zero dwords of the control, OTPM and state pages
	for off in 0x4000 0x5000 0x6000; do
		echo "tadata $off: $(od -An -tx4 -v -j $((off)) -N 4096 "$1" | tr -s ' ' '\n' |
			awk 'NF { if ($1 != "00000000") printf "%#05x=%s ", 4 * (NR - 1), $1 }')"
	done
}
case_run() { # NAME PRE_WRITE ARGS...
	name=$1 pre=$2; shift 2
	echo "== $name: kregnow ${pre:-none}; tri $*"
	reset_gpu
	n=$(sudo -n dmesg | wc -l)
	[ -n "$pre" ] && echo "$pre" | sudo -n tee "$D/kregnow" >/dev/null
	mkdir -p "$W/$name"
	sudo -n timeout 120 "$T" tri --keep-going --wait-ms 8000 --regs 0x0700-0x0750 \
		--words "$W/$name" --dump-render "$W/$name" "$@" 2>&1 </dev/null |
		grep -E "$KEEP" | grep -v "us$" | cut -c1-170
	for k in 0 1 2; do
		f="$W/$name/ta3d.$k.bin"
		[ -f "$f" ] && echo "ta3d after render pair $k: dword20 0x$(dw $f 20) dword21 0x$(dw $f 21) dword25 0x$(dw $f 25)"
	done
	[ -f "$W/$name/tri.tadata.bin" ] && pages "$W/$name/tri.tadata.bin"
	sudo -n dmesg | tail -n +$((n + 1)) | grep -iE "kregnow|hang|reset|recover|timed out|fault|lost|cancel" |
		cut -c1-180 | head -6
}
pb 0x422
for i in 1 2; do
	for v in none 0x200 0x400 0x1000 0x3fe00 0x1ff 0x3ffff; do
		pre=; [ "$v" != none ] && pre="0x0740=$v"
		case_run "one-ctx-$v-$i" "$pre" -n 2
	done
done
for i in 1 2; do
	for v in none 0x200 0x3fe00 0x3ffff; do
		pre=; [ "$v" != none ] && pre="0x0740=$v"
		case_run "two-ctx-$v-$i" "$pre" -n 2 --ctx2
	done
	case_run "two-ctx-between-0x200-$i" "" -n 2 --ctx2 --kreg-render 1:0x0740=0x200 \
		--kreg-render2 1:0x0740=0x3fe00 --kreg-render 2:0x0740=0x1ff
	case_run "two-ctx-between-0x3fe00-first-$i" "" -n 2 --ctx2 --kreg-render2 1:0x0740=0x3fe00 \
		--kreg-render 2:0x0740=0
done
pb 0x23
for i in 1 2; do
	for v in none 0x200 0x3fe00; do
		pre=; [ "$v" != none ] && pre="0x0740=$v"
		case_run "partial-n1-$v-$i" "$pre" -n 1 --width 1024 --height 768
		case_run "partial-n2-$v-$i" "$pre" -n 2 --width 1024 --height 768
	done
done
# D: the write while renders run: tri -n 300 and, beside it, 0x0740 = 0x200 written 60 times 50 ms
# apart; the lines the kernel logs for the writes say what the register read right after each.
pb 0x422
for i in 1 2; do
	echo "== writer-during-renders-$i: tri -n 300 --keep-going with 60 writes of 0x0740=0x200"
	reset_gpu
	mark="task-fields-0740 writer $$ $i"
	echo "$mark" | sudo -n tee /dev/kmsg >/dev/null
	( for k in $(seq 1 60); do
		echo "0x0740=0x200" | sudo -n tee "$D/kregnow" >/dev/null
		sleep 0.05
	done ) &
	wr=$!
	sudo -n timeout 120 "$T" tri --keep-going --wait-ms 8000 -n 300 2>&1 </dev/null |
		grep -E "^(tri:|diff)|FAILED|failed|renders ok" | grep -v "us$" | cut -c1-170 | tail -3
	wait $wr
	sudo -n dmesg | sed -n "/$mark/,\$p" > "$W/log"
	echo "kregnow writes logged: $(grep -c 'kregnow 0x0740' "$W/log")"
	grep 'kregnow 0x0740' "$W/log" | sed 's/^.*kregnow/kregnow/' | sort | uniq -c
	echo "kregnow shows: $(sudo -n cat "$D/kregnow" | grep 0x0740)"
done
pb 0x422
echo "pb_pages: $(sudo -n cat "$D/render_pb_pages")"
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
