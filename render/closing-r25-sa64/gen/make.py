#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r25-sa64's generator (round 24's plan, closing24/plan/rank-round24.md sections 2.1
and 5, closing24/DECISIONS-R24.md R24-1 a, R24-3 a). Writes tables/STAGE.txt,
predictions/STAGE.tsv and the programs bins/NAME.bin, every input read at the commits
session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now

Stages, in run order:
  pk64   E1096's pk-e391 and pk-e125 rows on t24 with `--scratch-show 64`: controls on the echo,
         on sa0-sa15 (their markers, as E1096 read them) and on the print (pk-e391: 64 scratch
         lines, no `more changed` line); gates q019; on_stop end
  q019   E391's 40 jobs (programs and pokes byte for byte, `--scratch-show 64`), then 16 held-out
         jobs at 3 and 6 rows (E391's attribute sets and runs, programs rendered from E391's own
         table with the size in the marker); frozen H-E391 (sa0-sa31 as E1096), H-ALL64, H-NONE,
         H-ROWS (fit 0, 1, 4 rows; held out 2, 3, 6, 8)
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

sys.path.insert(0, os.path.join(pins.MAIN, "tools", "usse-asm"))
import probe as P  # noqa: E402

TOOL = "t24"
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("pk64", "q019")

# ---- pinned inputs ----------------------------------------------------------------------------
AR = "data:pds/attribute-room/pds-attribute-room-rows/bins/"
DO = "data:followup/pds/douta/pds-douta-secattr-rows-4/bins/"
AR_TOML = "resgx545:probes/pds/attribute-room.toml"
DO_TOML = "resgx545:probes/pds/douta.toml"
DOUTA_TPL = "resgx545:probes/pds/templates/douta_words.s"
PDS_N = 36          # douta_words.s's data dwords (probe.py pds_data)
SHOW = 64           # --scratch-show: sa64_dump.s stores sa0-sa63 to scratch dwords 0-63


def bg1(rows):
    """bg:1 at a secondary attribute size of ROWS rows (attribute-room.toml: bits 24:18)."""
    return 0x30000 | rows << 18


ROWS = {bg1(r): r for r in (0, 1, 2, 3, 4, 6, 8)}
FIT_ROWS, HELD_ROWS, NEW_ROWS = (0, 1, 4), (2, 3, 6, 8), (3, 6)
SETS = (0, 16, 32, 48)


# ---- helpers ------------------------------------------------------------------------------------
def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def asm(text, isa):
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "x.bin"
        P._assemble(text, f, isa)
        return f.read_bytes()


def probe_row(name, st, knobs, args):
    return f"{name}|{st}|safe|{knobs}|{TOOL}|probe {args}"


def ar_probe():
    return tomllib.loads(pins.blob(AR_TOML).decode())["probe"][0]


