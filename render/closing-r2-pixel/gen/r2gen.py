#!/usr/bin/env python3
"""r2gen.py: regenerate the R2-pixel tables, frozen predictions, staged programs, TABLES.md and stages.txt.

Run (numpy not needed):  PYTHONDONTWRITEBYTECODE=1 python3 gen/r2gen.py     (then run/freeze_r2.sh freeze)
Inputs read only: the landed probe tool and template (tx_map.s is copied to templates/ and frozen), the p1141 data
repo's probe table (the L2e2 and L0e2 cases), S1b's frozen A4 images (gen/data/), E727's model counts (below).
Stages: r2-d-safe, r2-d-fault (Q281 D2), r2-a-safe, r2-a-fault (Q286 A2), and the conditional r2-a-slack (the
pre-approved slack pair, run only when the decision rule says a5 cannot tell: see PREFLIGHT.md section 5).
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import pathlib  # noqa: E402
import tomllib  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
R2 = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(R2 / "score"))
sys.path.insert(0, str(pathlib.Path.home() / "src/resgx545/tools/usse-asm"))
import probe  # noqa: E402  (the landed probe tool, read-only: renders and assembles the programs)
import r2models as M  # noqa: E402
import r2lib as L  # noqa: E402

DATA = pathlib.Path.home() / "src/resgx545-data/texture/p1141"
TABLES, PREDS, BINS, TEMPL = R2 / "tables", R2 / "predictions", R2 / "bins", R2 / "templates"
RT_HELD = "0x0118,0x012c,0x0c00-0x0c08"
TRI_COMMON = ("tri --tri-full --keep-going --wait-ms 20000 --width {w} --height {h} --max-width {mw} --max-height {mh} "
              "--poke cmd:1={te} --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26 "
              '--dump-render "$W/dump"')
# E727's model (closing2/pixel/q286_pairs_model.out): background pixels at TE 0x20 and the first one
E727 = {(320, 400): (28, (304, 128)), (288, 656): (605, (272, 208))}


class Row:
    def __init__(self, name, sset, risk, knobs, rt, args, role=""):
        self.name, self.set, self.risk, self.knobs, self.rt, self.args, self.role = name, sset, risk, knobs, rt, args, role


def write_table(stage, rows, need, head):
    names = [r.name for r in rows]
    assert len(names) == len(set(names)), stage
    out = [f"#stage {stage}"] + [f"#need {n}" for n in need] + [f"# {ln}" for ln in head.strip().splitlines()]
    for r in rows:
        assert "|" not in r.args and "\t" not in r.args, r.name
        out.append("|".join((r.name, r.set, r.risk, r.knobs, r.rt, r.args)))
    (TABLES / f"{stage}.txt").write_text("\n".join(out) + "\n")


def write_preds(name, preds):
    lines = ["case\tquantity\tvalue\tmodel\tset"] + ["\t".join(str(x) for x in p) for p in preds]
    (PREDS / f"{name}.tsv").write_text("\n".join(lines) + "\n")


# ------------------------------------------------------------------------------------------------ programs
def build_programs():
    """The three D2 programs.  s1d-tw64x64-l2e2 and s1d-tw128x32-l0e2 are S1b's (rebuilt here and required to be
    byte-identical to the staged copies, which faulted/completed on the laptop in S1b); s1d-tw64x64-l2e2-x1 is the same
    program with the last instruction `mov.skipinv.end o0, r10` -> `xor.skipinv.end o0, r10, #1`."""
    pr = tomllib.loads((DATA / "probes/p1141-addr.toml").read_text())["probe"][0]
    labels = pr["labels"]
    base = dict(name="s1d", question="s1", source="tx_map.s", coords=True, pixels=True, params={},
                inputs=["PRE", "SETUP", "SMP"])
    out = {}
    tmp = R2 / "debug" / "build"
    tmp.mkdir(exist_ok=True)
    for label, nm in (("ad-tw64x64-L2e2", "s1d-tw64x64-l2e2"), ("ad-tw128x32-L0e2", "s1d-tw128x32-l0e2")):
        p = probe._probe({**base, "name": nm, "cases": [pr["cases"][labels.index(label)]]}, "s1-d.toml")
        probe.build(p, tmp, TEMPL)
        mine, staged = (tmp / f"{nm}__0.bin").read_bytes(), (BINS / f"{nm}__0.bin").read_bytes()
        assert mine == staged, f"{nm}: the rebuilt program differs from the staged S1b copy"
        out[nm] = nm
    # the variant: a template with exactly the one changed line
    src = (TEMPL / "tx_map.s").read_text()
    old = "mov.skipinv.end o0, r10"
    assert src.count(old) == 1
    (TEMPL / "tx_map_x1.s").write_text(src.replace(old, "xor.skipinv.end o0, r10, #1"))
    nm = "s1d-tw64x64-l2e2-x1"
    p = probe._probe({**base, "name": nm, "source": "tx_map_x1.s",
                      "cases": [pr["cases"][labels.index("ad-tw64x64-L2e2")]]}, "r2-d.toml")
    probe.build(p, BINS, TEMPL)
    out[nm] = nm
    return out


# ------------------------------------------------------------------------------------------------ D2
def a4_rows():
    rows = [r.split("\t") for r in (HERE / "data/s1b_p-d-A4.tsv").read_text().splitlines()[1:]]
    return {r[0]: [int(v, 16) for v in r[3].split(",")] for r in rows}


def d2():
    progs = build_programs()
    s1b = {}
    for ln in (HERE / "data/s1b_p-d.tsv").read_text().splitlines()[1:]:
        c, q, v, m, s = ln.split("\t")
        s1b[(c, q)] = v
    okhash = s1b[("d-ok-64", "pix_sha256_if_complete")]
    a4 = a4_rows()
    assert M.pix_hash(a4["d-ok-64"]) == okhash
    L2, L2X, L0 = progs["s1d-tw64x64-l2e2"], progs["s1d-tw64x64-l2e2-x1"], progs["s1d-tw128x32-l0e2"]

    def row(nm, sset, pages, prog, knobs, role):
        risk = "risky" if "hypo" in knobs else "safe"
        return Row(nm, sset, risk, knobs, "-", f'probe --temps 32 --coords --pixels --scratch-pages {pages} "$S/{prog}__0.bin"', role)

    safe = [
        row("d-ok-64", "control", 64, L0, "stophang", "control: E722's passing case at 64 pages (S1b measured A4 exact)"),
        row("d-L2e2-19", "control", 19, L2, "expectnopix", "control (FIT): S1b's image byte for byte (coords page 1)"),
        row("d-L2e2-19x", "control", 19, L2X, "expectnopix", "control of the variant: S1b's image XOR 1 (every word)"),
        row("d-L2e2-18x", "heldout", 18, L2X, "expectnopix", "HELD OUT, decisive: coords page 2 under the xor: 0xdeadbeee everywhere"),
        row("d-L2e2-18", "repeat", 18, L2, "expectnopix", "retrodiction: S1b measured rc 3 'no pixel written' (fit, tallied apart)"),
    ]
    fault = [
        row("d-L2e2-17", "heldout", 17, L2, "hypo:d17:1", "HELD OUT: first read past the coords surface: BIF fault 0x90002 at 0x3e017001"),
        row("d-L2e2-16", "control", 16, L2, "hypo:d16:1", "control, LAST: E722's job unchanged (faults 0x90002 at 0x3e017001)"),
    ]
    need = [f"$S/{n}__0.bin" for n in (L0, L2, L2X)]
    head_s = """D2 (Q281, safe part): the 18-page outcome is the probe's own VM layout (closing2/exp-pixel.md section 0.1).
