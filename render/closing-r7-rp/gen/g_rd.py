#!/usr/bin/env python3
"""g_rd.py: stages p7-rdc (14 jobs) and p7-rd (34 jobs) of r7-rp (Q276; plan closing7/a/exp-pixel-r7.md 1.4, 3.4).

Command: R6's p6-rd command byte for byte (R5's C_BASE: `probe --tri pixel --temps 32 --pixels` on the 64x64 triangle with the PDS
iteration slot), tool t4 (~/sgxfive-test-rgn4, the binary of every precedent row).  Knobs: none (R6's `stophang s2` is not a knob
of this session's runner: it resets before every job and checks STATUS2 in its health).
  p7-rdc  R6's 14 bridge controls, R6's programs byte for byte (bins hashes pinned in gen/data/bins-rd.txt): c-e709 (G-o4), c-u
          (G-o1), c-all4 (5:1), c-ow, c-rd-0 (defines TRI), c-prd-0 k = 1 and 7; the driver's gate (score_rd7.gate).
  p7-rd   replicates rd-1..rd-7, n-rd-4, x-rd-4 (R6's programs byte for byte); held out x-rd-6, x-rd-7, n-rd-5 and the clean rows
          cl-4..cl-7, cl-p4 (k = 0): new programs by R6's generator method (gen/rdprog_rd.py, R6's program() unchanged; the same
          landed assembler, tools/usse-asm, whose hash is R6's pin), new markers 0x1f0..0x1ff (R6 used 0x181..0x1ec).
Checks before writing: R6's bins copied from closing6/r6-pixel/bins equal the published copies (resgx545-data render/closing-r6-
pixel/bins); R6's own configurations re-assembled here with R6's markers give R6's bins byte for byte (the method is R6's); R6's
table rows' args equal this table's; the score modules copied from R6 (score/rd_*.py) equal R6's with only their imports renamed.
  write(kp)   tables/p7-rdc.txt, tables/p7-rd.txt, predictions/p7-rdc.tsv, predictions/p7-rd.tsv, bins/*.bin (this area's),
              gen/data/bins-rd.txt, gen/data/sources-rd.lst
  controls(stage), producible(row)    (scorekit.refuse_unreadable)
  PY gen/g_rd.py"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(KP, "score")]
import rd7model as R7  # noqa: E402
import rd_rdmodel as RM  # noqa: E402
import rdprog_rd as PG  # noqa: E402
import scorekit  # noqa: E402

REPO = os.environ.get("RESGX545_MAIN", "/Users/jtorra/src/resgx545")
DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
R6 = "/Users/jtorra/src/scratch/resgx545/closing6/r6-pixel"
R6PUB = os.path.join(DATA, "render/closing-r6-pixel")
sys.path.insert(0, os.path.join(REPO, "tools/usse-asm"))

C_BASE = ('probe --tri pixel --temps 32 --pixels --dump-render "$W/dump" --width 64 --height 64 --vtx-coords 2 '
          '--blk 4=0x00030001 --slot pixpds="$S/pds_iter_xy.bin:12" --slot vtxuse="$S/vtx_coords.bin" "$S/{prog}.bin"')
TOOL = "t4"
KNOBS = "-"
LIMIT = 1                      # plan 2: fault limit 1, none expected (no fault in R5's p5-o4 or R6's p6-rd)
M_NEW = 0x1f0                  # first new marker; m * 64 + 0x3f < 0x8000 holds up to 0x1ff
COMMON = ["pds_iter_xy", "vtx_coords"]
R6_CTL_PROGS = {"c-e709": "r4o-e709", "c-u": "r4o-u", "c-all4": "r5o-c-all4", "c-ow": "r6o-c-ow", "c-rd-0": "r6o-c-rd-0",
                "c-prd-0-k1": "r6o-c-prd-0-k1", "c-prd-0-k7": "r6o-c-prd-0-k7"}
R6_RD_PROGS = {c: f"r6o-{c}" for c in R7.REPL}
NEW = R7.HELD + R7.CLEAN + [R7.CLP]
COPIED = {"rd_r4lib.py": "r4lib.py", "rd_o5model.py": "o5model.py", "rd_rdmodel.py": "rdmodel.py", "rd_score_o4.py": "score_o4.py",
          "rd_score_o5.py": "score_o5.py", "rd_score_rd.py": "score_rd.py"}
RENAMES = ("r4lib", "o5model", "rdmodel", "score_o4", "score_o5", "score_rd")

_read = []


def rd(path, mode="rb"):
    """Read a file outside KP and record it for gen/data/sources-rd.lst."""
    path = os.path.abspath(path)
    if not path.startswith(KP + os.sep) and path not in _read:
        _read.append(path)
    with open(path, mode) as f:
        return f.read()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def r6_markers():
    return {a: int(b) for a, b in (ln.split("\t") for ln in rd(os.path.join(R6, "bins/p6-markers.tsv"), "r").splitlines() if ln)}


def r6_table_args():
    out = {}
    for ln in rd(os.path.join(R6, "tables/p6-rd.txt"), "r").splitlines():
        if ln and not ln.startswith("#"):
            f = ln.split("|", 5)
            out[f[0]] = f[5]
    return out


def r6_preds():
    lines = rd(os.path.join(R6, "predictions/p6-rd.tsv"), "r").splitlines()[1:]
    return [ln.split("\t") for ln in lines]


def assemble(text, out):
    import probe
    probe._assemble(text, out)


def r6_text(name, ax, m):
    if name in ("c-ow", "c-rd-0") or name.startswith("c-prd-0"):
        return PG.special(ax, m, name)
    return PG.program(ax, m, RM.config(name))


def new_text(name, ax, m):
    cfg = R7.config(name)
    return PG.clean_pred(ax, m, cfg) if name.startswith("cl-p") else PG.program(ax, m, cfg)


def check_copies():
    """The score modules copied from R6 equal R6's with only their imports renamed."""
    for mine, theirs in COPIED.items():
        a = open(os.path.join(KP, "score", mine)).read()
        b = rd(os.path.join(R6, "score", theirs), "r")
        for r in RENAMES:
            a = re.sub(rf"^import rd_{r} as ", f"import {r} as ", a, flags=re.M)
        if a != b:
            raise SystemExit(f"g_rd: score/{mine} is not R6's {theirs} with its imports renamed")
        pub = rd(os.path.join(R6PUB, "score", theirs), "r")
        if pub != b:
            raise SystemExit(f"g_rd: R6's {theirs} differs from the published copy")


