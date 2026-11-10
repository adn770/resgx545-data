#!/usr/bin/env python3
"""The offline models of R2-pixel: the Q281 layout model against S1b's measured images and S1's fault, the xor variant
program (exactly one changed instruction), the Q286 layout numbers against the S3 a4 run and E727's pair table.
Prints ok/FAIL; exit 1 on any FAIL."""
import sys
sys.dont_write_bytecode = True

import gzip  # noqa: E402
import os  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402
import struct  # noqa: E402

R2 = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R2 / "gen"))
sys.path.insert(0, str(R2 / "score"))
import r2lib as L  # noqa: E402
import r2models as M  # noqa: E402

FX = R2 / "tests" / "fixtures"
ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def rows(path):
    return L.probe_rows(gzip.open(path).read().decode())


for p in (19, 20, 21):
    check(f"HL image at {p} pages = S1b's measured image", rows(FX / "s1b-p-d" / f"d-L2e2-{p}.txt.gz") == M.image(p))
check("18 pages: every word is the sentinel 0xdeadbeef (the probe's 'no pixel written')", set(M.image(18)) == {0xDEADBEEF})
check("18 pages with the xor: every word 0xdeadbeee (not the sentinel: the probe would write a pixel)", set(M.image(18, 1)) == {0xDEADBEEE})
check("19 pages: the coords words (y << 16 | x) from y = 16; 20 pages from y = 0",
      M.image(19)[0] == 0x00100000 and M.image(20)[0] == 0x00000000 and M.image(21)[0] == 0xD0005000)
check("17 and 16 pages: the first read is unmapped, at 0x3e017001 (E722's fault address)",
      M.image(17) is None and M.image(16) is None and M.first_fault(17) == M.first_fault(16) == 0x3E017001)
d16 = gzip.open(FX / "s1-p-d" / "d-L2e2-16.dmesg.gz").read().decode()
check("S1's kept d-L2e2-16 kernel log has BIF fault 0x90002 at 0x3e017001", L.bif_fault(d16) == ("0x90002", 0x3E017001))
check("the 19-page image XOR 1 differs from the 19-page image in every word", all(a ^ b == 1 for a, b in zip(M.image(19), M.image(19, 1))))
check("the layout is monotone: a word is scratch, coords texel, sentinel or fault by its offset (1024 dwords a page)",
      [M.layout_word(20480, p) for p in (21, 20, 19, 18)] == [0xD0005000, 0, 0x00100000, 0xDEADBEEF]
      and M.layout_word(20480, 17) == ("fault", 0x3E017001))
# ---- the staged programs: the variant is the base with one instruction changed --------------------------------
base = (R2 / "bins/s1d-tw64x64-l2e2__0.bin").read_bytes()
var = (R2 / "bins/s1d-tw64x64-l2e2-x1__0.bin").read_bytes()
check("the variant program has the base's length", len(base) == len(var) and len(base) % 8 == 0, f"{len(base)} bytes")
diff = [i // 8 for i in range(0, len(base), 8) if base[i:i + 8] != var[i:i + 8]]
check("exactly one 8-byte instruction differs, the last", diff == [len(base) // 8 - 1], str(diff))
w = struct.unpack("<Q", var[-8:])[0]
check("the changed word is `xor.skipinv.end o0, r10, #1` as the assembler encodes it (0x5885100120000501)", w == 0x5885100120000501, hex(w))
tx = (R2 / "templates/tx_map.s").read_text(), (R2 / "templates/tx_map_x1.s").read_text()
check("tx_map_x1.s is tx_map.s with only the last line changed",
      [a for a, b in zip(tx[0].splitlines(), tx[1].splitlines()) if a != b] == ["mov.skipinv.end o0, r10"]
      and len(tx[0].splitlines()) == len(tx[1].splitlines()))
landed = pathlib.Path.home() / "src/resgx545/probes/texture/templates/tx_map.s"
check("the frozen template copy is the landed tx_map.s", landed.read_text() == tx[0])
check("the staged base programs are S1b's frozen binaries (the faulting/completing ones)",
      (R2 / "bins/s1d-tw64x64-l2e2__0.bin").read_bytes() == (pathlib.Path.home() / "src/scratch/resgx545/closing/s1b-v2/bins/s1d-tw64x64-l2e2__0.bin").read_bytes()
      and (R2 / "bins/s1d-tw128x32-l0e2__0.bin").read_bytes() == (pathlib.Path.home() / "src/scratch/resgx545/closing/s1b-v2/bins/s1d-tw128x32-l0e2__0.bin").read_bytes())
# ---- Q286 -----------------------------------------------------------------------------------------------
check("layout 320x400 (n 2): rgn 0x4000, rgn_size 0x1800, size 0x8000; in 544x400: size 0xa000",
      (lambda a, b: (a["rgn"], a["rgn_size"], a["size"], b["size"]) == (0x4000, 0x1800, 0x8000, 0xa000))(L.layout(320, 400), L.layout(544, 400)))
check("boundary-exact: four arrays end at 0xa000 = the TA data size; a fifth would fault at page 0x2000a",
      L.fault_page_if(4, (320, 400), (544, 400)) is None and L.fault_page_if(5, (320, 400), (544, 400)) == 0x2000a)
check("a6: four arrays in a 320x400 context fault at page 0x20008", L.fault_page_if(4, (320, 400), (320, 400)) == 0x20008)
check("slack pair 288x656 in 544x656: rgn 0x7000, rgn_size 0x2400, size 0x11000; four arrays end at 0x10000, five at 0x12400",
      (lambda t, m: (t["rgn"], t["rgn_size"], m["size"], m["rgn"] + 4 * t["rgn_size"], m["rgn"] + 5 * t["rgn_size"]) == (0x7000, 0x2400, 0x11000, 0x10000, 0x12400))(L.layout(288, 656), L.layout(544, 656)))
check("slack pair: one page of slack (four arrays fit, five fault at page 0x20011); the control faults at 0x2000d",
      L.fault_page_if(4, (288, 656), (544, 656)) is None and L.fault_page_if(5, (288, 656), (544, 656)) == 0x20011
      and L.fault_page_if(4, (288, 656), (288, 656)) == 0x2000d)
a4 = L.read_bytes(str(FX / "s3-a4" / "a4-ctl-320x400-te20.tri.tadata.bin.gz"))
lay = L.layout(320, 400)
s, below = L.tadata_slots(a4, lay["rgn"], lay["rgn_size"])
check("S3's kept a4 TA data: 0xa000 bytes, one array written from 0x4000, nothing below 0x4000 or from 0x5800", len(a4) == 0xa000 and s[0] > 0 and sum(s[1:]) == 0 and below == 0, f"{s} below {below}")
a4out = L.read_text(str(FX / "s3-a4" / "a4-ctl-320x400-te20.txt.gz"))
m = re.search(r"^diff: (\d+) of (\d+) pixels, first \((\d+), (\d+)\)", a4out, re.M)
check("S3's kept a4 output: diff 28 of 128000, first (304, 128), echo 544x400", m and m.groups() == ("28", "128000", "304", "128") and "targets up to 544x400" in a4out)
print("ALL OK" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
