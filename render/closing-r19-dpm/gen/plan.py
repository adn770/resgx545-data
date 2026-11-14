#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""plan.py: r19-dpm's generator (round 19, S2: what a final render that does not overflow shows;
closing19/plan/rank-round19.md section 3; DECISIONS-R19). Writes tables/STAGE.txt and
predictions/STAGE.tsv for the five stages, in run order:

  ld   (8, E1079)  Q045's load readback: E631 Part B on the final-PB knob (geometry kick at P, final
                   on N = 0x100 pages, which does not overflow), base twins and page 6 zeroed before
                   the final (`--tadata-fill-render 2:6:0`; medium, `soft`, last in the stage)
  ldb  (6, E1080)  Q045's state-page statistic: 4096x4096 default triangle, -n 1, knob 0
  dz   (15, E1081) Q038's depth readback: E628's dl form (dz-a), the layered background with a
                   depth buffer (dz-c, -n 1, t10), E628's ov form (dz-ov), final on N
  zs   (7, E1082)  Q107's sign, zero row and tile order: E629's ramp, final on N
  rd   (6, E1083)  Q088: which control word a partial render stores with (render 1's or another)

  python3 gen/plan.py          write the tables and predictions
  python3 gen/plan.py --check  exit 1 when a written file differs from what it would write

Every geometry row (t18b under regtimeline): `tri -n 2 --geometry 1 --final-pb-pages 0x100`, the
geometry kick overflows at P (E625: one partial render at 1024x768 for P 0x28 to 0x30), the final
render does not: its premise (`ctl:ovf1=1 ctl:ovf2=0 ctl:thr=0xde`, run/hooks.sh) is read on every
geometry row and one off stops the stage (rc 24). Every depth row on the geometry form passes
`--depth-ctl-next` (else the host refills the buffers before the final, line 3269 of the tool).
`--ctx2` and `--bg-layer` refuse `--geometry`: no row mixes them (dz-c is -n 1 on t10)."""
from __future__ import annotations

import pathlib
import sys

KP = pathlib.Path(__file__).resolve().parent.parent

STAGES = ("ld", "ldb", "dzl", "dza", "dzc", "dzo", "zsc", "zs", "rd")
GATES = {"dza": "dzl", "zs": "zsc"}           # score.py gate: the stage runs if those controls pass
RECORDS = {"ld": "E1079", "ldb": "E1080", "dzl": "E1081", "dza": "E1081", "dzc": "E1081",
           "dzo": "E1081", "zsc": "E1082", "zs": "E1082", "rd": "E1083"}
RT = "0x012c,0x0620-0x0628,0x0658,0x0660,0x0668,0x0700,0x070c-0x0710,0x0720-0x0734,0x0748,0x0a74"
LEAD = "0.3"
T18 = '"$HOME/sgxfive-test-t18b"'
T10 = '"$HOME/sgxfive-test-t10"'
N_FINAL = 0x100
D_OFF = 0x22
THR_N = N_FINAL - D_OFF                     # 0xde: the final render's ZLS threshold (H-UPD)
COMMON = ('--keep-going --keep-overflow --wait-ms 20000 --dump-render "$W" --dump-each '
          '--words "$W" --regs 0x0600-0x0750')
GEO = (f"tri --width 1024 --height 768 -n 2 --geometry 1 --final-pb-pages 0x{N_FINAL:x} "
       + COMMON)
NL33, LD33, NL1, E336 = 0x0017110C, 0x0017510E, 0x0017100C, 0x0011700A
Z05 = "--poke blk:1=0x00400200"                       # E461's z = 0.5 triangle
RAMP = "--tri-full --tri-z 0.25,0.75,0.25"            # E629's full-screen ramp
OVZ = "--tri-z 0.25,0.75,0.25"                        # E628's ov rows
BG = "dbg:render_bg_layer=Y dbg:render_bg_src=0x3e800000"   # r9-k1's binding
PREMISE = "ctl:ovf1=1 ctl:ovf2=0 ctl:thr=0x%x" % THR_N
# G33 layout (E465): tile (tx, ty) at dword 512 * (34 ty + tx); tile rows 0-11 = the first
# macrotile row at 1024x768 (E628's zero region), dwords below ROW12
ROW12 = 512 * 34 * 12
G1_SLOTS = 127                                         # slots 0 .. 126 at G = 1 (q107_rule)


def hx(v):
    return f"0x{v:x}"


def g_of(ctl):
    """CR_ISP_ZLSCTL bits 11:3 (E465)."""
    return ctl >> 3 & 0x1FF


def marker(k):
    return 0xD0190000 + k


def rt(tool, args):
    return f"0 {LEAD} {RT} -- {tool} {args}"


def dbg_p(p):
    return f"dbg:render_pb_pages={hx(p)}"


def row(name, sset, risk, knobs, args, tool=T18, **meta):
    return dict(name=name, set=sset, risk=risk, knobs=" ".join(knobs.split()), tool="rt",
                args=rt(tool, args), **meta)


# ---- ld ----------------------------------------------------------------------------------------
def ld_rows():
    out = []
    for n, s, p in (("ld-b28-1", "control", 0x28), ("ld-b28-2", "control", 0x28),
                    ("ld-b30", "heldout", 0x30), ("ld-b2c", "heldout", 0x2C)):
        reads = " reads:ovf1,ovf2,thr" if s == "control" else ""
        out.append(row(n, s, "safe", f"{dbg_p(p)} expectdiff {PREMISE}{reads}", GEO, p=p,
                       zero=False, twin=None))
    for n, s, p, tw in (("ld-z28-1", "fit", 0x28, "ld-b28-1"), ("ld-z28-2", "fit", 0x28, "ld-b28-2"),
                        ("ld-z30", "heldout", 0x30, "ld-b30"), ("ld-z2c", "heldout", 0x2C, "ld-b2c")):
        out.append(row(n, s, "medium", f"{dbg_p(p)} expectdiff soft {PREMISE}",
                       GEO + " --tadata-fill-render 2:6:0", p=p, zero=True, twin=tw))
    return out


# ---- ldb ---------------------------------------------------------------------------------------
LDB_ARGS = "tri --width 4096 --height 4096 -n 1 " + COMMON


def ldb_rows():
    out = []
    for n, s, p in (("ldb-c0", "control", 0xC0), ("ldb-100", "control", 0x100),
                    ("ldb-40", "heldout", 0x40), ("ldb-60", "heldout", 0x60),
                    ("ldb-80", "heldout", 0x80), ("ldb-a0", "heldout", 0xA0)):
        reads = " reads:ovf1,nparts,peak" if s == "control" else ""
        out.append(row(n, s, "safe", f"{dbg_p(p)} ctl:ovf1=1{reads}", LDB_ARGS, p=p,
                       raised=p < 0xC0))
    return out


# ---- dz ----------------------------------------------------------------------------------------
def dl_args(ctl, k, geo):
    base = GEO if geo else "tri --width 1024 --height 768 -n 1 " + COMMON
    nxt = f" --depth-ctl-next {hx(ctl)}" if geo else ""
    return (f"{base} {Z05} --depth --depth-ctl {hx(ctl)}{nxt} --depth-fill index "
            f'--depth-dump "$W" --depth-store --depth-store-fill {hx(marker(k))}')


def dz_rows():
    out = [
        row("dz-ac-nl", "control", "safe", "dbg:render_pb_pages=0x422 expectdiff ctl:ovf1=0 "
            "ctl:sidx=0 reads:ovf1,sidx", dl_args(NL33, 1, False), tool=T10, form="dl",
            ctl=NL33, p=0x422, geo=False),
        row("dz-ac-ld", "control", "safe", "dbg:render_pb_pages=0x422 expectdiff ctl:ovf1=0 "
            "ctl:sidx=1 reads:ovf1,sidx", dl_args(LD33, 2, False), tool=T10, form="dl",
            ctl=LD33, p=0x422, geo=False),
        row("dz-cc", "control", "safe", f"{BG} dbg:render_pb_pages=0x422 expectdiff ctl:ovf1=0 "
            "ctl:diff=0 reads:ovf1,diff,inplace", None, tool=T10, form="bg", p=0x422,
            geo=False),
    ]
    k = 3
    for n, s, p, c in (("dz-a-nl28-1", "fit", 0x28, NL33), ("dz-a-nl28-2", "fit", 0x28, NL33),
                       ("dz-a-ld28", "fit", 0x28, LD33), ("dz-a-e336-28", "heldout", 0x28, E336),
                       ("dz-a-nl30", "heldout", 0x30, NL33), ("dz-a-ld30", "heldout", 0x30, LD33)):
        out.append(row(n, s, "safe", f"{dbg_p(p)} expectdiff {PREMISE}", dl_args(c, k, True),
                       form="dl", ctl=c, p=p, geo=True))
        k += 1
    for n, s in (("dz-c28-1", "heldout"), ("dz-c28-2", "heldout")):
        out.append(row(n, s, "safe", f"{BG} dbg:render_pb_pages=0x28 expectdiff ctl:ovf1=1", None,
                       tool=T10, form="bg", p=0x28, geo=False))
    for n, s, p, mv in (("dz-ov-far28", "fit", 0x28, -96), ("dz-ov-near28", "fit", 0x28, 96),
                        ("dz-ov-far30", "heldout", 0x30, -96), ("dz-ov-near30", "heldout", 0x30, 96)):
        a = (f"{GEO} --move 2:{mv},0 {OVZ} {Z05} --depth --depth-ctl {hx(NL33)} --depth-ctl-next "
             f'{hx(NL33)} --depth-fill {hx(marker(k))} --depth-dump "$W"')
        out.append(row(n, s, "safe", f"{dbg_p(p)} expectdiff {PREMISE}", a, form="ov", ctl=NL33,
                       p=p, geo=True, fill=marker(k)))
        k += 1
    for r in out:
        if r["form"] == "bg":
            a = ("tri --width 1024 --height 768 -n 1 --bg-layer --keep-going --keep-overflow "
                 '--wait-ms 20000 --dump-render "$W" --words "$W" --regs 0x0600-0x0750 --depth '
                 f"--depth-ctl {hx(NL33)} --depth-pages 0x340 --depth-fill {hx(marker(k))} "
                 '--depth-dump "$W"')
            r["args"], r["fill"] = rt(T10, a), marker(k)
            k += 1
    return out


# ---- zs ----------------------------------------------------------------------------------------
def z_args(c1, c2, k, geo):
    base = GEO if geo else "tri --width 1024 --height 768 -n 1 " + COMMON
    nxt = f" --depth-ctl-next {hx(c2)}" if geo else ""
    return (f"{base} {RAMP} --depth --depth-ctl {hx(c1)}{nxt} --depth-fill {hx(marker(k))} "
            '--depth-dump "$W"')


def zs_rows():
    out = [row("zs-c33", "control", "safe", "dbg:render_pb_pages=0x422 expectdiff ctl:ovf1=0 "
               "reads:ovf1", z_args(NL33, None, 20, False), tool=T10, g=33, p=0x422, geo=False,
               twin=None, fill=marker(20)),
           row("zs-c1", "control", "safe", "dbg:render_pb_pages=0x422 expectdiff ctl:ovf1=0 "
               "reads:ovf1", z_args(NL1, None, 21, False), tool=T10, g=1, p=0x422, geo=False,
               twin="zs-c33", fill=marker(21))]
    k = 22
    for n, s, p, c, tw in (("zs-28-g33-1", "fit", 0x28, NL33, None),
                           ("zs-28-g33-2", "fit", 0x28, NL33, None),
                           ("zs-28-g1", "fit", 0x28, NL1, "zs-28-g33-1"),
                           ("zs-30-g33", "heldout", 0x30, NL33, None),
                           ("zs-30-g1", "heldout", 0x30, NL1, "zs-30-g33")):
        out.append(row(n, s, "safe", f"{dbg_p(p)} expectdiff {PREMISE}", z_args(c, c, k, True),
                       g=g_of(c), p=p, geo=True, twin=tw, fill=marker(k)))
        k += 1
    return out


# ---- rd ----------------------------------------------------------------------------------------
def rd_rows():
    out, k = [], 30
    for n, s, p, c1, c2 in (("rd-28-a1", "fit", 0x28, NL33, NL1), ("rd-28-a2", "fit", 0x28, NL33, NL1),
                            ("rd-28-b1", "heldout", 0x28, NL1, NL33),
                            ("rd-28-b2", "heldout", 0x28, NL1, NL33),
                            ("rd-30-a", "heldout", 0x30, NL33, NL1),
                            ("rd-30-b", "heldout", 0x30, NL1, NL33)):
        out.append(row(n, s, "safe", f"{dbg_p(p)} expectdiff {PREMISE}", z_args(c1, c2, k, True),
                       g1=g_of(c1), g2=g_of(c2), p=p, geo=True, fill=marker(k)))
        k += 1
    return out


def tables():
    """The stages in run order. dz and zs are split by the dumps their rows write (the scorer's
    REQUIRED is per stage, per row): dzl E628's -n 1 dl controls, dza the dl geometry rows (gated
    by dzl), dzc the layered background (-n 1, its control first), dzo the ov rows; zsc the -n 1
    pair (E996's rule), zs the geometry rows (gated by zsc)."""
    dz, zs = dz_rows(), zs_rows()
    return {"ld": ld_rows(), "ldb": ldb_rows(),
            "dzl": [r for r in dz if r["form"] == "dl" and not r["geo"]],
            "dza": [r for r in dz if r["form"] == "dl" and r["geo"]],
            "dzc": [r for r in dz if r["form"] == "bg"],
            "dzo": [r for r in dz if r["form"] == "ov"],
            "zsc": [r for r in zs if not r["geo"]],
            "zs": [r for r in zs if r["geo"]],
            "rd": rd_rows()}


def rows_by_name():
    return {r["name"]: r for rs in tables().values() for r in rs}


# ---- predictions (frozen before the run) -------------------------------------------------------
SRC = {
    "ld": "E631 Part B, E627 (page 6 lists), E626 (walk), rank-round19 3a",
    "ldb": "Q045 part (b) and Round 12 (dpm_raise.py A2), E627, E625 (raise)",
    "dz": "E628 (dl, ov forms), E442/E038, rank-round19 3c",
    "zs": "E629 (sign), E628 (zero region), E996/E1020 and q107_rule.py (tile order)",
    "rd": "E465 (G marks the layout), d43e4bb (rd:11 per render), rank-round19 3e",
}


def family(st):
    return {"dzl": "dz", "dza": "dz", "dzc": "dz", "dzo": "dz", "zsc": "zs"}.get(st, st)


def predictions(st, rs):
    P = []
    st = family(st)

    def add(n, q, v, m, s):
        P.append((n, q, str(v), m, s, SRC[st]))

    for r in rs:
        n, s = r["name"], r["set"]
        if r.get("geo"):
            add(n, "ovf1", 1, "PREMISE", "control")
            add(n, "ovf2", 0, "PREMISE", "control")
            add(n, "thr", hx(THR_N), "PREMISE", "control")
        if st == "ld":
            if not r["zero"]:
                if s == "control":
                    add(n, "rep", 1, "CTL", "control")
                continue
            add(n, "page6", ">=1", "PREMISE", "control")
            for q in ("same_param", "same_counts", "same_image"):
                add(n, q, 1, "H-NOLOAD", s)
            add(n, "same_param|same_counts", "0 (either)", "H-LOAD", s)
        elif st == "ldb":
            add(n, "ovf1", 1, "PREMISE", "control")
            add(n, "raised", int(r["raised"]), "E625", "control" if s == "control" else s)
            if s == "control":
                add(n, "sum", "thr0-1", "R-THR", "control")
            else:
                add(n, "sum", "peak-1", "R-PEAK", s)
                add(n, "sum", "thr0-1", "R-THR", s)
                add(n, "sum", "peak-1+-3", "R-NEAR", s)
        elif st == "dz":
            if s == "control":
                if r["form"] == "dl":
                    add(n, "ovf1", 0, "CTL", "control")
                    add(n, "sidx", int(r["ctl"] == LD33), "CTL", "control")
                else:
                    add(n, "ovf1", 0, "CTL", "control")
                    add(n, "diff", 0, "CTL", "control")
                continue
            if r["form"] == "dl":
                if r["ctl"] == NL33:
                    add(n, "idx_hi", ">0", "H-PRPATH", s)
                    add(n, "idx_hi", "0", "H-HOSTBITS", s)
                else:
                    add(n, "idx_any", ">0", "H-PRPATH", s)
                    add(n, "idx_any", ">0", "H-HOSTBITS", s)
                add(n, "z1_lo", ">0", "H-PRZERO", s)
                add(n, "z1_lo", "0", "H-CLRREAD", s)
            elif r["form"] == "bg":
                add(n, "ovf1", 1, "PREMISE", "control")
                add(n, "diff", 0, "H-WHOLE", s)
                add(n, "diff", ">0", "H-LOSS", s)
            else:
                add(n, "kept1", ">=0.5*t1", "H-PRLOAD", s)
                add(n, "kept1", "<=0.05*t1", "H-OWNCLEAR", s)
        elif st == "zs":
            if s == "control":
                add(n, "ovf1", 0, "CTL", "control")
                if r["twin"]:
                    add(n, "rule", "all scored", "CTL", "control")
                continue
            if r["g"] == 33:
                raised = r["p"] == 0x28
                add(n, "sign1_hi", ">0" if raised else "0", "H-PRSIGN", s)
                add(n, "sign2", "0", "H-PRSIGN", s)
                add(n, "sign2", ">0" if raised else "0", "H-FINALSIGN", s)
                add(n, "zero2_lo", "0", "H-PRSIGN", s)
            else:
                add(n, "rule", "all scored", "H-E996", s)
                add(n, "rule", "fewer", "E1020", s)
        elif st == "rd":
            add(n, "g_store1", r["g1"], "H-RD", s)
            add(n, "g_store1", 1, "H-FW-CONST", s)
            add(n, "g_store1", r["g2"], "H-FW-FINAL", s)
    return P


HEAD = {
    "ld": ("ld (8, E1079): Q045's load readback. E631 Part B on the final-PB knob: the geometry kick "
           "overflows at P, the final render (N 0x100) does not, so it no longer stores over page "
           "6 before a read. Base rows first (the 0x28 pair are the controls: the dumps repeat byte "
           "for byte), then page 6 zeroed before the final (medium [infer], soft, last: the second "
           "soft failure in a row stops the stage; any premise off stops it). H-LOAD: the zeroed "
           "lists change the final's frees (param dump or 0x0730/0x0660 differ from the base twin); "
           "H-NOLOAD: identical."),
    "ldb": ("ldb (6, E1080): Q045's state-page statistic on raised 4096x4096 jobs, the page at "
            "0x42000 (E627). R-PEAK: the 16 macrotile counts sum to the last run's peak status - 1; "
            "R-THR: thr0 - 1; R-NEAR: within 3. Controls P 0xc0 and 0x100 (not raised: R-THR)."),
    "dzl": ("dzl (2, E1081): E628's -n 1 0x422 dl cells on t10, the controls dza is gated by: "
            "without load bits the store holds the scene's depth (3 distinct values, sidx 0), with "
            "them the loaded indices (sidx 1); can fail on the new module."),
    "dza": ("dza (6, E1081): Q038, E628's dl form with the final on N 0x100 (no abort): "
            "H-PRPATH (the final store holds indices past tile row 11 without load bits) vs "
            "H-HOSTBITS (none); H-PRZERO (zeros below row 12 of the load buffer after render 1) vs "
            "H-CLRREAD; one row with E336's word 0x0011700a (rd's load half). Gated by dzl."),
    "dzc": ("dzc (3, E1081): the layered background with a depth buffer (-n 1, t10, "
            "--depth-pages 0x340 so the G 33 store stays in its buffer): H-WHOLE vs H-LOSS at "
            "0x28; the control at 0x422 (diff 0) first."),
    "dzo": ("dzo (4, E1081): E628's ov form with the final on N 0x100, no load bits: "
            "H-PRLOAD (the final keeps the partial render's depth) vs H-OWNCLEAR."),
    "zsc": ("zsc (2, E1082): the -n 1 0x422 ramp pair G 33 / G 1 on t10, the controls zs is "
            "gated by: no overflow, q107_rule's RULE holds (E996, E1020's 6 of 6)."),
    "zs": ("zs (5, E1082): Q107 on E629's ramp with the final on N: H-PRSIGN vs H-FINALSIGN "
           "(the sign and the zero row), H-E996 vs E1020 (tile order of the G 1 store against its "
           "G 33 twin, q107_rule.py). Gated by zsc."),
    "rd": ("rd (6, E1083): Q088. The partial render of the geometry kick stores with the G of "
           "render 1's control word (H-RD) or another (H-FW-CONST: the library's G 1; H-FW-FINAL: "
           "the final's word); render 1 / render 2 G 33 / G 1 and swapped."),
}


def table_text(st, rs):
    out = [f"#stage {st}", "#limit 0", f"# {HEAD[st]}"]
    out += ["|".join((r["name"], r["set"], r["risk"], r["knobs"], r["tool"], r["args"]))
            for r in rs]
    return "\n".join(out) + "\n"


def extra_knobs(T_):
    return sorted({k for rs in T_.values() for r in rs for k in r["knobs"].split()
                   if k.startswith("ctl:")})


def knob_values(T_, name):
    return sorted({k.split("=", 1)[1] for rs in T_.values() for r in rs
                   for k in r["knobs"].split() if k.startswith(f"dbg:{name}=")},
                  key=lambda v: int(v, 16) if v.startswith("0x") else 0)


def outputs():
    T_ = tables()
    files = {}
    for st in STAGES:
        files[f"tables/{st}.txt"] = table_text(st, T_[st])
        files[f"predictions/{st}.tsv"] = "case\tquantity\tvalue\tmodel\tset\tsource\n" + "".join(
            "\t".join(p) + "\n" for p in predictions(st, T_[st]))
    return T_, files


def main(argv):
    T_, files = outputs()
    if argv[1:] == ["--check"]:
        bad = [f for f, t in files.items() if not (KP / f).exists() or (KP / f).read_text() != t]
        print("generator current" if not bad else "differs: " + " ".join(bad))
        return 1 if bad else 0
    for f, t in files.items():
        (KP / f).parent.mkdir(exist_ok=True)
        (KP / f).write_text(t)
    print(sum(len(v) for v in T_.values()), "jobs:", {s: len(v) for s, v in T_.items()})
    print("extra_knobs =", extra_knobs(T_))
    print("render_pb_pages values =", knob_values(T_, "render_pb_pages"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