def ar_cases():
    """attribute-room's 40 cases: (index, run, rows, first attribute, poke)."""
    d = ar_probe()
    out = []
    for i, (case, cs) in enumerate(zip(d["cases"], d["case_set"])):
        (poke,) = cs["pokes"]
        out.append((i, 1 + i // 20, ROWS[int(poke.split("=")[1], 16)], case[16] >> 8, poke))
    return out


def markers(run, rows, lo):
    """attribute-room's markers: 0xa<run><rows:02x><attribute:04x> (attribute-room.toml)."""
    return [0xA0000000 | run << 24 | rows << 16 | (lo + k) for k in range(16)]


def ar_case(run, rows, lo):
    """An attribute-room case at any size: its 16 markers, then C0-C15 = attribute << 8."""
    return markers(run, rows, lo) + [(lo + k) << 8 for k in range(16)]


def render_case(case):
    d = ar_probe()
    p = P._probe(d, "attribute-room.toml")
    return asm(P.render(p, case, pins.blob(DOUTA_TPL).decode()), "pds")


def do_markers(i):
    d = [p for p in tomllib.loads(pins.blob(DO_TOML).decode())["probe"]
         if p["name"] == "pds-douta-secattr-rows-4"][0]
    return d["cases"][i][:16], d["case_set"][i]["pokes"][0]


def markers_value(ms):
    return ",".join(f"{m:08x}" for m in ms)


def name_of(run, rows, lo):
    return f"q019-{run}-r{rows}-a{lo:02d}"


def q019_jobs():
    """[(name, run, rows, lo, poke, E391 case index or None)]: E391's 40, then the 16 held out."""
    out = [(name_of(run, rows, lo), run, rows, lo, poke, i)
           for i, run, rows, lo, poke in ar_cases()]
    for run in (1, 2):
        for rows in NEW_ROWS:
            for lo in SETS:
                out.append((name_of(run, rows, lo), run, rows, lo, f"bg:1=0x{bg1(rows):x}", None))
    return out


# ---- stages -------------------------------------------------------------------------------------
USE64 = f'--temps 32 --pds {PDS_N} --use "$S/bins/sa64_dump.bin" --scratch-show {SHOW}'
USE16 = f'--temps 32 --pds {PDS_N} --use "$S/bins/sa_dump.bin" --scratch-show {SHOW}'


def pk64(files):
    rows, pred = [], [HEAD]
    files["bins/sa64_dump.bin"] = pins.blob(AR + "sa64_dump.bin")
    files["bins/sa_dump.bin"] = pins.blob(DO + "sa_dump.bin")
    files["bins/pk-e391.bin"] = pins.blob(AR + "pds-attribute-room-rows__0.bin")
    files["bins/pk-e125.bin"] = pins.blob(DO + "pds-douta-secattr-rows-4__0.bin")
    ms, poke = do_markers(0)
    ar_poke = ar_cases()[0][4]
    rows.append(probe_row("pk-e391", "control", "reads:echo,shown",
                          f'{USE64} --poke {ar_poke} "$S/bins/pk-e391.bin"'))
    rows.append(probe_row("pk-e125", "control", "reads:echo,shown",
                          f'{USE16} --poke {poke} "$S/bins/pk-e125.bin"'))
    src = "E1096 (r23-pk pk): t22's echo and sa0-sa15; rank-round24.md 5"
    pred.append(line("pk-e391", "echo", "bg:1=0x00030000", "H-ECHO", "control", src))
    pred.append(line("pk-e125", "echo", "bg:1=0x00130000", "H-ECHO", "control", src))
    pred.append(line("pk-e391", "own", markers_value(markers(1, 0, 0)), "H-E391", "control",
                     "E1096/E391 run 1, 0 rows, attributes 0-15: sa0-sa15 its markers, stray 0"))
    pred.append(line("pk-e125", "own", markers_value(ms), "H-E125", "control",
                     "E1096/E125 rows 4, markers A: sa0-sa15 its markers, stray 0"))
    pred.append(line("pk-e391", "shown", "64/0", "H-SHOW", "control",
                     "t24 --scratch-show 64: sa64_dump.s changes 64 dwords (E1096: 32 shown + "
                     "`32 more changed`): 64 lines, no more line"))
    pred.append(line("pk-e125", "shown", "16/0", "H-SHOW", "control",
                     "sa_dump.s changes 16 dwords (E1096's pk-e125: 16 lines, no more line)"))
    return rows, pred


def q019(files):
    rows, pred = [], [HEAD]
    for name, run, nrows, lo, poke, i in q019_jobs():
        st = "fit" if nrows in FIT_ROWS else "heldout"
        if i is None:
            files[f"bins/{name}.bin"] = render_case(ar_case(run, nrows, lo))
        else:
            files[f"bins/{name}.bin"] = pins.blob(AR + f"pds-attribute-room-rows__{i}.bin")
        rows.append(probe_row(name, st, "-", f'{USE64} --poke {poke} "$S/bins/{name}.bin"'))
        bg = int(poke.split("=")[1], 16)
        src = "E391's job" if i is not None else "held out: E391's set at a size it did not run"
        pred.append(line(name, "echo", f"bg:1=0x{bg:08x}", "H-ECHO", st,
                         "rank-round24.md 5: every poke row reads its echo (premise)"))
        # H-E391 (in-row control of the old reading): sa0-sa31 as E1096 read them
        pred.append(line(name, "own_lo", 16 if lo < 32 else 0, "H-E391", st,
                         f"{src}; E391/E1096: attributes 0-31 at their own sa, none of 32-63 in "
                         "sa0-sa31, no stray"))
        # the new reading: sa32-sa63
        pred.append(line(name, "own", 16, "H-ALL64", st,
                         f"{src}; rank-round24.md 2.1: attributes {lo}-{lo + 15} at sa{lo}-"
                         f"sa{lo + 15} at every size, no stray in sa0-sa63"))
        pred.append(line(name, "own", 16 if lo < 32 else 0, "H-NONE", st,
                         f"{src}; rank-round24.md 2.1: no marker of 32-63 in sa0-sa63 at any "
                         "size (E391's never sa32-sa63 stands)"))
        pred.append(line(name, "own", f"fit:{lo}", "H-ROWS", st,
                         "rank-round24.md 2.1: fitted on 0, 1, 4 rows by the scorer (fit table "
                         "hashed and printed first); held out: at 2 and 3 rows between 1 and 4, "
                         "at 6 and 8 at least 4"))
    return rows, pred


HEADERS = {
    "pk64": """#stage pk64
#limit 0
# pk64 (rank-round24.md 5, R24-1 a): E1096's pk-e391 (E391 case 0: 0 rows, attributes 0-15, sa64_dump.bin) and pk-e125
# (E125 case 0: 4 rows, sa_dump.bin) on t24 with --scratch-show 64. Controls: the echo (H-ECHO), sa0-sa15 their markers
# (H-E391, H-E125, as E1096), the print (H-SHOW: pk-e391 64 scratch lines and no `more changed` line, pk-e125 16).
# Gates q019. Stop: a poke row whose echo count is not its poke count, a print capped below 64 (run/hooks.sh), any fault
# or hang; on_stop end.""",
    "q019": """#stage q019
#limit 0
# q019 (Q019, rank-round24.md 2.1 and 5): E391's 40 jobs on t24 (data pds/attribute-room bins and pokes byte for byte,
# sa64_dump.bin) with --scratch-show 64, then 16 held out at 3 and 6 rows (E391's four attribute sets, two runs; the
# programs rendered from attribute-room.toml with the size in the marker). Frozen: H-E391 (sa0-sa31 as E1096: the in-row
# control), H-ALL64 (attributes 32-63 at sa32-sa63 at every size), H-NONE (none of 32-63 at any size), H-ROWS (fit 0, 1,
# 4 rows; held out 2, 3, 6, 8; fit table hashed first). Gate: pk64's controls. Stop: a poke row without its echo, a
# print capped below 64 (run/hooks.sh), any fault or hang.""",
}


def build():
    files = {}
    stages = {"pk64": pk64(files), "q019": q019(files)}
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