def bins(kp):
    """Copy R6's programs, re-assemble R6's configurations (they must give R6's bytes), assemble the new ones.  Returns
    ({prog: sha}, {cfg-ax: marker})."""
    bd = os.path.join(kp, "bins")
    os.makedirs(bd, exist_ok=True)
    progs = COMMON + [f"{p}-{ax}" for p in list(R6_CTL_PROGS.values()) + list(R6_RD_PROGS.values()) for ax in "xy"]
    pins = {}
    for p in progs:
        b = rd(os.path.join(R6, "bins", p + ".bin"))
        if rd(os.path.join(R6PUB, "bins", p + ".bin")) != b:
            raise SystemExit(f"g_rd: R6's {p}.bin differs from the published copy")
        with open(os.path.join(bd, p + ".bin"), "wb") as f:
            f.write(b)
        pins[p] = sha(b)
    mk = r6_markers()
    tmp = tempfile.mkdtemp(prefix="rd-asm-", dir=os.path.join(kp, "debug"))
    try:
        for name in ["c-ow", "c-rd-0", "c-prd-0-k1", "c-prd-0-k7"] + R7.REPL:
            for ax in "xy":
                out = os.path.join(tmp, f"{name}-{ax}.bin")
                assemble(r6_text(name, ax, mk[f"{name}-{ax}"]), out)
                if open(out, "rb").read() != open(os.path.join(bd, f"r6o-{name}-{ax}.bin"), "rb").read():
                    raise SystemExit(f"g_rd: R6's {name}-{ax} re-assembled is not R6's bin: the method is not R6's")
    finally:
        shutil.rmtree(tmp)
    markers = {}
    m = M_NEW
    for name in NEW:
        for ax in "xy":
            assert m * 64 + 0x3f < 0x8000
            p = f"r7o-{name}-{ax}"
            assemble(new_text(name, ax, m), os.path.join(bd, p + ".bin"))
            pins[p] = sha(open(os.path.join(bd, p + ".bin"), "rb").read())
            markers[f"{name}-{ax}"] = m
            m += 1
    for name in R6_CTL_PROGS:
        if name in mk or f"{name}-x" in mk:
            markers[f"{name}-x"], markers[f"{name}-y"] = mk[f"{name}-x"], mk[f"{name}-y"]
    for name in R7.REPL:
        markers[f"{name}-x"], markers[f"{name}-y"] = mk[f"{name}-x"], mk[f"{name}-y"]
    return pins, markers


def prog_of(name):
    if name in R6_CTL_PROGS:
        return R6_CTL_PROGS[name]
    if name in R6_RD_PROGS:
        return R6_RD_PROGS[name]
    return f"r7o-{name}"


def rows(stage):
    """[(row name, set, program)] of a stage, in order."""
    if stage == "p7-rdc":
        cfgs = [(c, "control") for c in R7.CONTROLS]
    else:
        cfgs = [(c, "replicate") for c in R7.REPL] + [(c, "heldout") for c in R7.HELD + R7.CLEAN + [R7.CLP]]
    return [(f"{c}-{ax}", st, f"{prog_of(c)}-{ax}") for c, st in cfgs for ax in "xy"]