HL: scratch (P pages) then the 3-page coords surface, adjacent: P = 19 reads coords page 1 (the coords words), P = 18 reads
coords page 2 (0xdeadbeef = 'no pixel written' to the probe's sentinel check).  HS: a sampler/BIF effect between 16 and 19.
The variant s1d-tw64x64-l2e2-x1 is tx_map.s with `xor.skipinv.end o0, r10, #1`: at 18 pages a job writing 0xdeadbeee is
not 'no pixel written': HL says the image is 0xdeadbeee everywhere (2048 of 2048), HS says rc 3 or another image.
Knob proof: the probe's `scratch at 0x3e003000 (N KiB)` line (another base voids the row).  Non-faulting rows only."""
    head_f = """D2 (Q281, fault part, LAST): d-L2e2-17 (HELD OUT: HL says the first read past the coords surface is unmapped, BIF
fault 0x90002 at 0x3e017001; HS says it completes or faults elsewhere) and the control d-L2e2-16 (E722's fault).  Each
group is one event; every fault is followed by the runner's reset and health triangle."""
    write_table("r2-d-safe", safe, need, head_s)
    write_table("r2-d-fault", fault, need[1:2], head_f)
    preds = []
    imgs = []

    def P(*a):
        preds.append(a)

    def img_pred(nm, sset, pages, xor, label):
        px = M.image(pages, xor)
        P(nm, "scratch_line", f"({pages * 4} KiB)", "knob", sset)
        P(nm, "outcome", "complete", label, sset)
        P(nm, "pix_sha256_if_complete", M.pix_hash(px), label, sset)
        imgs.append((nm, label, pages, px))
        return px

    P("d-ok-64", "scratch_line", "(256 KiB)", "knob", "control")
    P("d-ok-64", "outcome", "complete", "A4", "control")
    P("d-ok-64", "pix_sha256_if_complete", okhash, "A4", "control")
    imgs.append(("d-ok-64", "ad-tw128x32-L0e2", 64, a4["d-ok-64"]))
    img_pred("d-L2e2-19", "control", 19, 0, "HL (fit: S1b measured 2048 of 2048)")
    img_pred("d-L2e2-19x", "control", 19, 1, "HL (S1b's image XOR 1)")
    # 18x: HL = 0xdeadbeee everywhere, rc 0; HS = rc 3 (no pixel written) or another image
    px = img_pred("d-L2e2-18x", "heldout", 18, 1, "HL")
    assert set(px) == {0xDEADBEEE}
    P("d-L2e2-18x", "outcome", "rc3 no pixel written", "HS (rc 3)", "heldout")
    P("d-L2e2-18x", "outcome", "other image", "HS (another image)", "heldout")
    P("d-L2e2-18", "scratch_line", "(72 KiB)", "knob", "repeat")
    P("d-L2e2-18", "outcome", "rc3 no pixel written", "HL (retrodiction: S1b measured rc 3)", "repeat")
    P("d-L2e2-18", "outcome", "complete", "HS", "repeat")
    assert M.first_fault(17) == M.first_fault(16) == 0x3E017001
    for nm, sset, pages in (("d-L2e2-17", "heldout", 17), ("d-L2e2-16", "control", 16)):
        P(nm, "scratch_line", f"({pages * 4} KiB)", "knob", sset)
        P(nm, "outcome", "fault", "HL" if nm.endswith("17") else "E722", sset)
        P(nm, "fault_word", "0x90002", "HL" if nm.endswith("17") else "E722", sset)
        P(nm, "fault_addr", "0x3e017001", "HL" if nm.endswith("17") else "E722", sset)
    P("d-L2e2-17", "outcome", "complete", "HS", "heldout")
    write_preds("r2-d", preds)
    lines = ["job\tlabel\tpages\tpixels"] + [f"{n}\t{lab}\t{pg}\t" + ",".join(f"{v:08x}" for v in px) for n, lab, pg, px in imgs]
    (PREDS / "r2-d-images.tsv").write_text("\n".join(lines) + "\n")
    return safe, fault, preds


# ------------------------------------------------------------------------------------------------ A2
def a2():
    def tri(w, h, mw, mh, te):
        return TRI_COMMON.format(w=w, h=h, mw=mw, mh=mh, te=te)

    ex = "expectdiff"
    safe = [
        Row("a4-ctl-320x400-te20", "control", "safe", f"stophang {ex}", "-", tri(320, 400, 544, 400, "0x20000000"),
            "control, E727's model: TE 0x20 at 320x400 in a context made for 544x400: 28 wrong pixels, first (304,128)"),
        Row("a1-256x160-dump", "heldout", "risky", f"stophang {ex}", "-", tri(256, 160, 256, 160, "0xe0000000"),
            "E729's completing 4x size, with the dump: slot 4 zero (H4) or array-like (H5)"),
        Row("a2-320x128-dump", "heldout", "risky", f"stophang {ex}", "-", tri(320, 128, 320, 128, "0xe0000000"),
            "E729's second completing 4x size, with the dump"),
        Row("a3-256x160-rep", "replicate", "risky", f"stophang {ex}", "-", tri(256, 160, 256, 160, "0xe0000000"),
            "replicate of a1: TA data sha256 equal"),
    ]
    fault = [
        Row("a5-320x400-max544", "heldout", "risky", f"held hypo:fx:2 {ex}", RT_HELD, tri(320, 400, 544, 400, "0xe0000000"),
            "HELD OUT, held: 4x in a context made for 544x400 (arrays end exactly at the TA data's end 0xa000)"),
        Row("a6-320x400-max320", "control", "risky", f"held hypo:fx:2 {ex}", RT_HELD, tri(320, 400, 320, 400, "0xe0000000"),
            "control, held, LAST: the same target in a context made for 320x400 (TA data 0x8000): must fault 0x90004"),
    ]
    slack = [
        Row("sa4-ctl-288x656-te20", "control", "safe", f"stophang {ex}", "-", tri(288, 656, 544, 656, "0x20000000"),
            "slack-pair control: TE 0x20 at 288x656 in 544x656: 605 wrong pixels (E727 model), 1 array"),
        Row("sa5-288x656-max544", "heldout", "risky", f"held hypo:fx:2 {ex}", RT_HELD, tri(288, 656, 544, 656, "0xe0000000"),
            "slack pair, HELD OUT, held: 4 arrays end at 0x10000, TA data 0x11000 (one page of slack)"),
        Row("sa6-288x656-max288", "control", "risky", f"held hypo:fx:2 {ex}", RT_HELD, tri(288, 656, 288, 656, "0xe0000000"),
            "slack pair control, held, LAST: max 288x656 (TA data 0xd000): must fault 0x90004 at 0x2000d"),
    ]
    head_s = """A2 (Q286, safe part): S3's design with a4 refrozen to E727's model (S3 measured a4: diff 28 of 128000, first
(304,128), echo 544x400, TA data 0xa000, one array at 0x4000..0x5800, nothing below 0x4000 or from 0x5800).  a1, a2 (own
contexts, TE 0xe0) and the replicate a3 as S3.  Every tri row carries expectdiff (S3's a4 stopped the stage without it)."""
    head_f = """A2 (Q286, fault part, LAST): a5 is HELD OUT (HELD: debugfs hold_recovery Y while the registers are read, then the
kernel's own debugfs reset, as S3).  H4: completes, diff 0, TA data 0xa000, slots 0-3 of 0x1800 from 0x4000.  H5 (or the
slack of the kernel layout): held fault 0x90004 at page 0x2000a, status2 0x480.  a6 is the control that can fail."""
    head_k = """A2 slack pair (PRE-APPROVED fallback, 2026-11-10 R2-8): 288x656 in a context made for 544x656 (rgn 0x7000,
rgn_size 0x2400, size 0x11000: four arrays end at 0x10000, one page of slack; a fifth would end at 0x12400).  Run only when
the decision rule says a5 cannot tell (PREFLIGHT.md section 5)."""
    write_table("r2-a-safe", safe, [], head_s)
    write_table("r2-a-fault", fault, [], head_f)
    write_table("r2-a-slack", slack, [], head_k)
    preds = []

    def P(*a):
        preds.append(a)

    def ctl(case, w, h, mw, mh, sset="control"):
        n, (bx, by) = E727[(w, h)]
        lay = L.layout(w, h)
        P(case, "outcome", "complete", "both", sset)
        P(case, "diff", f"{n} of {w * h}", "E727 model", sset)
        P(case, "diff_first", f"({bx}, {by})", "E727 model", sset)
        P(case, "max_echo", f"{mw}x{mh}", "knob", sset)
        P(case, "tadata_size", hex(L.layout(mw, mh)["size"]), "knob", sset)
        P(case, "slots_written", "1", "both", sset)
        P(case, "rgn", hex(lay["rgn"]), "layout", sset)
        P(case, "rgn_size", hex(lay["rgn_size"]), "layout", sset)

    ctl("a4-ctl-320x400-te20", 320, 400, 544, 400)
    for nm, w, h in (("a1-256x160-dump", 256, 160), ("a2-320x128-dump", 320, 128)):
        P(nm, "outcome", "complete", "both", "heldout")
        P(nm, "diff", f"0 of {w * h}", "both", "heldout")
        P(nm, "tadata_size", hex(L.layout(w, h)["size"]), "knob", "heldout")
        P(nm, "min_slots_written", "4", "knob", "heldout")
        P(nm, "slot4", "zero", "H4", "heldout")
        P(nm, "slot4", "written", "H5", "heldout")
    P("a3-256x160-rep", "tadata_sha256", "same as a1-256x160-dump", "both", "replicate")

    def pair(a5, a6, w, h, mw, mh):
        fp5 = L.fault_page_if(4, (w, h), (mw, mh))
        fp6 = L.fault_page_if(4, (w, h), (w, h))
        assert fp6 is not None
        P(a5, "outcome", "complete" if fp5 is None else "fault", "H4", "heldout")
        P(a5, "outcome", "fault", "H5", "heldout")
        P(a5, "diff", f"0 of {w * h}", "H4", "heldout")
        P(a5, "max_echo", f"{mw}x{mh}", "knob", "heldout")
        P(a5, "tadata_size", hex(L.layout(mw, mh)["size"]), "H4", "heldout")
        P(a5, "slots_written", "4", "H4", "heldout")
        P(a5, "int_stat", "0x90004", "H5", "heldout")
        P(a5, "fault_page", hex(L.TADATA_BASE_PAGE + (L.layout(mw, mh)["size"] >> 12)), "H5", "heldout")
        P(a5, "status2", "0x480", "H5", "heldout")
        P(a6, "outcome", "fault", "both", "control")
        P(a6, "max_echo", f"{w}x{h}", "knob", "control")
        P(a6, "int_stat", "0x90004", "both", "control")
        P(a6, "fault_page", hex(fp6), "both", "control")
        P(a6, "status", "0x20000000", "HE", "control")
        P(a6, "status2", "0x480", "HE", "control")
        P(a6, "extra_bits", "none", "HE", "control")
        P(a6, "extra_bits", "some", "HF", "control")
        return fp5

    assert pair("a5-320x400-max544", "a6-320x400-max320", 320, 400, 544, 400) is None      # boundary-exact: f = 4 fits
    ctl("sa4-ctl-288x656-te20", 288, 656, 544, 656)
    fp = pair("sa5-288x656-max544", "sa6-288x656-max288", 288, 656, 544, 656)
    assert fp is None
    write_preds("r2-a", preds)
    return safe, fault, slack, preds


# ------------------------------------------------------------------------------------------------ views
def tables_md(d_safe, d_fault, a_safe, a_fault, a_slack, dp, ap):
    out = ["# R2-pixel frozen tables (generated by gen/r2gen.py; the .txt tables and .tsv predictions are the frozen files)", "",
           "Quantity = value [hypothesis/label].  Sets: control, heldout, repeat (a fit of earlier data run again; tallied apart),",
           "replicate.  Stage order: r2-d-safe, r2-d-fault, r2-a-safe, r2-a-fault; r2-a-slack only by its gate.", ""]
    for st, rows, preds in (("r2-d-safe", d_safe, dp), ("r2-d-fault", d_fault, dp), ("r2-a-safe", a_safe, ap),
                            ("r2-a-fault", a_fault, ap), ("r2-a-slack", a_slack, ap)):
        out += [f"## {st}", "", "| row | set | knobs | frozen predictions |", "|---|---|---|---|"]
        for r in rows:
            ps = [f"{q} = {v[:60]} [{m}]" for c, q, v, m, s in preds if c == r.name]
            out.append(f"| {r.name} | {r.set} | {r.knobs} | " + "; ".join(ps) + " |")
        out.append("")
        for r in rows:
            out.append(f"- {r.name}: {r.role}")
        out.append("")
    (R2 / "TABLES.md").write_text("\n".join(out) + "\n")


def main():
    for d in (TABLES, PREDS, BINS, TEMPL):
        d.mkdir(exist_ok=True)
    ds, df, dp = d2()
    as_, af, ak, ap = a2()
    (R2 / "stages.txt").write_text("r2-d-safe\nr2-d-fault\nr2-a-safe\nr2-a-fault\n")
    (R2 / "conditional.txt").write_text("r2-a-slack\n")
    tables_md(ds, df, as_, af, ak, dp, ap)
    print(f"tables: {len(ds)}+{len(df)} D2 rows, {len(as_)}+{len(af)}+{len(ak)} A2 rows; predictions {len(dp)}+{len(ap)}")


if __name__ == "__main__":
    main()
