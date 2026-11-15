#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r23-pk's generator (round 22's plan, closing22/plan/rank-round22.md sections 2.1,
2.2 and 6, R22-2 a, R22-4 a). Writes tables/STAGE.txt, predictions/STAGE.tsv and the programs
bins/NAME.bin (+ bins/NAME.s for the ones this session writes), every input read at the commits
session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Stages, in run order:
  pk     the poke echo of t22 (R22-4 a): one repeat each of E391 (attribute-room case 0), E125
         (douta secattr-rows-4 case 0) and E568 (fy-28-p0-csc), each a control reading its
         `probe NAME: poked ...` echo, and an unpoked control (no echo line); gates q019, q181
  q019   E391's 40 jobs on t22 (Q019): fit 0, 1, 4 rows, held out 2, 8 rows; H-E391 frozen,
         H-ROWS fitted by the scorer on the fit rows (hash printed) before the held out are read
  q181   E568's YUV fills (fy-28/29 p0 csc and nocsc, p1 csc) and two E037 copies (Q181)
  q123   placed programs of up to 8192 words (Q123): the in-step controls first, an exe18 start
         at bit 16, then crossings of the 0x80000 step (bit 16 of the index); on_stop end
  q123h  crossings of index bit 17 (exe18 at 0xffe00), gated on q123 (controls passed, every
         bit-16 crossing carried, the exe18 start honoured): every landing is then mapped