def row_line(name, st, prog):
    return "|".join((name, st, "safe", KNOBS, TOOL, C_BASE.format(prog=prog)))


HEAD = {
    "p7-rdc": """Q276 (r7-rp), stage p7-rdc: R6's 14 bridge controls of p6-rd, R6's command and programs byte for byte (bins pinned in
gen/data/bins-rd.txt), tool t4.  c-e709 (E709's o4g-3: G-o4), c-u (R4's program: G-o1, tag-2 fraction >= 0.98), c-all4 (R5's:
5:1), c-ow (the last o0 write is the pixel, >= 0.95 of TRI), c-rd-0 (readback through r10, >= 0.95 of TRI; TRI = its own pixels in
both jobs), c-prd-0 k = 1 and 7 (the predicate on o0 lane by lane, >= 0.95 of each lane).  The driver's gate (score_rd7.py gate
p7-rdc): G-o4, G-o1, c-ow, c-rd-0 and both c-prd-0 rows must pass, else p7-rd is skipped and the session goes on.  No fault
expected (none in R5's p5-o4 or R6's p6-rd); a fault stops the stage.""",
    "p7-rd": """Q276 (r7-rp), stage p7-rd (after p7-rdc's gate passed): R6's p6-rd rerun with the share counted over own-source words
(a word that decodes to the pixel itself), tool t4, R6's command.  Replicates (R6's programs byte for byte): rd-1..rd-7, n-rd-4,
x-rd-4; a replicate whose top label differs from R6's is not replicated and voids its entry.  Held out: x-rd-6, x-rd-7 (o6 / o7
written as (9 + j) | 0x10: tag 15, and 0x10 = tag 0 with bit 4 at j = 7), n-rd-5 (no o5 write); clean cl-4..cl-7 (only o0 = word A
and o_j = word B written, then o_j read: R6's original rule, one class at >= 0.90 of all TRI in both jobs); cl-p4 (cl-4 with
`p1 or.skipinv o4` under xor.testtaz.chan0 !c0, p1, g25, #0; R6's lane rule).  Own-source rule: class L when in both jobs L holds
>= 0.85 of the own-source words and no other model class (S, A0, A4) more than 0.02.  Predicted: H-MOD4 (S S S A0 A4 A4 A4;
x-rd-6, x-rd-7, n-rd-5 read o2's, o3's, o1's word; cl-4 word A, cl-5..7 not word B, cl-p4 word A on every lane).  Fault limit 1,
none expected.""",
}


def preds(markers):
    """{stage: [(case, quantity, value, model, set)]}."""
    r6p = r6_preds()
    out = {"p7-rdc": [], "p7-rd": []}
    ctl_cases = {f"{c}-x" for c in R7.CONTROLS}
    for f in r6p:                              # R6's frozen control rows, verbatim
        if f[0] in ctl_cases:
            out["p7-rdc"].append(tuple(f[:4]) + ("control",))
    P = out["p7-rdc"].append
    P(("@p7-rdc", "gate", "G-o4 c-e709; G-o1 c-u >= 0.98; c-ow 1:1 >= 0.95 of TRI; c-rd-0 1:2 >= 0.95 of TRI; c-prd-0 k1 and k7 "
       "lanes as frozen (>= 0.95 of each lane's TRI pixels in both jobs)", "R6's bridge (plan 3.4); any control not PASS: gate not 0, "
       "the driver skips p7-rd", "control"))
    P(("@p7-rdc", "void", "c-all4 not 5:1", "R6: the stage's layout cannot be read; p7-rd's verdict is cannot tell (not a gate)",
       "control"))
    Q = out["p7-rd"].append
    for name in R7.REPL + R7.HELD + R7.CLEAN + [R7.CLP]:
        st = "replicate" if name in R7.REPL else "heldout"
        x = f"{name}-x"
        Q((x, "marker", f"{markers[x]:#x}", "frozen program marker (x job; the y job's is " + f"{markers[name + '-y']:#x})", st))
        Q((x, "labels", " ".join(f"{c}={v}" for c, v in R7.labels(name).items()), "class labels (rd7model.labels)", st))
        if name in R7.REPL:
            Q((x, "r6_top", R7.R6_TOP[name], "R6's top label in both jobs (fold/posthoc_r6.txt A): a different top label in either "
               "job: not replicated, the entry is void", st))
        if name == R7.CLP:
            for mdl in R7.MODELS:
                Q((x, "lanes", ",".join(R7.clp_lanes(mdl)), mdl + (" (gated, as c-prd-0)" if mdl == "H-STORE" else ""), st))
            continue
        for mdl in R7.MODELS:
            Q((x, "class", R7.klass(mdl, name), mdl, st))
    Q(("@p7-rd", "models", " ".join(f"{m}={','.join(RM.rd_vector(m))}" for m in R7.MODELS),
       "R6's frozen rd vectors over j = 1..7 (!S = any decided class but S)", "heldout"))
    Q(("@p7-rd", "own_rule", f"class L: in both jobs L >= {R7.OWN_SHARE} of the own-source words and every other model class "
       f"(S, A0, A4) <= {R7.RIVAL_MAX}; own-source words < {R7.OWN_MIN} in a job: cannot tell", "plan 3.4 (fit on R6's p6-rd: "
       "0.903..1.000, rivals 0)", "heldout"))
    Q(("@p7-rd", "clean_rule", f"one class at >= {RM.CLASS_SHARE} of ALL TRI pixels in both jobs (R6's read_rd unchanged: X, O, "
       f"S, A0, W); cl-p4: R6's lane rule (>= {RM.LANE_SHARE} of each lane's TRI pixels in both jobs)", "plan 3.4", "heldout"))
    Q(("@p7-rd", "verdict", "H-MOD4 held: every replicate replicated and decided as H-MOD4, every held-out and clean row as H-MOD4; "
       "H-STORE at j: a decided entry with j >= 4 reads S (E878's post hoc reading refuted, Q276 reopened); else cannot tell or "
       "H-MOD4 refuted", "plan 3.4 outcomes", "heldout"))
    return out


