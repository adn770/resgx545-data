# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# Stolen memory and GTT sizes: configuration space and one register, read only. 00:02.0 is the
# graphics device (BSM, the base of stolen memory, at 0x5c; GMCH_CTRL at 0x52), 00:00.0 the host
# bridge (whose graphics control word, GGC, other Intel parts keep at 0x50 or 0x52).
set -u
echo "## uname"; uname -r
for dev in 00:02.0 00:00.0; do
	echo "## lspci $dev"
	sudo -n lspci -s "$dev" -vvv
	echo "## config space $dev, first 256 bytes"
	sudo -n lspci -s "$dev" -xxx
done
echo "## BSM (00:02.0 offset 0x5c)"
sudo -n setpci -s 00:02.0 5c.l
echo "## GMCH_CTRL (00:02.0 offset 0x52)"
sudo -n setpci -s 00:02.0 52.w
echo "## GGC (00:00.0 offset 0x52)"
sudo -n setpci -s 00:00.0 52.w
echo "## GGC (00:00.0 offset 0x50)"
sudo -n setpci -s 00:00.0 50.w
echo "## graphics device resources"
sudo -n lspci -s 00:02.0 -v | grep -iE "memory at|i/o ports|prefetchable"
# gma500 takes the GTT's physical start from PGETBL_CTL (MMIO 0x2020 of region 0) and the
# stolen memory as BSM up to it, less one page.
echo "## PGETBL_CTL (region 0 + 0x2020)"
bar=$(sudo -n setpci -s 00:02.0 10.l)
sudo -n python3 -c "
import mmap, os, struct
fd = os.open('/dev/mem', os.O_RDONLY | os.O_SYNC)
m = mmap.mmap(fd, 4096, mmap.MAP_SHARED, mmap.PROT_READ, offset=(0x$bar & ~0xf) + 0x2000)
print(hex(struct.unpack_from('<I', m, 0x20)[0]))
"
echo "## the driver's own view"
sudo -n dmesg | grep -F "gma500 0000:00:02.0" | head -n 40
for f in /sys/class/drm/card0/device/resource /sys/kernel/debug/dri/0/gtt_mm; do
	if sudo -n test -e "$f"; then echo "## has $f"; sudo -n cat "$f"; else echo "## lacks $f"; fi
done
sudo -n sh -c 'ls /sys/kernel/debug/dri/*/' 2>/dev/null | head -n 60