Inputs: RESGX545_DATA, RESGX545_MAIN (tools/usse-asm: probe.py's render and the assemblers)."""
import os
import pathlib
import sys
import tempfile
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import pins  # noqa: E402
from q123 import (Q123, PHAS, code_index, heap_base_prog, placed,  # noqa: E402,F401
                  q123_models)

sys.path.insert(0, os.path.join(pins.MAIN, "tools", "usse-asm"))
import probe as P  # noqa: E402

TOOL = "t22"
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("pk", "q019", "q181", "q123", "q123h")

# ---- pinned inputs ----------------------------------------------------------------------------
AR = "data:pds/attribute-room/pds-attribute-room-rows/bins/"
DO = "data:followup/pds/douta/pds-douta-secattr-rows-4/bins/"
AR_TOML = "resgx545:probes/pds/attribute-room.toml"
DO_TOML = "resgx545:probes/pds/douta.toml"
YUV_TOML = {"csc": "resgx545:probes/texture/tx-formats-yuv-csc.toml",
            "nocsc": "resgx545:probes/texture/tx-formats-yuv-nocsc.toml"}
YUV_TPL = "resgx545:probes/texture/templates/tx_map.s"
YUV_PRED = "resgx545:tools/texture/p1132/predictions-declared.tsv"
PDS_N = 36          # douta_words.s's data dwords (probe.py pds_data on both tables)
ROWS = {0x30000: 0, 0x70000: 1, 0xb0000: 2, 0x130000: 4, 0x230000: 8}
FIT_ROWS, HELD_ROWS = (0, 1, 4), (2, 8)

# E037 (texture-tpu-csc): the UYVY copy, set 0 loaded with the BT.601 words, and not loaded
UYVY = "--poke tex:1=0x7d03f01f --poke tex:0^=0x90"
CSC0 = ("--poke xfer:17^=0x1 --poke xfer:18=0x00950095 --poke xfer:19=0x00000095 "
        "--poke xfer:20=0x010203ce --poke xfer:21=0x039800cc --poke xfer:22=0")
E037_CSC, E037_BLACK = "0xb6067a95fa98de2d", "0xd3522437a14b6325"
BLACK_SHA = "e3a911a400487825d8d19475cac4c31d8146d8662e054851c42cfe4282b308d4"  # 2048 x ff000000

# ---- helpers ------------------------------------------------------------------------------------
def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def asm(text, isa="usse"):
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "x.bin"
        P._assemble(text, f, isa)
        return f.read_bytes()


def probe_row(name, st, knobs, args):
    return f"{name}|{st}|safe|{knobs}|{TOOL}|probe {args}"


def ar_cases():
    """attribute-room's 40 cases: (index, run, rows, first attribute, bg:1)."""
    d = tomllib.loads(pins.blob(AR_TOML).decode())["probe"][0]
    out = []
    for i, (case, cs) in enumerate(zip(d["cases"], d["case_set"])):
        (poke,) = cs["pokes"]
        bg = int(poke.split("=")[1], 16)
        lo = case[16] >> 8                        # C0: the first attribute's index
        out.append((i, 1 + i // 20, ROWS[bg], lo, poke))
    return out


def ar_markers(i):
    d = tomllib.loads(pins.blob(AR_TOML).decode())["probe"][0]
    return d["cases"][i][:16]


def do_markers(i):
    d = [p for p in tomllib.loads(pins.blob(DO_TOML).decode())["probe"]
         if p["name"] == "pds-douta-secattr-rows-4"][0]
    return d["cases"][i][:16], d["case_set"][i]["pokes"][0]


def yuv_bins():
    """{label: bytes} of tx-formats-yuv-csc's four cases (nocsc's are the same programs)."""
    tpl = pins.blob(YUV_TPL).decode()
    out = {}
    for kind, pin in YUV_TOML.items():
        pd = tomllib.loads(pins.blob(pin).decode())["probe"][0]
        p = P._probe(pd, pathlib.Path(pin).name)
        for label, case in zip(pd["labels"], p.cases):
            out[label] = asm(P.render(p, case, tpl))
        assert P.tool_args(p) == (["--temps", "32", "--coords", "--pixels"] +
                                  ([a for k in pd.get("pokes", []) for a in ("--poke", k)]))
    return out


def yuv_declared():
    out = {}
    for ln in pins.blob(YUV_PRED).decode().splitlines():
        f = ln.split("\t")
        if len(f) >= 5 and f[0] == "tx-formats" and f[1].startswith("fy-"):
            out[f[1]] = f[4]
    return out


def markers_value(ms):
    return ",".join(f"{m:08x}" for m in ms)


# ---- stages -------------------------------------------------------------------------------------
def pk(files):
    rows, pred = [], [HEAD]
    files["bins/sa64_dump.bin"] = pins.blob(AR + "sa64_dump.bin")
    files["bins/sa_dump.bin"] = pins.blob(DO + "sa_dump.bin")
    ar0 = pins.blob(AR + "pds-attribute-room-rows__0.bin")
    files["bins/pk-e391.bin"] = ar0
    files["bins/pk-none.bin"] = ar0
    files["bins/pk-e125.bin"] = pins.blob(DO + "pds-douta-secattr-rows-4__0.bin")
    ms, poke = do_markers(0)
    _, _, _, _, ar_poke = ar_cases()[0]
    use64 = f'--temps 32 --pds {PDS_N} --use "$S/bins/sa64_dump.bin"'
    use16 = f'--temps 32 --pds {PDS_N} --use "$S/bins/sa_dump.bin"'
    rows.append(probe_row("pk-e391", "control", "reads:echo", f'{use64} --poke {ar_poke} '
                          '"$S/bins/pk-e391.bin"'))
    rows.append(probe_row("pk-e125", "control", "reads:echo", f'{use16} --poke {poke} '
                          '"$S/bins/pk-e125.bin"'))
    rows.append(probe_row("pk-e568", "control", "reads:echo", f'--temps 32 --coords --pixels '
                          f'{CSC0} "$S/bins/pk-e568.bin"'))
    rows.append(probe_row("pk-none", "control", "reads:echo", f'{use64} "$S/bins/pk-none.bin"'))
    files["bins/pk-e568.bin"] = yuv_bins()["fy-28-p0-csc"]
    src = "rank-round22.md 2.1, R22-4 a; t22's usage (sgxfive-test.c at 3c68e8d)"
    pred.append(line("pk-e391", "echo", "bg:1=0x00030000", "H-ECHO", "control", src))
    pred.append(line("pk-e125", "echo", "bg:1=0x00130000", "H-ECHO", "control", src))
    pred.append(line("pk-e568", "echo", "xfer:17^=0x1,xfer:18=0x00950095,xfer:19=0x00000095,"
                     "xfer:20=0x010203ce,xfer:21=0x039800cc,xfer:22=0x00000000", "H-ECHO",
                     "control", src))
    pred.append(line("pk-none", "echo", "-", "H-ECHO", "control", src + "; no poke, no echo"))
    # the records the repeats stand for (R22-4 a: a correction only if they differ)
    pred.append(line("pk-e391", "own", markers_value(ar_markers(0)), "H-E391", "control",
                     "E391 run 1, 0 rows, attributes 0-15: sa0-sa15 its markers"))
    pred.append(line("pk-e125", "own", markers_value(ms), "H-E125", "control",
                     "E125 rows 4, markers A: sa0-sa15 its markers"))
    pred.append(line("pk-e568", "pixsha", BLACK_SHA, "H-NOLOAD", "control",
                     "E568: fy-28-p0-csc read 0xff000000 at all 2048 pixels"))
    pred.append(line("pk-e568", "pixsha", yuv_declared()["fy-28-p0-csc"], "H-LOAD", "control",
                     "E568's declared E037 conversion (tools/texture/p1132/predictions-declared.tsv)"))
    return rows, pred


def q019(files):
    rows, pred = [], [HEAD]
    for i, run, nrows, lo, poke in ar_cases():
        name = f"q019-{run}-r{nrows}-a{lo:02d}"
        st = "fit" if nrows in FIT_ROWS else "heldout"
        files[f"bins/{name}.bin"] = pins.blob(AR + f"pds-attribute-room-rows__{i}.bin")
        rows.append(probe_row(name, st, "-", f'--temps 32 --pds {PDS_N} --use '
                              f'"$S/bins/sa64_dump.bin" --poke {poke} "$S/bins/{name}.bin"'))
        bg = poke.split("=")[1]
        pred.append(line(name, "echo", f"bg:1=0x{int(bg, 16):08x}", "H-ECHO", st,
                         "rank-round22.md 2.1: every poke row reads its echo"))
        # H-E391: attributes 0-31 at their own sa, 32-63 in none of the shown sa0-sa31
        own = 16 if lo < 32 else 0
        pred.append(line(name, "own", own, "H-E391", st,
                         f"E391: markers of attributes {lo}-{lo + 15} in sa{lo}-sa{lo + 15}"
                         if lo < 32 else f"E391: no marker of attributes {lo}-{lo + 15} in "
                         "sa0-sa31"))
        pred.append(line(name, "stray", 0, "H-E391", st,
                         "E391: no marker of this job anywhere else in sa0-sa31"))
        pred.append(line(name, "own", f"fit:{lo}", "H-ROWS", st,
                         "rank-round22.md 2.1: fitted on 0, 1, 4 rows by the scorer (rule hash "
                         "printed first), monotone in rows at 2 and 8"))
    return rows, pred


def q181(files):
    rows, pred = [], [HEAD]
    bins, decl = yuv_bins(), yuv_declared()
    copy = "copy --every-value --pixels"
    rows.append(f"c-copy-csc|control|safe|expectdiff reads:hash|{TOOL}|{copy} {UYVY} {CSC0}")
    rows.append(f"c-copy-none|control|safe|expectdiff reads:hash|{TOOL}|{copy} {UYVY}")
    pred.append(line("c-copy-csc", "hash", E037_CSC, "H-E037", "control",
                     "E037: the UYVY copy with set 0 loaded (BT.601)"))
    pred.append(line("c-copy-none", "hash", E037_BLACK, "H-E037", "control",
                     "E037: the UYVY copy with the load flag clear (black)"))
    for name, st in (("fy-28-p0-csc", "fit"), ("fy-29-p0-csc", "fit"),
                     ("fy-28-p0-nocsc", "fit"), ("fy-29-p0-nocsc", "fit"),
                     ("fy-28-p1-csc", "heldout"), ("fy-29-p1-csc", "heldout")):
        files[f"bins/{name}.bin"] = bins[name.replace("-nocsc", "-csc")]
        csc = name.endswith("-csc")
        rows.append(probe_row(name, st, "-", "--temps 32 --coords --pixels " +
                              (CSC0 + " " if csc else "") + f'"$S/bins/{name}.bin"'))
        if csc:
            pred.append(line(name, "echo", "xfer:17^=0x1,xfer:18=0x00950095,xfer:19=0x00000095,"
                             "xfer:20=0x010203ce,xfer:21=0x039800cc,xfer:22=0x00000000",
                             "H-ECHO", st, "rank-round22.md 2.1"))
            pred.append(line(name, "pixsha", decl[name], "H-LOAD", st,
                             "E568's declared E037 conversion (predictions-declared.tsv)"))
        pred.append(line(name, "pixsha", BLACK_SHA, "H-NOLOAD", st,
                         "E568: opaque black at all 2048 pixels, with and without the poke"))
    return rows, pred


def q123(files, stage):
    rows, pred = [], [HEAD]
    if stage == "q123":
        files["bins/q123-base.s"] = ("\n".join(heap_base_prog()) + "\n").encode()
        files["bins/q123-base.bin"] = asm(files["bins/q123-base.s"].decode())
    for name, stg, st, form, off, kind, n, t in Q123:
        if stg != stage:
            continue
        idx0 = code_index(off, form)
        text = "\n".join(placed(kind, n, t, idx0)) + "\n"
        files[f"bins/{name}.s"] = text.encode()
        files[f"bins/{name}.bin"] = asm(text)
        models = q123_models(off, form, kind, n, t, 17 if stage == "q123h" else 16)
        ctl = st == "control"
        want = models.get("H-CARRY18")
        knobs = f"reads:o0,placed o0:{want:08x}" if ctl else "-"
        rows.append(probe_row(name, st, knobs, f'--temps 32 --place 0x{off:x}="$S/bins/{name}.bin" '
                              f'--place-form {form} "$S/bins/q123-base.bin"'))
        for m, v in models.items():
            pred.append(line(name, "o0", "-" if v is None else f"0x{v:08x}", m, st,
                             f"rank-round22.md 2.2; {kind} at 0x{off:x} ({form}), {n} words, "
                             f"target word {t} (index 0x{idx0 + t:x})"))
        pred.append(line(name, "placed", f"{n}/{n}", "H-PLACED", st,
                         "t22: placed words read back as built"))
    return rows, pred


HEADERS = {
    "pk": """#stage pk
#limit 0
# pk (R22-4 a, rank-round22.md 2.1): t22's poke echo. One repeat each of E391 (attribute-room case 0: 0 rows, attributes
# 0-15), E125 (douta secattr-rows-4 case 0: 4 rows, markers A) and E568 (fy-28-p0-csc), each a control whose reading is
# its `probe NAME: poked SPACE:N 0xOLD -> 0xNEW` lines (H-ECHO: every poke echoed, the sent word the poke's), and pk-none
# (E391's program unpoked: no echo line). Each repeat is also scored against its record (H-E391, H-E125, H-NOLOAD /
# H-LOAD). Stop: a poke row whose echo count is not its poke count (run/hooks.sh), any fault or hang; on_stop end.""",
    "q019": """#stage q019
#limit 0
# q019 (Q019, rank-round22.md 2.1): E391's 40 jobs on t22 (data pds/attribute-room bins, sa64_dump.bin), bg:1 at 0, 1,
# 2, 4, 8 rows, attributes 0-15/16-31/32-47/48-63, two runs. Frozen H-E391 (attributes 0-31 at their own sa, 32-63 in
# none of sa0-sa31: the tool prints 32 scratch dwords). Fit 0, 1, 4 rows, held out 2, 8: H-ROWS is fitted by the scorer
# on the fit rows (its rule's hash printed before any held-out row is read). Gate: pk's controls. Stop: a poke row
# without its echo (run/hooks.sh), any fault or hang.""",
    "q181": """#stage q181
#limit 0
# q181 (Q181, rank-round22.md 2.1): E568's YUV fills on t22 with the echo (fy-28/29 p0 csc and nocsc, p1 csc held out)
# and E037's copy as the copy control (set 0 loaded: 0xb6067a95fa98de2d; not loaded: black). Frozen per fill H-NOLOAD
# (E568's black) against H-LOAD (E568's declared E037 conversion). Gate: pk's controls. Stop: a poke row without its
# echo, any fault or hang.""",
    "q123": """#stage q123
#limit 0
# q123 (Q123, rank-round22.md 2.2, R22-2 a): placed programs of up to 8192 words, every word not in the program a pad that
# ends the task with its own word number (0xb0000000 | k), the probe's own program at the heap base 256 pads
# (0xc0de0000 | k): every landing is mapped and names itself. The in-step controls first (0x40000, 600 words: a run and a
# lapc to word 590), then the exe18 start at 0x80040 (H-EXE18 against H-EXE16), then the bit-16 crossings at 0x7fe00 and
# 0x78000 (8192 words): H-CARRY18 against H-WRAP. Stop: a control off its frozen o0, placed words not read back as built,
# any fault or hang (on_stop end).""",
    "q123h": """#stage q123h
#limit 0
# q123h (Q123, rank-round22.md 2.2): index bit 17, exe18 at 0xffe00 (index 0x1ffc0, the step at word 64): a run, a ba and
# a lapc. Gate (score.py gate): q123's controls passed, every bit-16 crossing carried and the exe18 start was honoured, so
# the only landings left are 0x100000 (H-CARRY18) or the heap base (a 17-bit wrap), both mapped. Stop: any fault or hang.""",
}


def build():
    files = {}
    stages = {"pk": pk(files), "q019": q019(files), "q181": q181(files),
              "q123": q123(files, "q123"), "q123h": q123(files, "q123h")}
    for st in ORDER:
        rows, pred = stages[st]
        files[f"tables/{st}.txt"] = (HEADERS[st] + "\n" + "\n".join(rows) + "\n").encode()
        files[f"predictions/{st}.tsv"] = "".join(pred).encode()
    return files


def main(argv):
    files = build()
    if "--check" in argv:
        bad = [p for p, b in files.items()
               if not os.path.exists(os.path.join(KP, p)) or open(os.path.join(KP, p), "rb").read() != b]
        for p in bad:
            print(f"stale: {p}")
        return 1 if bad else 0
    for p, b in files.items():
        f = os.path.join(KP, p)
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, "wb") as fh:
            fh.write(b)
    print(f"wrote {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
