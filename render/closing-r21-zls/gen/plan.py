#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""plan.py: r21-zls's generator (round 21, S1: Q088's reload half and what reads the render
details' ZLS word, Q107's zero-row count; closing21/plan/rank-round21.md section 3;
closing21/DECISIONS-R21.md). Writes tables/STAGE.txt and predictions/STAGE.tsv for the four
stages, in run order:

  zc  (2, E1093)  controls: E1088's zr-28-nl-1 again byte for byte (zc-r25: the store after the
                  final is the refilled 0.25 at every hi window dword, store.1 = depth.1 there),
                  then r20's zc-nl (E628's -n 1 0x422 dl cell without load bits: sidx 0). zregs2
                  (0x0484 = rd:12, 0x0488 = rd:13 in every non-zero sample from the first partial
                  render on, zc-r25) is a reading control: if it fails only the register readings
                  (H-PRMASK, zl's and zw's) are void
  zl  (7, E1093)  Q088's reload half at R 0.75: H-LOADTEST vs H-LOADNOTEST on raised rows,
                  H-HOSTBITS on not-raised rows, the store after the final, hi region only
  zw  (3, E1094)  what reads the word: H-PRMASK (0x0480 during the partial renders = rd:11 |
                  0x000c4000) vs H-PR1419 (rd:11 | 0x00084000) vs H-OTHER, on E336's word at a
                  raised and a not-raised P and on E1082's G 1 word
  zz  (4, E1095)  Q107's zero-row count (optional, narrow): H-ZCOUNT (depth.2's zero window
                  dwords in tile rows 0-11: 184320 raised, 118784 not raised, none signed) vs H-ZP

  python3 gen/plan.py          write the tables and predictions
  python3 gen/plan.py --check  exit 1 when a written file differs from what it would write

Every geometry row (t18b under regtimeline): `tri -n 2 --geometry 1 --final-pb-pages 0x100`, the
kick overflows at P, the final does not: its premise (`ctl:ovf1=1 ctl:ovf2=0 ctl:thr=0xde`,
run/hooks.sh) is read on every geometry row and one off stops the stage (rc 24); the refill rows
also read `ctl:refill=1`. Every depth row passes `--depth-ctl-next` (else the host refills before
the final). regtimeline samples r20-zls's register set (0x0480-0x0490 included, read only)."""
from __future__ import annotations

import pathlib
import sys

KP = pathlib.Path(__file__).resolve().parent.parent

STAGES = ("zc", "zl", "zw", "zz")
GATES = {"zl": "zc", "zw": "zc", "zz": "zc"}   # the plan: zc's store controls off, nothing runs
RECORDS = {"zc": "E1093", "zl": "E1093", "zw": "E1094", "zz": "E1095"}
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
ONE, HALF, R75, QUARTER = 0x3F800000, 0x3F000000, 0x3F400000, 0x3E800000
MOVE = 96                                    # px right: 3 tiles of 32, the in-tile index kept
DPAGES = 0x340                               # the G 33 store's 1024x768 window in its buffer
W, H = 1024, 768
ROW12 = 512 * 34 * 12                        # tile rows 0-11 at G 33: lo below, hi from here
U_TRI, U_RAMP = 19, 49                       # E625's page need, read on r19-dpm's kept peaks
PRMASK, PR1419 = 0x000C4000, 0x00084000      # H-PRMASK's bits 14, 18, 19; the rival's 14, 19
ZC_RAISED, ZC_NOT = 184320, 118784           # H-ZCOUNT, window dwords (E1082's 0x28/0x30, E1090)


def hx(v):
    return f"0x{v:x}"


def g_of(ctl):
    """CR_ISP_ZLSCTL bits 11:3 (E465)."""
    return ctl >> 3 & 0x1FF


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


def r_args(ctl, fill, refill):
    """r20-zls's zr form (rank-round21 section 3's common form)."""
    return (f"{GEO} {Z05} --depth --depth-ctl {hx(ctl)} --depth-ctl-next {hx(ctl)} --depth-pages "
            f"{hx(DPAGES)} --depth-fill {hx(ONE)} --depth-dump \"$W\" --depth-store "
            f"--depth-store-fill {hx(fill)} --refill 2:depth={hx(refill)} --move 2:{MOVE},0")


