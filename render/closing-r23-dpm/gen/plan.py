#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""plan.py: r23-dpm's generator (round 23, the P2 rows of closing22/plan/rank-round22.md sections
2.3, 2.4 and 2.5; closing23/DECISIONS-R23.md, closing22/DECISIONS-R22.md all (a)). Writes
tables/STAGE.txt and predictions/STAGE.tsv for the three stages, in run order:

  rl  (10, E1099)  Q038's colour of a geometry final: E442's reload (bins/pds_bg_pos.bin:12 and
                   bins/bg_reload_1024.bin, E442's own bytes) in E1089's zm form (the moved final
                   on its own PB, no depth buffer) with --keep-target 2: H-RELOAD (every pixel the
                   final changes became its red: the background reload keeps render 1's colour)
                   against H-REPAINT (render 1's green is gone outside the final's triangle).
                   Controls: rl-c1 (E442's -n 1 image at 0x422: 207456 triangle, 578976 at the
                   sentinel) and rl-c2 (--keep-target 2 without the reload at 0x28: the library
                   background repaints all 786432 pixels, E1089's zm-28 colours)
  og  (6, E1100)   Q191's kick clause: the 64x64 owner (flag 0xc) closed early, the second
                   context's render 1 a geometry kick (--ctx2-geometry 1) with kept.geo.1.bin
                   between the kick and its closing render: H-TAKICK (E631's four owner words
                   already in kept.geo.1.bin) against H-RENDEREND (none there, all four in
                   kept.1.bin). Control og-4 (flag 0x4: no word in either copy)
  zn  (5, E1101)   Q088's not-raised load clause, frozen from E1093's zl-2e-ld (post hoc):
                   H-LOADNODRAW (load bits, not raised: the store after the final is the 0.75 load
                   at every hi window dword, T2 absent) against H-HOSTBITS (0.5 inside T2, 0.75
                   elsewhere). Control zn-c (E1093's zl-2e-nl form: H-HOSTBITS without load bits)

  python3 gen/plan.py          write the tables and predictions
  python3 gen/plan.py --check  exit 1 when a written file differs from what it would write

rl and zn run t22b under regtimeline with r21-zls's register list; og runs t22b alone. Every
geometry row (`tri -n 2 --geometry 1 --final-pb-pages 0x100`) reads its premise (`ctl:ovf1=1
ctl:ovf2=0 ctl:thr=0xde`, run/hooks.sh): one off stops the stage (rc 24). The not-raised window
for the triangle (U 19, E625): the kick overflows iff P - 0x22 < 19 and is raised iff 2 (P -
0x22) < 21, so 0x2e to 0x34 are the not-raised P that overflow (the plan's 0x38 does not overflow:
0x32 instead, README "Deviations")."""
from __future__ import annotations

import pathlib
import sys

KP = pathlib.Path(__file__).resolve().parent.parent

STAGES = ("rl", "og", "zn")
GATES: dict = {}          # no stage gates another; a FAILED control voids its own stage's headline
RECORDS = {"rl": "E1099", "og": "E1100", "zn": "E1101"}
RT = ("0x012c,0x0620-0x0628,0x0658,0x0660,0x0668,0x0700,0x070c-0x0710,0x0720-0x0734,0x0748,0x0a74,"
      "0x0480-0x0490")                       # r21-zls's register list, read only
LEAD = "0.3"
T22 = '"$HOME/sgxfive-test-t22b"'
N_FINAL = 0x100
D_OFF = 0x22
THR_N = N_FINAL - D_OFF                     # 0xde: the final render's ZLS threshold
COMMON = ('--keep-going --keep-overflow --wait-ms 20000 --dump-render "$W" --dump-each '
          '--words "$W" --regs 0x0600-0x0750')
GEO = (f"tri --width 1024 --height 768 -n 2 --geometry 1 --final-pb-pages 0x{N_FINAL:x} "
       + COMMON)
NL1 = "tri --width 1024 --height 768 -n 1 " + COMMON
PDS, PIX = "bins/pds_bg_pos.bin", "bins/bg_reload_1024.bin"
RELOAD = f'--bg-pds "$S/{PDS}:12" --bg-pixel "$S/{PIX}"'
KEEP = "--keep-target 2"
NL33, LD33 = 0x0017110C, 0x0017510E
Z05 = "--poke blk:1=0x00400200"                       # E461's z = 0.5 triangle
PREMISE = "ctl:ovf1=1 ctl:ovf2=0 ctl:thr=0x%x" % THR_N
ONE, HALF, R75 = 0x3F800000, 0x3F000000, 0x3F400000
MOVE = 96                                    # px right: 3 tiles of 32, the in-tile index kept
DPAGES = 0x340                               # the G 33 store's 1024x768 window in its buffer
W, H = 1024, 768
NPIX = W * H
ROW12 = 512 * 34 * 12                        # tile rows 0-11 at G 33: lo below, hi from here
U_TRI = 19                                   # E625's page need of the 1024x768 triangle
RED, GREEN, NAVY, SLATE, SENT = 0xFFFF0000, 0xFF00FF00, 0xFF000080, 0xFF203040, 0xDEADBEEF
T_PIX = 207456                               # the triangle's pixels at 1024x768 (E311, E442)
BG_PIX = NPIX - T_PIX                        # 578976
OWNER = {(1, 0): 0x00200047, (2, 0): 0x04000417, (3, 0): 0x00020001, (3, 1): 2}   # E631, E1087
OG_SIZE = 24576                              # a 64x64 context's kept TA data (E1087)
OG = ('tri --width 64 --height 64 -n 1 --keep-overflow --wait-ms 20000 --ctx2 '
      '--close-first-early --kept-copy "$W" --words "$W" --kpoke-render 1:ta:7^=0x%x '
      '--ctx2-geometry 1')


def hx(v):
    return f"0x{v:x}"


def raised(p, u=U_TRI):
    """E625: the first abort's threshold is raised iff 2 (P - 0x22) < U + 2."""
    return 2 * (p - D_OFF) < u + 2


def overflows(p, u=U_TRI):
    return p - D_OFF < u


def rt(args):
    return f"0 {LEAD} {RT} -- {T22} {args}"


def dbg_p(p):
    return f"dbg:render_pb_pages={hx(p)}"


def row(name, sset, knobs, tool, args, **meta):
    return dict(name=name, set=sset, risk="safe", knobs=" ".join(knobs.split()), tool=tool,
                args=args, **meta)


# ---- rl ----------------------------------------------------------------------------------------
RL = (("rl-28-a", "fit", 0x28), ("rl-28-b", "fit", 0x28), ("rl-2c-a", "heldout", 0x2C),
      ("rl-2c-b", "heldout", 0x2C), ("rl-30-a", "heldout", 0x30), ("rl-30-b", "heldout", 0x30),
      ("rl-34-a", "heldout", 0x34), ("rl-34-b", "heldout", 0x34))


def rl_rows():
    out = [
        # E442's 1024x768 0x422 reload cell on tri: the triangle and the sentinel elsewhere
        row("rl-c1", "control", "dbg:render_pb_pages=0x422 expectdiff ctl:ovf1=0 "
            "reads:ovf1,tri1,oth1,win1", "rt", rt(f"{NL1} {RELOAD}"), p=0x422, geo=False,
            reload=True),
        # E1089's zm-28 with the target kept and the library's background: every pixel repainted
        row("rl-c2", "control", f"dbg:render_pb_pages=0x28 expectdiff {PREMISE} "
            "reads:ovf1,ovf2,thr,chg,red2", "rt", rt(f"{GEO} {KEEP} --move 2:{MOVE},0"),
            p=0x28, geo=True, reload=False, raised=raised(0x28)),
    ]
    for n, s, p in RL:
        out.append(row(n, s, f"{dbg_p(p)} expectdiff {PREMISE}", "rt",
                       rt(f"{GEO} {RELOAD} {KEEP} --move 2:{MOVE},0"), p=p, geo=True,
                       reload=True, raised=raised(p)))
    return out


# ---- og ----------------------------------------------------------------------------------------
OGR = (("og-4", "control", 0x422, 0x4), ("og-c-a", "fit", 0x422, 0xC), ("og-c-b", "fit", 0x422, 0xC),
       ("og-c-c", "heldout", 0x422, 0xC), ("og-c-d", "heldout", 0x422, 0xC),
       ("og-p200", "heldout", 0x200, 0xC))


def og_rows():
    out = []
    for n, s, p, f in OGR:
        k = f"dbg:render_keep=1 {dbg_p(p)}" + (" reads:ovf1,kept,gsize" if s == "control" else "")
        out.append(row(n, s, k, "t22b", OG % f, p=p, flag=f))
    return out


# ---- zn ----------------------------------------------------------------------------------------
ZN = (("zn-c", "control", 0x2E, NL33), ("zn-2e-ld", "fit", 0x2E, LD33),
      ("zn-30-ld", "heldout", 0x30, LD33), ("zn-32-ld", "heldout", 0x32, LD33),
      ("zn-34-ld", "heldout", 0x34, LD33))


def marker(k):
    return 0xD0230000 + k


def z_args(ctl, fill):
    """r21-zls's zl form (E1093) byte for byte but the tool and the marker."""
    return (f"{GEO} {Z05} --depth --depth-ctl {hx(ctl)} --depth-ctl-next {hx(ctl)} --depth-pages "
            f"{hx(DPAGES)} --depth-fill {hx(ONE)} --depth-dump \"$W\" --depth-store "
            f"--depth-store-fill {hx(fill)} --refill 2:depth={hx(R75)} --move 2:{MOVE},0")


def zn_rows():
    out = []
    for k, (n, s, p, c) in enumerate(ZN, 1):
        rd = " reads:ovf1,ovf2,thr,refill" if s == "control" else ""
        out.append(row(n, s, f"{dbg_p(p)} expectdiff {PREMISE} ctl:refill=1{rd}", "rt",
                       rt(z_args(c, marker(k))), ctl=c, p=p, geo=True, refill=R75,
                       raised=raised(p)))
    return out


def tables():
    return {"rl": rl_rows(), "og": og_rows(), "zn": zn_rows()}


def rows_by_name():
    return {r["name"]: r for rs in tables().values() for r in rs}


# ---- predictions (frozen before the run) -------------------------------------------------------
SRC = {
    "rl": "E442, E1089 (zm-28, zm-2c, zm-30), E625, E311, rank-round22 2.3",
    "og": "E631, E1087 (own1 o1-4, o1-c-a to o1-c-d, o1-p200), E1085, rank-round22 2.4",
    "zn": "E1093 (zl-2e-ld post hoc, zl-2e-nl), E1088, E625, rank-round22 2.5",
}


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
        if st == "rl":
            if n == "rl-c1":
                add(n, "ovf1", 0, "CTL", "control")
                add(n, "tri1|win1|oth1", f"{T_PIX}|0|{BG_PIX}", "CTL", "control")
                continue
            if n == "rl-c2":
                add(n, "chg", NPIX, "CTL", "control")
                add(n, "colours2", f"{hx(RED)} {T_PIX}, {hx(NAVY)} {BG_PIX}", "CTL", "control")
                continue
            add(n, "raised", int(r["raised"]), "E625", "reading")
            add(n, "chg", "= red2 (every changed pixel became red)", "H-RELOAD", s)
            add(n, "colours2", "red, green and the sentinel only; green > 0", "H-RELOAD", s)
            add(n, "chg", "> red2", "H-REPAINT", s)
            add(n, "colours2", "no green", "H-REPAINT", s)
            add(n, "red2", T_PIX if r["raised"] else f"> {T_PIX} (E1089 zm-30: + 18582)",
                "E1089", "reading")
        elif st == "og":
            if s == "control":
                add(n, "ovf1", 0, "CTL", "control")
                add(n, "kept", "3 (2 if the copy after the close reads empty)", "CTL", "control")
                add(n, "gsize", OG_SIZE, "CTL", "control")
                add(n, "owner_words_geo|owner_words_after", "0|0", "CTL", "control")
                continue
            add(n, "owner_words_geo|owner_words_after", "4|4", "H-TAKICK", s)
            add(n, "owner_words_geo|owner_words_after", "0|4", "H-RENDEREND", s)
            add(n, "owner_words_closed", "0 (E1087)", "E1087", "reading")
        elif st == "zn":
            add(n, "raised", int(r["raised"]), "E625", "reading" if s == "control" else s)
            if s == "control":
                add(n, "store2_hi", "0.5 inside T2, 0.5 or 1.0 in T1 \\ T2, 1.0 elsewhere",
                    "CTL", "control")
                continue
            add(n, "store2_hi", "0.75 everywhere (the load written back, T2 absent)",
                "H-LOADNODRAW", s)
            add(n, "store2_hi", "0.5 inside T2, 0.75 elsewhere", "H-HOSTBITS", s)
    return P


HEAD = {
    "rl": ("rl (10, E1099, Q038): E442's reload in a geometry final. Every row but rl-c1 is E1089's "
           "zm form (1024x768 -n 2 --geometry 1 --final-pb-pages 0x100, the final moved 96 px, no "
           "depth buffer) with --keep-target 2: render 2 starts on render 1's target and the tool "
           "counts its pixels against render 1's readback (`tri 1024x768 #2: target kept, X pixels "
           "changed, colours ...`). Frozen: H-RELOAD (X = the red count, only red, green and the "
           "sentinel 0xdeadbeef, green > 0: the reload keeps render 1's colour) vs H-REPAINT (X > "
           "red, no green). Controls: rl-c1 (E442's -n 1 0x422 cell: 207456 triangle, wrong 0 "
           "inside, 578976 other) and rl-c2 (no reload at 0x28: X = 786432, red 207456, 0xff000080 "
           "578976). A FAILED control voids the stage's headlines."),
    "og": ("og (6, E1100, Q191 kick clause): E1087's 64x64 own1 form with --ctx2-geometry 1: the "
           "second context's render 1 is a geometry kick, kept.geo.1.bin is copied before its "
           "closing render. Frozen: H-TAKICK (E631's four owner words, control page 1 dword 0 "
           "0x00200047, OTPM page 2 dword 0 0x04000417, state page 3 dwords 0, 1 0x00020001, 2, "
           "all in kept.geo.1.bin) vs H-RENDEREND (none there, all four in kept.1.bin). Control "
           "og-4 (flag 0x4): no owner word in either copy. An empty copy is counted (cannot tell), "
           "never a stop; a missing closing render or copy after it stops the stage."),
    "zn": ("zn (5, E1101, Q088): r21-zls's zl form (E1093) at not-raised P with load bits "
           "0x0017510e: 0x2e (fit, E1093's zl-2e-ld again), 0x30, 0x32, 0x34 (held out). On the "
           "store after the final, hi region only: H-LOADNODRAW (0.75 at every hi window dword) vs "
           "H-HOSTBITS (0.5 inside T2, 0.75 elsewhere); a row read raised (ta3d.1.bin dword 38) "
           "cannot tell. Control zn-c (E1093's zl-2e-nl form, no load bits): 0.5 inside T2, 0.5 "
           "or 1.0 in T1 \\ T2, 1.0 elsewhere."),
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
                  key=lambda v: int(v, 16) if v.startswith("0x") else int(v))


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
