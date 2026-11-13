# SPDX-License-Identifier: MIT
"""f2.py: stage f2 (r13-flag, Q046 sideband bit 11; closing13/plan/rank-round13.md section 2 "F2";
planned faults, user OK R13-3 a). E383's form (probes/pbe/sideband-channels.toml: probe --tri
pixel, the eot slot eot_plain, the pixel shader writing 0xc0804020, every pixel read back; the
programs are E383's published bins), sideband 0x0a00 | mode: bit 11 with E383's bit 9, in pack
modes 0, 4 and 8.

E383 ran bit 11 in modes 0 to 8, one job each, and every one faulted ("job faulted, context lost";
its kernel log keeps nine `BIF fault 0x91000 at 0x37001xxx` lines in run order, the table's order
0a00 to 0a08 [infer: the log has no per-case markers]: mode 0 at 0x3700103b, mode 4 at 0x37001003,
mode 8 at 0x37001013). This is exploration (the plan: no rule frozen beyond the faults), so the
rows are replicates whose new readings are the fault's status, address and page on B60AB0B4:

  H-E383       each bit-11 row faults (E383, 9 of 9)
  H-E383-PAGE  with BIF_INT_STAT 0x91000 at page 0x37001000 [infer: B60AB0B4 lays the heaps out
               as E383's module did]
  H-NOFAULT    the null: the row completes

Control that can fail, first: E383's bit-12 mode 0 job (0x1200, colour 0) under r13-tex sb12's
H-FIXED rule: it completes and at least 4055 of its 4096 pixels are words of E383's mode 0 set
(both kept runs). The three bit-11 rows are the stage's planned rows (expectfault, #limit 3); the
third is the stage's last row, so the count never stops the stage with a row left."""
import re

E383 = "data:pbe/sideband-channels"
EOT = f"{E383}/pbe-sideband-channels-0208/bins/eot_plain.bin"
COLOUR0 = f"{E383}/pbe-sideband-channels-0208/bins/pbe-sideband-channels-0208__0.bin"
BINS = {"eot_plain.bin": EOT, "sb-c0.bin": COLOUR0}
RAW12 = f"{E383}/pbe-sideband-channels-bit12-1200/raw.txt"
KLOG = f"{E383}/kernel.log"
ROW = re.compile(r"^probe (\S+): row (\d+): ([0-9a-fA-F ]+)$", re.M)
FAULT = re.compile(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+) ")
INSET_MIN = 4055
MODES = (0, 4, 8)
STAT, PAGE = "0x91000", "0x37001000"


def args(sideband):
    return (f'probe --tri pixel --pixels --slot eot="$S/bins/eot_plain.bin" --sideband '
            f'{sideband:#x} "$S/bins/sb-c0.bin"')


def mode0_words(blob):
    """E383's words of bit 12 in mode 0, both kept runs (every row of both images)."""
    rows = {}
    for m in ROW.finditer(blob(RAW12).decode()):
        rows.setdefault(m.group(1), {})[int(m.group(2))] = [int(t, 16) for t in m.group(3).split()]
    assert len(rows) == 2 and all(sorted(r) == list(range(64)) for r in rows.values())
    return sorted({v for r in rows.values() for y in r.values() for v in y})


def e383_faults(blob):
    """[(stat, address)] of E383's kernel log, in order (nine: modes 0 to 8 [infer])."""
    return FAULT.findall(blob(KLOG).decode())


def jobs(blob):
    """[(name, set, knobs, args, {quantity: {model: value}})] in run order."""
    out = [("f2-ctl", "control", "reads:pixels", args(0x1200),
            {"end": {"H-FIXED": "ok"}, "inset": {"H-FIXED": f">={INSET_MIN}"}})]
    for m in MODES:
        out.append((f"f2-b11-m{m}", "replicate", "expectfault", args(0x0A00 | m),
                    {"end": {"H-E383": "fault", "H-E383-PAGE": "fault", "H-NOFAULT": "ok"},
                     "fstat": {"H-E383-PAGE": STAT}, "fpage": {"H-E383-PAGE": PAGE}}))
    return out