def write_stage(kp, stage, pr):
    rs = rows(stage)
    need = [f"$S/{p}.bin" for p in COMMON] + [f"$S/{p}.bin" for _, _, p in rs]
    need = list(dict.fromkeys(need))
    lines = [f"#stage {stage}", f"#limit {LIMIT}"] + [f"#need {n}" for n in need]
    lines += [f"# {ln}".rstrip() for ln in HEAD[stage].strip().splitlines()]
    lines += [row_line(*r) for r in rs]
    with open(os.path.join(kp, "tables", stage + ".txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(kp, "predictions", stage + ".tsv"), "w") as f:
        f.write("case\tquantity\tvalue\tmodel\tset\n")
        for p in pr[stage]:
            assert len(p) == 5 and all("\t" not in str(x) and "\n" not in str(x) for x in p), p
            f.write("\t".join(str(x) for x in p) + "\n")


def producible(row):
    """Reading keys a row's job can produce: a `probe --tri pixel --pixels` job at 64x64 prints its class and every pixel row."""
    a = row.split("|")[5] if "|" in row else row
    keys = {"class"}
    if a.startswith("probe ") and "--pixels" in a and "--width 64 --height 64" in a:
        keys |= {"pixels"}
    return keys


def controls(stage="p7-rdc"):
    """The controls of a stage and what each reads (p7-rd has none of its own: its gate is p7-rdc's)."""
    if stage != "p7-rdc":
        return []
    return [{"name": n, "reads": ["class", "pixels"]} for n, _, _ in rows("p7-rdc")]


def write(kp=KP):
    for d in ("tables", "predictions", "bins", "gen/data", "debug"):
        os.makedirs(os.path.join(kp, d), exist_ok=True)
    check_copies()
    pins, markers = bins(kp)
    r6a = r6_table_args()
    for stage in ("p7-rdc", "p7-rd"):
        for name, _, prog in rows(stage):
            if name in r6a and r6a[name] != C_BASE.format(prog=prog):
                raise SystemExit(f"g_rd: {name}'s args are not R6's")
    pr = preds(markers)
    for stage in ("p7-rdc", "p7-rd"):
        by = {n: row_line(n, s, p) for n, s, p in rows(stage)}
        scorekit.refuse_unreadable({c["name"]: (tuple(c["reads"]), by[c["name"]]) for c in controls(stage)}, producible)
        write_stage(kp, stage, pr)
    with open(os.path.join(kp, "gen/data/bins-rd.txt"), "w") as f:
        f.write("".join(f"{h}  {p}.bin\n" for p, h in sorted(pins.items())))
    srcs = list(_read) + [os.path.join(REPO, "tools/usse-asm/usse-asm"), os.path.join(REPO, "tools/usse-asm/probe.py")]
    with open(os.path.join(kp, "gen/data/sources-rd.lst"), "w") as f:
        f.write("\n".join(sorted(set(srcs))) + "\n")
    return pins


if __name__ == "__main__":
    p = write(KP)
    print(f"g_rd: p7-rdc {len(rows('p7-rdc'))} jobs, p7-rd {len(rows('p7-rd'))} jobs, {len(p)} bins pinned")
