#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""plan.py: r20-zls's generator (round 20, S1: Q088's reload half, Q038's store clauses, Q107's
not-raised clause; closing20/plan/rank-round20.md section 3; closing20/DECISIONS-R20.md). Writes
tables/STAGE.txt and predictions/STAGE.tsv for the four stages, in run order:

  zc  (3, E1088)  controls: E1081's dz-a-nl28-1 again, first (the store after the final is the
                  store after render 1), then E628's -n 1 0x422 dl cells on t18b (store: the
                  scene's depth / the loaded indices); zregs (0x0480-0x0488 read the poked word and bases)
                  is a reading control: if it fails only the register readings are void
  zr  (8, E1088)  Q088's reload half: render 1 overflows (raised at 0x28, 0x2c), the host writes
                  0.25 into the load buffer (`--refill 2:depth=0x3e800000`), the final draws T1
                  moved 96 px right; H-LOADBASE / H-STOREBASE / H-NOSTORE / H-HOSTBITS on the store
                  after the final, against the row's own store after render 1
  zm  (3, E1089)  Q038's colour clause, narrowed: the moved final without a depth buffer;
                  H-REPAINT (the final paints every pixel) vs H-HOLES (target pixels left at the
                  library's sentinel)
  zq  (4, E1090)  Q107's not-raised clause: E629's ramp at P 0x44 and 0x4c (overflows, not raised:
                  E625's 2 (P - 0x22) >= U + 2 with U 49), H-NR-PLAIN vs H-AFTERPR

  python3 gen/plan.py          write the tables and predictions
  python3 gen/plan.py --check  exit 1 when a written file differs from what it would write

Every geometry row (t18b under regtimeline): `tri -n 2 --geometry 1 --final-pb-pages 0x100`, the
kick overflows at P, the final does not: its premise (`ctl:ovf1=1 ctl:ovf2=0 ctl:thr=0xde`,
run/hooks.sh) is read on every geometry row and one off stops the stage (rc 24). Every depth row
on the geometry form passes `--depth-ctl-next` (else the host refills before the final); zr's
refill is its own `--refill 2:depth=...`, read as `ctl:refill=1`. regtimeline samples r19's DPM
set plus 0x0480-0x0490 (CR_ISP_ZLSCTL, the load and store bases, the stencil bases; read only,
R20-7 a)."""
from __future__ import annotations

import pathlib
import sys

KP = pathlib.Path(__file__).resolve().parent.parent

STAGES = ("zc", "zr", "zm", "zq")
GATES = {"zr": "zc", "zm": "zc", "zq": "zc"}   # the plan: zc's store controls off, nothing runs
RECORDS = {"zc": "E1088", "zr": "E1088", "zm": "E1089", "zq": "E1090"}
RT = ("0x012c,0x0620-0x0628,0x0658,0x0660,0x0668,0x0700,0x070c-0x0710,0x0720-0x0734,0x0748,0x0a74,"
      "0x0480-0x0490")
LEAD = "0.3"
T18 = '"$HOME/sgxfive-test-t18b"'
N_FINAL = 0x100
D_OFF = 0x22
THR_N = N_FINAL - D_OFF                     # 0xde: the final render's ZLS threshold
COMMON = ('--keep-going --keep-overflow --wait-ms 20000 --dump-render "$W" --dump-each '
          '--words "$W" --regs 0x0600-0x0750')
GEO = (f"tri --width 1024 --height 768 -n 2 --geometry 1 --final-pb-pages 0x{N_FINAL:x} "
       + COMMON)
NL1 = "tri --width 1024 --height 768 -n 1 " + COMMON
NL33, LD33, NL1C, E336 = 0x0017110C, 0x0017510E, 0x0017100C, 0x0011700A
Z05 = "--poke blk:1=0x00400200"                       # E461's z = 0.5 triangle
RAMP = "--tri-full --tri-z 0.25,0.75,0.25"            # E629's full-screen ramp
PREMISE = "ctl:ovf1=1 ctl:ovf2=0 ctl:thr=0x%x" % THR_N
ONE, HALF, QUARTER = 0x3F800000, 0x3F000000, 0x3E800000
REFILL = f"--refill 2:depth=0x{QUARTER:x}"
MOVE = 96                                    # px right: 3 tiles of 32, the in-tile index kept
DPAGES = 0x340                               # zr: the G 33 store's 1024x768 window in its buffer
W, H = 1024, 768
ROW12 = 512 * 34 * 12                        # tile rows 0-11 at G 33 (E628's zero region)
U_TRI, U_RAMP = 19, 49                       # E625's page need, read on r19-dpm's kept peaks


def hx(v):
    return f"0x{v:x}"


def g_of(ctl):
    """CR_ISP_ZLSCTL bits 11:3 (E465)."""
    return ctl >> 3 & 0x1FF


def marker(k):
    return 0xD0200000 + k


def raised(p, u):
    """E625: the first abort's threshold is raised iff 2 (P - 0x22) < U + 2."""
    return 2 * (p - D_OFF) < u + 2


def rt(args):
    return f"0 {LEAD} {RT} -- {T18} {args}"


def dbg_p(p):
    return f"dbg:render_pb_pages={hx(p)}"


def row(name, sset, knobs, args, **meta):
    return dict(name=name, set=sset, risk="safe", knobs=" ".join(knobs.split()), tool="rt",
                args=rt(args), **meta)


# ---- zc ----------------------------------------------------------------------------------------
def dl_args(ctl, k):
    """E628's dl form, -n 1 (r19-dpm's dz-ac rows, here on t18b)."""
    return (f"{NL1} {Z05} --depth --depth-ctl {hx(ctl)} --depth-fill index "
            f'--depth-dump "$W" --depth-store --depth-store-fill {hx(marker(k))}')


def zc_rows():
    geo = (f"{GEO} {Z05} --depth --depth-ctl {hx(NL33)} --depth-ctl-next {hx(NL33)} --depth-fill "
           f'index --depth-dump "$W" --depth-store --depth-store-fill 0xd0190003')
    return [
        # E1081's dz-a-nl28-1 unchanged (its marker too): the store after the final is the store
        # after render 1, one partial render
        row("zc-geo", "control", f"dbg:render_pb_pages=0x28 expectdiff {PREMISE} ctl:ssame=1 "
            "ctl:nparts=1 reads:ovf1,ovf2,thr,ssame,nparts", geo, ctl=NL33, p=0x28, geo=True),
        row("zc-nl", "control", "dbg:render_pb_pages=0x422 expectdiff ctl:ovf1=0 ctl:sidx=0 "
            "reads:ovf1,sidx", dl_args(NL33, 1), ctl=NL33, p=0x422, geo=False),
        row("zc-ld", "control", "dbg:render_pb_pages=0x422 expectdiff ctl:ovf1=0 ctl:sidx=1 "
            "reads:ovf1,sidx", dl_args(LD33, 2), ctl=LD33, p=0x422, geo=False),
    ]


# ---- zr ----------------------------------------------------------------------------------------
def r_args(ctl, k, move=True):
    mv = f" --move 2:{MOVE},0" if move else ""
    return (f"{GEO} {Z05} --depth --depth-ctl {hx(ctl)} --depth-ctl-next {hx(ctl)} --depth-pages "
            f"{hx(DPAGES)} --depth-fill {hx(ONE)} --depth-dump \"$W\" --depth-store "
            f"--depth-store-fill {hx(marker(k))} {REFILL}{mv}")


ZR = (("zr-28-nl-1", "fit", 0x28, NL33, True), ("zr-28-nl-2", "fit", 0x28, NL33, True),
      ("zr-28-ld", "fit", 0x28, LD33, True), ("zr-2c-nl", "heldout", 0x2C, NL33, True),
      ("zr-28-nm", "heldout", 0x28, NL33, False), ("zr-30-nl", "heldout", 0x30, NL33, True),
      ("zr-30-ld", "heldout", 0x30, LD33, True), ("zr-28-e336", "heldout", 0x28, E336, True))


def zr_rows():
    out, k = [], 10
    for n, s, p, c, mv in ZR:
        out.append(row(n, s, f"{dbg_p(p)} expectdiff {PREMISE} ctl:refill=1", r_args(c, k, mv),
                       ctl=c, p=p, geo=True, move=MOVE if mv else 0, fill=marker(k),
                       reading_only=c == E336, raised=raised(p, U_TRI)))
        k += 1
    return out


# ---- zm ----------------------------------------------------------------------------------------
def zm_rows():
    out = []
    for n, s, p in (("zm-28", "fit", 0x28), ("zm-2c", "heldout", 0x2C), ("zm-30", "heldout", 0x30)):
        out.append(row(n, s, f"{dbg_p(p)} expectdiff {PREMISE}", f"{GEO} --move 2:{MOVE},0", p=p,
                       geo=True, move=MOVE, raised=raised(p, U_TRI)))
    return out


# ---- zq ----------------------------------------------------------------------------------------
def z_args(c, k):
    return (f"{GEO} {RAMP} --depth --depth-ctl {hx(c)} --depth-ctl-next {hx(c)} --depth-fill "
            f'{hx(marker(k))} --depth-dump "$W"')


def zq_rows():
    out, k = [], 20
    for n, s, p, c, tw in (("zq-44-g33", "fit", 0x44, NL33, None), ("zq-44-g1", "fit", 0x44, NL1C,
                                                                   "zq-44-g33"),
                           ("zq-4c-g33", "heldout", 0x4C, NL33, None),
                           ("zq-4c-g1", "heldout", 0x4C, NL1C, "zq-4c-g33")):
        out.append(row(n, s, f"{dbg_p(p)} expectdiff {PREMISE}", z_args(c, k), g=g_of(c), p=p,
                       geo=True, twin=tw, fill=marker(k), raised=raised(p, U_RAMP)))
        k += 1
    return out


def tables():
    return {"zc": zc_rows(), "zr": zr_rows(), "zm": zm_rows(), "zq": zq_rows()}


def rows_by_name():
    return {r["name"]: r for rs in tables().values() for r in rs}


# ---- predictions (frozen before the run) -------------------------------------------------------
SRC = {
    "zc": "E628 (dl cells), E1081 (dz-a-nl28-1), E169 (ZLSCTL bit 0), rank-round20 3a",
    "zr": "E1081, E628, E629, E467, E625, E1083, rank-round20 3b",
    "zm": "E038/E311 (the final's background), render.c's sentinel fill, rank-round20 3c",
    "zq": "E629, E628, E625, E1082, q107_rule.py (E996, E1020), rank-round20 3d",
}
REGIME = ("raised iff TA3DCtl dword 38 of ta3d.1.bin is non-zero (E625, E1082); a row is scored "
          "under the regime read, not its label")


def predictions(st, rs):
    P = []

    def add(n, q, v, m, s):
        P.append((n, q, str(v), m, s, SRC[st]))

    for r in rs:
        n, s = r["name"], r["set"]
        if r.get("geo"):
            add(n, "ovf1", 1, "PREMISE", "control")
            add(n, "ovf2", 0, "PREMISE", "control")
            add(n, "thr", hx(THR_N), "PREMISE", "control")
        if st == "zc":
            if r["geo"]:
                add(n, "ssame", 1, "CTL", "control")
                add(n, "nparts", 1, "CTL", "control")
                add(n, "store2_eq_store1_window", "all", "CTL", "control")
            else:
                add(n, "ovf1", 0, "CTL", "control")
                add(n, "sidx", int(r["ctl"] == LD33), "CTL", "control")
                add(n, "zregs", f"0x0480={hx(r['ctl'])}|rd53.bit4, 0x0484=load, 0x0488=store",
                    "ZREGS", "reading")
        elif st == "zr":
            add(n, "refill", 1, "PREMISE", "control")
            add(n, "raised", int(r["raised"]), "E625", s)
            if r["reading_only"]:
                add(n, "zls_0480", "per render", "READING", "reading")
                continue
            ld = r["ctl"] == LD33
            if r["raised"]:
                add(n, "store2", "0.25 everywhere", "H-LOADBASE", s)
                add(n, "store2", "|store1|, 0.5 in T2 over 1.0", "H-STOREBASE", s)
                add(n, "store2", "store1", "H-NOSTORE", s)
            add(n, "store2", "0.25 everywhere" if ld else "0.5 in T2, 1.0 elsewhere", "H-HOSTBITS",
                s)
            add(n, "zls_0480_pr", hx(r["ctl"]) + "|rd53.bit4", "H-RDREG", "reading")
        elif st == "zm":
            add(n, "wrong", 0, "H-REPAINT", s)
            add(n, "other", ">0", "H-HOLES", s)
        elif st == "zq":
            add(n, "raised", 0, "E625", "control")
            if r["g"] == 33:
                add(n, "sign2|zero2_lo", "0|0", "H-NR-PLAIN", s)
                add(n, "zero2_lo", ">0", "H-AFTERPR", s)
            else:
                add(n, "rule", "all scored", "H-NR-PLAIN", s)
                add(n, "rule", "fewer", "H-AFTERPR", s)
    return P


HEAD = {
    "zc": ("zc (3, E1088): the controls every later stage is gated by. zc-geo (first): E1081's "
           "dz-a-nl28-1 unchanged (the store report after the final equals render 1's, one "
           "partial render; the scorer compares the dumps inside the store window); zc-nl, zc-ld: "
           "E628's -n 1 0x422 dl cells on t18b (the store holds the scene's depth, sidx 0 / the "
           "loaded indices, sidx 1). zregs (a reading control, never a stop): 0x0480 reads the poked "
           "control word (bit 0 as render details dword 53 bit 4, E169) with 0x0484 = the load "
           "buffer and 0x0488 = the store buffer, in one sample; if it fails, every register "
           "reading of the session is void. On a stop the session ends."),
    "zr": ("zr (8, E1088): Q088's reload half and Q038's store clauses. Render 1 overflows into a "
           "partial render (raised at 0x28, 0x2c; not at 0x30), the host writes 0.25 into the load "
           "buffer before the final (`--refill`, read as ctl:refill=1), the final draws T1 moved "
           "96 px right at z 0.5. On the store after the final, against the row's own store "
           "after render 1: H-LOADBASE (0.25 everywhere), H-STOREBASE (|store.1|, 0.5 in T2 over "
           "1.0), H-NOSTORE (store.1 dword for dword), H-HOSTBITS (the final's own word); a row "
           "that is not raised is scored by H-HOSTBITS's form under every model (the regime "
           "read, not the label). zr-28-e336 is a reading only. Gated by zc."),
    "zm": ("zm (3, E1089): the moved final without a depth buffer. The library writes its "
           "sentinel into the target before every kick (render.c), so the partial render's "
           "colour cannot survive to the final's check: H-REPAINT (wrong 0: the final paints "
           "every pixel) vs H-HOLES (pixels left at the sentinel, `other` > 0). Gated by zc."),
    "zq": ("zq (4, E1090): Q107 at P where the ramp overflows without a raise (0x44, 0x4c; E625 "
           "with U 49): H-NR-PLAIN (no sign, no zero row in depth.2; q107_rule's RULE holds on "
           "the G 1 dump against its G 33 twin) vs H-AFTERPR (zero row kept, RULE fails). "
           "The regime is read per row (not raised, else the row cannot tell). Gated by zc."),
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
