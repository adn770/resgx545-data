# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Q067, the flag-set cases of ctx-table-host-filled.sh in both orders of the two kernel pokes: the
# base (pb:4) at 16 scratch pages the tool maps, the flag word (pb:0 = 0x1) poked before or after
# it, over a zero-filled scratch (Z) and over the table the kernel builds before a job (K: entry i =
# ((i - 1) & 0xffff) << 16 | (i + 1), the last entry's next = 0xffff), three runs each; and the
# base alone over K and over zeros, three runs each, to recheck the flag-clear cases. debugfs
# alias_ctx_rw is set before each tri; 64x64 renders on contexts for 64x64. The tool reports the
# scratch dwords the job changed against the pre-fill. Root through sudo -n.
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
python3 - "$W/tableK.bin" <<'PY'
import struct, sys
n = 0x422
t = [0] + [(((i - 1) & 0xffff) << 16) | (i + 1 if i < n else 0xffff) for i in range(1, n + 1)]
open(sys.argv[1], "wb").write(struct.pack("<%dI" % len(t), *t))
PY
BASE="--scratch 16 --scratch-fill 0 --scratch-at $SC"
for i in 1 2 3; do
	case_run "flag-then-base-zero-$i" $BASE --kpoke-render 1:pb:0=0x1 --kpoke-render "1:pb:4=$SC"
	case_run "base-then-flag-zero-$i" $BASE --kpoke-render "1:pb:4=$SC" --kpoke-render 1:pb:0=0x1
	case_run "flag-then-base-K-$i" $BASE --scratch-file "$W/tableK.bin" --kpoke-render 1:pb:0=0x1 --kpoke-render "1:pb:4=$SC"
	case_run "base-then-flag-K-$i" $BASE --scratch-file "$W/tableK.bin" --kpoke-render "1:pb:4=$SC" --kpoke-render 1:pb:0=0x1
	case_run "base-only-K-$i" $BASE --scratch-file "$W/tableK.bin" --kpoke-render "1:pb:4=$SC"
	case_run "base-only-zero-$i" $BASE --kpoke-render "1:pb:4=$SC"
done
echo "alias_ctx_rw at the end: $(sudo -n cat "$D/alias_ctx_rw")"
echo "#### health"
reset_gpu
sudo -n "$T" fill 2>&1 | grep -E "^job|^diff"
sudo -n "$T" tri 2>&1 | grep -E "^diff|^tri 64x64 #1: [0-9]+ tri"
