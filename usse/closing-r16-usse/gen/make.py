#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r16-usse's generator. Writes tables/STAGE.txt and predictions/STAGE.tsv of the two
stages (uadd, utest, in run order) and the programs bins/NAME.s and bins/NAME.bin (usse-asm of the
pinned commit), every input read at the commits session.toml's [freeze] names (gen/pins.py), the
predictions from sgx-sim of that commit and gen/rule.py (gen/progs.py says which).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now
A prediction's value is the scratch dwords the program changes, `OFFSET=VALUE` (bytes, hex)
joined by commas; a dword the model does not name is left at its fill (0xd0000000 | i)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import progs  # noqa: E402
import scorekit  # noqa: E402
import sim  # noqa: E402

HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("uadd", "utest", "urpt")
TOOL = "t10"
PROBE = "probe --temps 32"
HEADERS = {
    "uadd": """# r16-usse uadd, Q126 (rank-round16.md section 2, R16-5 a): iaddu32 over eight (r1, source 2) pairs a program, each
# result stored to its own scratch dword (E599's pattern, client fills); r1's low half 0x8000-0xffff in seven pairs, 0x7fff
# in one (both extensions agree there). Forms not run before: source 2 #1, #127 and c56 (0xffffffff), the destinations i0
# and sa0 (read back by mov). Frozen: H-ZX (E521; sgx-sim) against H-SX. The write masks are stage urpt, the session's last.
# Controls that can fail: E521's pairs and E498's iaddu32 tests over two pairs, replicated (kept readbacks).
# Stop: any fault or hang (#limit 0, safe class); the second row without its scratch readout.""",
    "utest": """# r16-usse utest, Q137 (rank-round16.md section 2, R16-5 a): the class 9 test field, one form and one join a program,
# fields 0-15 packed one bit a field (`p0 or`) with the value of the operation, six input pairs whose results cover zero,
# positive and negative (or #7: no zero result is possible); shl, shr, asr with registers, or and rol with #7, iadd32 and
# iaddu32 sums, each with the a join and the o join; then the lane operations iadd8 and iadd16 on one pair of distinct
# bytes, chan0-or02 by the nine fields the assembler names, the a join, and last the o join (the E530 family with lanes).
# Frozen: H-RULE (E499/E529/E530 as sgx-sim gives it) against H-SETAND (a), H-AJOIN, H-ORFALSE, H-SETOR (o), H-CHAN0
# (lanes). Controls that can fail: E499's and E529's kept tables (rawcond, rawjoin-o), replicated.
# Stop: any fault or hang (#limit 0, safe class); the second row without its scratch readout.""",
    "urpt": """# r16-usse urpt, Q126's repeat (rank-round16.md section 2, R16-5 a): iaddu32 r10.xy and r10.xyzw (the write mask of the
# test, a field no job ran on a class 9 word; sgx-sim refuses it), sources r1 + k and r5 + k, r10-r13 preset to markers, the
# same eight pairs as uadd's. Frozen: H-ZX-ADV (component k writes d + k from the sources advanced by k, as the other
# forms' masks, with E521's extension) against H-SX, H-NOREP (only d written) and H-NOADV (every component d's value).
# Control that can fail: E521's pairs again, first. The session's last stage (on_stop = "end").
# Stop: any fault or hang (#limit 0, safe class); the second row without its scratch readout.""",
}


def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def fmt(d):
    return ",".join("0x%03x=0x%08x" % (k, d[k]) for k in sorted(d))


def row(name, st):
    knobs = "reads:scratch" if st == "control" else "-"
    return f'{name}|{st}|safe|{knobs}|{TOOL}|{PROBE} "$S/bins/{name}.bin"'


def put_prog(files, j):
    files[f"bins/{j['name']}.s"] = j["text"].encode()
    files[f"bins/{j['name']}.bin"] = sim.assemble(j["text"])


def stage(files, names, job):
    rows, pred = [], [HEAD]
    for n in names:
        j = job(n)
        put_prog(files, j)
        rows.append(row(n, j["set"]))
        for q, models in j["preds"].items():
            for m, d in models.items():
                src = j["why"] + ("; kept readbacks" if m in ("H-E499", "H-E529", "H-E521",
                                                               "H-E498") else
                                  "; sgx-sim (pinned)" if m in ("H-SIM",) else
                                  "; gen/rule.py, sgx-sim's classes")
                pred.append(line(n, q, fmt(d), m, j["set"], src))
    return rows, pred


def build():
    files, tables = {}, {}
    tables["uadd"] = stage(files, progs.UROWS, progs.uadd_job)
    tables["utest"] = stage(files, progs.TROWS, progs.utest_job)
    tables["urpt"] = stage(files, progs.RROWS, progs.uadd_job)
    import score as SC
    for st in ORDER:
        rows, pred = tables[st]
        files[f"tables/{st}.txt"] = (f"#stage {st}\n#limit 0\n{HEADERS[st]}\n"
                                     + "\n".join(rows) + "\n").encode()
        files[f"predictions/{st}.tsv"] = "".join(pred).encode()
        controls = {}
        for r in rows:
            name, s, _, knobs, tool, args = r.split("|", 5)
            if s == "control":
                reads = [w[6:].split(",") for w in knobs.split() if w.startswith("reads:")]
                controls[name] = (tuple(reads[0]) if reads else (),
                                  dict(name=name, args=args, stage=st))
        scorekit.refuse_unreadable(controls, SC.producible)
    return files


def main(argv):
    files = build()
    check = "--check" in argv
    bad = []
    for rel, b in sorted(files.items()):
        p = os.path.join(KP, rel)
        if check:
            if not os.path.exists(p) or open(p, "rb").read() != b:
                bad.append(rel)
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b)
    if check:
        for d in ("bins", "tables", "predictions"):
            full = os.path.join(KP, d)
            for n in sorted(os.listdir(full)) if os.path.isdir(full) else []:
                if f"{d}/{n}" not in files:
                    bad.append(f"{d}/{n} (not written by the generator)")
        print("\n".join(f"differs: {b}" for b in bad) or f"generator current: {len(files)} files")
        return 1 if bad else 0
    print(f"wrote {len(files)} files; pins read: {', '.join(sorted(pins.READ))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
