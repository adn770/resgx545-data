# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q067, the control of E446 with a table the host filled: debugfs alias_ctx_rw is set before each
# tri below; 64x64 renders on contexts for 64x64, as in ctx-page-writable-control.sh. The
# descriptor's page-table base (pb:4) points at 16 scratch pages the tool maps and pre-fills
# (--scratch-file) with a table, and the flag word is left as the kernel sets it (bit 0 clear):
#   A  no poke, once: the table as the render leaves it (dump offset 0x422000, 0x423 dwords)
#   H  the scratch pre-filled with A's table (the values E446's case C leaves in the scratch,
#      entry 0 = 0, entry 1 = 0x04220002), three runs
#   K  the scratch pre-filled with the table the kernel builds before a job (entry i, 1 to 0x422,
#      = ((i - 1) & 0xffff) << 16 | (i + 1), the last entry's next = 0xffff: E309's layout;
#      the first entries ffff0002 00010003 00020004 are the ones E446 read), three runs
#   Z  the scratch pre-filled with 0 (E446's F), once
#   C  flag bit 0 set (1:pb:0=0x1) over the pre-filled table H, once; and over the zero fill, once
# The tool reports the scratch dwords the job changed against the pre-fill; each case's
# parameter dump is compared with A's. Root through sudo -n.
set -u
T=${SGXFIVE_TEST:-$HOME/sgxfive-test-1118}
D=$(sudo -n sh -c 'ls -d /sys/kernel/debug/dri/*/sgx' | head -n 1)
[ -x "$T" ] || { echo "no $T: build userspace/libsgxfive (11.18) for the laptop first"; exit 1; }
echo "## uname"; uname -r
echo "## firmware"; sha256sum /lib/firmware/sgx545_ukernel.fw
echo "## installed module"; INST=$(modinfo -F srcversion gma500_gfx 2>/dev/null); echo "$INST"
echo "## loaded module"; LOAD=$(sudo -n cat /sys/module/gma500_gfx/srcversion); echo "$LOAD"
[ -n "$INST" ] && [ "$INST" = "$LOAD" ] || { echo "the loaded module is not the installed one"; exit 1; }
echo "## tool"; sha256sum "$T"
echo "## clock"; date
reset_gpu() { echo 1 | sudo -n tee "$D/reset" >/dev/null; sleep 1; }
W=$(mktemp -d)
trap 'echo N | sudo -n tee "$D/alias_ctx_rw" >/dev/null; reset_gpu; rm -rf "$W"' EXIT
KEEP="^(job|diff|tri|scratch|layout|kpoke)|failed|dword|page"
SC=$(sudo -n "$T" tri --scratch 16 2>&1 | sed -n 's/^scratch: \(0x[0-9a-f]*\) .*/\1/p' | head -n 1)
[ -n "$SC" ] || { echo "no scratch address"; exit 1; }
# 1 MiB above where the heap's allocator put it: clear of the colour buffer it hands out later
SC=$(printf '0x%x' $(( SC + 0x100000 )))
echo "scratch address: $SC"
case_run() { # NAME ARGS...
	name=$1; shift
	echo "== $name (alias_ctx_rw Y)"
	reset_gpu
	echo Y | sudo -n tee "$D/alias_ctx_rw" >/dev/null
	n=$(sudo -n dmesg | wc -l)
	mkdir -p "$W/$name"
	sudo -n "$T" tri --wait-ms 8000 --dump-render "$W/$name" "$@" 2>&1 | grep -E "$KEEP" | head -n 40
	echo "kernel: $(sudo -n dmesg | tail -n +$((n + 1)) | grep -iE 'fault|alias|kpoke|recover' | sed 's/^\[[ 0-9.]*\] //' | head -n 4 | tr '\n' ';')"
	echo "bif: int $(sudo -n cat "$D/regs" | awk '$1 == "reg" && $2 == "0x0c04" { print $3 }') fault $(sudo -n cat "$D/regs" | awk '$1 == "reg" && $2 == "0x0c08" { print $3 }')"
	if [ -f "$W/A1/tri.param.bin" ] && [ -f "$W/$name/tri.param.bin" ]; then
		echo "param vs A1: $(cmp -l "$W/A1/tri.param.bin" "$W/$name/tri.param.bin" 2>&1 | wc -l) bytes differ"
		echo "page table (dump offset 0x422000), entries 0-3 and 1057-1060: $(od -An -tx4 -v -j $((0x422000)) -N 16 "$W/$name/tri.param.bin" | tr -s ' ') / $(od -An -tx4 -v -j $((0x422000 + 4 * 1057)) -N 16 "$W/$name/tri.param.bin" | tr -s ' ')"
	fi
	echo N | sudo -n tee "$D/alias_ctx_rw" >/dev/null
}
case_run A1
dd if="$W/A1/tri.param.bin" of="$W/tableH.bin" bs=4 skip=$((0x422000 / 4)) count=$((0x423)) 2>/dev/null
echo "table H: $(wc -c < "$W/tableH.bin") bytes, first dwords $(od -An -tx4 -v -N 16 "$W/tableH.bin" | tr -s ' ')"
python3 - "$W/tableK.bin" <<'PY'
import struct, sys
n = 0x422
t = [0] + [(((i - 1) & 0xffff) << 16) | (i + 1 if i < n else 0xffff) for i in range(1, n + 1)]
open(sys.argv[1], "wb").write(struct.pack("<%dI" % len(t), *t))
PY
echo "table K: $(wc -c < "$W/tableK.bin") bytes, first dwords $(od -An -tx4 -v -N 16 "$W/tableK.bin" | tr -s ' ')"
ARGS="--scratch 16 --scratch-fill 0 --scratch-at $SC --kpoke-render 1:pb:4=$SC"
for i in 1 2 3; do case_run H$i $ARGS --scratch-file "$W/tableH.bin"; done
for i in 1 2 3; do case_run K$i $ARGS --scratch-file "$W/tableK.bin"; done
case_run Z1 $ARGS
case_run CH1 $ARGS --scratch-file "$W/tableH.bin" --kpoke-render 1:pb:0=0x1
case_run CZ1 $ARGS --kpoke-render 1:pb:0=0x1
echo "alias_ctx_rw at the end: $(sudo -n cat "$D/alias_ctx_rw")"
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