# ---- zc ----------------------------------------------------------------------------------------
def zc_rows():
    nl = (f"{NL1} {Z05} --depth --depth-ctl {hx(NL33)} --depth-fill index "
          f'--depth-dump "$W" --depth-store --depth-store-fill 0xd0200001')
    return [
        # E1088's zr-28-nl-1 byte for byte (its marker 0xd020000a too)
        row("zc-r25", "control", f"dbg:render_pb_pages=0x28 expectdiff {PREMISE} ctl:refill=1 "
            "reads:ovf1,ovf2,thr,refill", r_args(NL33, 0xD020000A, QUARTER), ctl=NL33, p=0x28,
            geo=True, refill=QUARTER, raised=raised(0x28, U_TRI)),
        # r20-zls's zc-nl byte for byte (E628's dl cell without load bits, E1081's dz-ac-nl)
        row("zc-nl", "control", "dbg:render_pb_pages=0x422 expectdiff ctl:ovf1=0 ctl:sidx=0 "
            "reads:ovf1,sidx", nl, ctl=NL33, p=0x422, geo=False),
    ]


# ---- zl ----------------------------------------------------------------------------------------
ZL = (("zl-28-nl", "fit", 0x28, NL33), ("zl-24-nl", "heldout", 0x24, NL33),
      ("zl-2a-ld", "heldout", 0x2A, LD33), ("zl-2c-nl", "heldout", 0x2C, NL33),
      ("zl-2e-nl", "heldout", 0x2E, NL33), ("zl-2e-ld", "heldout", 0x2E, LD33),
      ("zl-34-nl", "heldout", 0x34, NL33))


def marker(k):
    return 0xD0210000 + k


def zl_rows():
    out = []
    for k, (n, s, p, c) in enumerate(ZL, 1):
        out.append(row(n, s, f"{dbg_p(p)} expectdiff {PREMISE} ctl:refill=1",
                       r_args(c, marker(k), R75), ctl=c, p=p, geo=True, refill=R75,
                       raised=raised(p, U_TRI)))
    return out


# ---- zw ----------------------------------------------------------------------------------------
ZW = (("zw-2c-e336", 0x2C, E336), ("zw-2e-e336", 0x2E, E336), ("zw-28-g1", 0x28, NL1C))


def zw_rows():
    out = []
    for k, (n, p, c) in enumerate(ZW, 0x10):
        out.append(row(n, "heldout", f"{dbg_p(p)} expectdiff {PREMISE} ctl:refill=1",
                       r_args(c, marker(k), R75), ctl=c, p=p, geo=True, refill=R75,
                       raised=raised(p, U_TRI)))
    return out


# ---- zz ----------------------------------------------------------------------------------------
def z_args(c, fill):
    """r20-zls's zq form (E629's ramp, G 33 on both renders, no refill, no move)."""
    return (f"{GEO} {RAMP} --depth --depth-ctl {hx(c)} --depth-ctl-next {hx(c)} --depth-fill "
            f'{hx(fill)} --depth-dump "$W"')


ZZ = (("zz-24", 0x24), ("zz-38", 0x38), ("zz-3c", 0x3C), ("zz-50", 0x50))


def zz_rows():
    out = []
    for k, (n, p) in enumerate(ZZ, 0x20):
        out.append(row(n, "heldout", f"{dbg_p(p)} expectdiff {PREMISE}", z_args(NL33, marker(k)),
                       ctl=NL33, p=p, geo=True, raised=raised(p, U_RAMP)))
    return out


def tables():
    return {"zc": zc_rows(), "zl": zl_rows(), "zw": zw_rows(), "zz": zz_rows()}


def rows_by_name():
    return {r["name"]: r for rs in tables().values() for r in rs}


# ---- predictions (frozen before the run) -------------------------------------------------------
SRC = {
    "zc": "E1088 (zr-28-nl-1, look.out), E628, E1081 (dz-ac-nl), rank-round21 3a",
    "zl": "E1088, E1081, E625, E465, rank-round21 3b",
    "zw": "E1088 (look.out: four kept words), E336, E1082, E169, rank-round21 3c",
    "zz": "E629, E625, E1082 (zs 0x28, 0x30), E1090 (zq 0x44, 0x4c), rank-round21 3d",
}


def prmask_word(c, mask=PRMASK):
    return c | mask


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
            if "refill" in r:
                add(n, "refill", 1, "PREMISE", "control")
        if st == "zc":
            if r["geo"]:
                add(n, "store2_hi", "0.25 at every hi window dword", "CTL", "control")
                add(n, "store1_eq_depth1_hi", "all", "CTL", "control")
                add(n, "zregs2", "0x0484=rd:12, 0x0488=rd:13 in every non-zero sample", "H-OFFS",
                    "reading")
            else:
                add(n, "ovf1", 0, "CTL", "control")
                add(n, "sidx", 0, "CTL", "control")
        elif st == "zl":
            add(n, "raised", int(r["raised"]), "E625", s)
            ld = r["ctl"] == LD33
            if r["raised"]:
                add(n, "store2_hi", "0.5 inside T2, 0.75 elsewhere", "H-LOADTEST", s)
                add(n, "store2_hi", "0.75 everywhere", "H-LOADNOTEST", s)
                add(n, "final_check_wrong_inside", 0, "H-LOADTEST", "reading")
            else:
                add(n, "store2_hi", "0.5 inside T2, 0.75 elsewhere" if ld else
                    "0.5 inside T2, 0.5 or 1.0 in T1 \\ T2, 1.0 elsewhere", "H-HOSTBITS", s)
            add(n, "zls_0480_pr", hx(prmask_word(r["ctl"])) + " (>= 80 %, else rd:11)",
                "H-PRMASK", "reading")
        elif st == "zw":
            add(n, "raised", int(r["raised"]), "E625", "reading")
            add(n, "zls_0480_pr", hx(prmask_word(r["ctl"])) + " (>= 80 %, else rd:11)",
                "H-PRMASK", s)
            add(n, "zls_0480_pr", hx(prmask_word(r["ctl"], PR1419)) + " (>= 80 %, else rd:11)",
                "H-PR1419", s)
            add(n, "zls_0480_pr", "any other", "H-OTHER", s)
        elif st == "zz":
            add(n, "raised", int(r["raised"]), "E625", s)
            add(n, "zero2_lo|sign2", f"{ZC_RAISED if r['raised'] else ZC_NOT}|0", "H-ZCOUNT", s)
            add(n, "zero2_lo", "any other", "H-ZP", s)
    return P


HEAD = {
    "zc": ("zc (2, E1093): the controls every later stage is gated by. zc-r25 (first): E1088's "
           "zr-28-nl-1 byte for byte (P 0x28 raised, 0x0017110c, refill 0.25, move 96): the store "
           "after the final is 0.25 at every window dword of tile rows 12 and below (hi) and the "
           "store after render 1 equals the load buffer there. zc-nl: r20's E628 -n 1 0x422 dl "
           "cell without load bits (sidx 0). zregs2 (a reading control, never a stop): on zc-r25 "
           "every sample from the first partial render on with a non-zero 0x0480-0x0488 reads "
           "0x0484 = rd:12 and 0x0488 = rd:13; if it fails, the register readings (H-PRMASK) are "
           "void. On a stop the session ends."),
    "zl": ("zl (7, E1093): Q088's reload half at refill 0.75 (`--refill 2:depth=0x3f400000`, read "
           "as ctl:refill=1). On the store after the final, hi region only: a raised row (TA3DCtl "
           "dword 38 of ta3d.1.bin non-zero, read, not the label) scores H-LOADTEST (0.5 inside "
           "T2, 0.75 elsewhere) against H-LOADNOTEST (0.75 everywhere); a not-raised row scores "
           "H-HOSTBITS (load bits: as H-LOADTEST; none: 0.5 inside T2, 0.5 or 1.0 in T1 \\ T2, "
           "1.0 elsewhere). H-PRMASK on every row (void if zregs2 fails). Gated by zc."),
    "zw": ("zw (3, E1094): what reads the render details' word. During the partial renders "
           "(0x0658 bit 0) at least 80 % of the 0x0480 samples read rd:11 | 0x000c4000 and none "
           "anything but that or rd:11 (H-PRMASK), vs rd:11 | 0x00084000 (H-PR1419) and H-OTHER, "
           "rd:11 from words.1.txt. E336's 0x0011700a at a raised (0x2c) and a not-raised (0x2e) "
           "P, E1082's G 1 word 0x0017100c at 0x28. Stores are readings. Void if zregs2 fails. "
           "Gated by zc."),
    "zz": ("zz (4, E1095, optional, narrow): E629's ramp as r20's zq. H-ZCOUNT: depth.2 holds "
           "184320 zero window dwords in tile rows 0-11 when the kick is raised (read: TA3DCtl "
           "dword 38) and 118784 when not, and no signed window dword; H-ZP: any other count. "
           "Gated by zc."),
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
