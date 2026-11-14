#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""plan.py: r19-k0's generator (round 19 S1, closing19/plan/rank-round19.md section 2): the rows of
stages k0 (E1077) and f0 (E1078), their frozen predictions, and the constants the reader, the
scorer, the hooks' tests and the mock share. `python3 gen/plan.py` writes tables/STAGE.txt and
predictions/STAGE.tsv; tests/test_plan.py holds them current.

k0: does module E0CC4027 with render_final_pb_pages at 0 run B60AB0B4's jobs byte for byte
(H-SAME against H-DIFF)? Kept twins: r13-dpm pr2-c1/pr2-c4 (3072x2048, t10, rt), r10-dpm (and
r9-ldpm, equal) a0-cal-2048 (rgn4; the builder's library-mock scene check, debug/scenecheck, gave
rgn4, t10 and t18b the same job image byte for byte, so t10 runs it), r13-zls zb-c-ctl (64x32
ZLS store, t10; t18b too), and the geometry form t10 against t18b on this module (no kept twin).

f0: does the EDM apply a TA command's thresholds (flag 0x2000, dwords 10-13) before that kick's
TA? H-UPD (applied at the final kick), H-IGN (ignored), H-LATE (stored, applied only later),
H-STICK (f0-back: N's kept into the next scene), H-STORE (the descriptor's pb:10-13 hold the
command's thresholds after the final kick) [infer: edm_dataflow.md's reading, never run]."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)

STAGES = ("k0", "kg", "f0")
# r13-dpm's register set plus 0x0620 and 0x0668 (the TA and PDS thresholds), plan section 2
RT = ("0x012c,0x0620-0x0628,0x0658,0x0660,0x0668,0x0700,0x070c-0x0710,0x0720-0x0734,0x0748,"
      "0x0a74")
RTPRE = f"0 0.3 {RT} -- "
T10 = '"$HOME/sgxfive-test-t10"'
T18B = '"$HOME/sgxfive-test-t18b"'
PROG = '"$S/bins/p1139-green.bin"'
D_OFF = 0x22                       # ZLS = global threshold = P - 0x22 (thr0)
RAISE = 0x20                       # E625: the threshold raised once by 0x20
REGS = "0x0600-0x0750"             # --regs at every --words snapshot (0x0624 among them)
GEO = ("--keep-going --keep-overflow --wait-ms 20000 --dump-render \"$W\" --dump-each "
       f"--words \"$W\" --regs {REGS}")

# kept twins (data 95df71e98)
A0_PARAM = "e366ead787d9c084e9bb4af38c40b89fedee943e0b75b680a17afa9dd80fec3b"
A0_TADATA = "ddf914f07fc9cda166deab6219d2e9af1cf3ee2ac02ee2a849d4424a28df408a"
A0_S = {2: 0x51, 3: 0x9D, 4: 0xE8, 5: 0x132}          # r9-ldpm and r10-dpm a0-cal-2048, equal
Z_DSHA = "92f04c7ca9c6de014a49e509fc8773530a211050cae18cfe47fef084d3a0e7c1"
Z_ARGS = ("tri --keep-going --wait-ms 20000 --width 64 --height 32 --max-width 64 --max-height 32 "
          "--tri-full --tri-z 0.5,0.5,0.5 --depth --depth-ctl 0x0017500e --depth-fill 0x3f400000 "
          "--depth-store --depth-dump \"$W\" --poke blk:1=0x00400200 --pixels "
          "--kpoke-render 1:rd:12=0x1000")
PR_ARGS = f"probe --tri pixel --width 3072 --height 2048 --vertices 1500 {PROG}"
A0_ARGS = f"probe --tri pixel --width 2048 --height 2048 --vertices 1500 --dump-render \"$W\" {PROG}"
GEO_ARGS = f"tri --width 1024 --height 768 -n 2 --geometry 1 {GEO}"

KNOB_VALUES = ("0x2b6", "0xe2", "0x162", "0x28", "0x30", "0x24", "0x100", "0x422")


def thr(p):
    return p - D_OFF


def pds(p):
    g = thr(p)
    return g - 0x100 if g > 0x100 else 0


def pb_words(p, n):
    """pb:10-13 after a final kick that applied N's thresholds (sgx_render_pb_thresholds of the
    fork 456404fcffe5: TA = list + 0x10, list = max(P, N); ZLS = global = N - 0x22; PDS)."""
    lst = max(p, n)
    return (lst + 0x10, thr(n), thr(n), pds(n))


def hx(v):
    return f"0x{v:x}"


# ---- rows: (name, set, risk, knobs, tool, args, {quantity: {model: value}}, source) -----------
def k0_rows():
    """Stage k0 (6 rows, the kept twins of B60AB0B4): every row a control but k0-pr4. Its files
    are read by the hooks into readings.tsv (dsha, param, tadata): the scorer reads only .txt."""
    pr = {"nparts": {"CTL": "1", "H-SAME": "1"}, "knob": {"CTL": "0x294", "H-SAME": "0x294"}}
    z = {"drawn": {"CTL": "2048", "H-SAME": "2048"}, "dst": {"CTL": "2048", "H-SAME": "2048"},
         "dsha": {"CTL": Z_DSHA[:16], "H-SAME": Z_DSHA}}
    zk = f"expectdiff reads:drawn,dst,dsha ctl:drawn=2048 ctl:dst=2048 ctl:dsha={Z_DSHA[:16]}"
    prk = "dbg:render_pb_pages=0x2b6 expect:rc3-overflow"
    a0k = (f"dbg:render_pb_pages=0x162 expect:rc3-overflow reads:param,tadata,knob "
           f"ctl:param={A0_PARAM[:16]} ctl:tadata={A0_TADATA[:16]}")
    src_pr = "r13-dpm pr2-c1-1/2 (B60AB0B4, t10): 1 partial render, knob 0x294"
    src_z = "r13-zls zb-c-ctl (B60AB0B4, t10): depth-store.1.bin sha256, 2048 drawn and stored"
    return [
        ("k0-pr1-1", "control", "safe", f"{prk} reads:nparts,knob ctl:nparts=1 ctl:knob=0x294", "rt",
         RTPRE + f"{T10} {PR_ARGS}", pr, src_pr),
        ("k0-z-t10", "control", "safe", zk, "t10", Z_ARGS, z, src_z),
        ("k0-a0", "control", "safe", a0k, "rt", RTPRE + f"{T10} {A0_ARGS}",
         {"param": {"CTL": A0_PARAM[:16], "H-SAME": A0_PARAM},
          "tadata": {"CTL": A0_TADATA[:16], "H-SAME": A0_TADATA}, "nparts": {"H-SAME": "1"},
          "knob": {"H-SAME": "0x140"}, **{f"s{k}": {"H-SAME": hx(v)} for k, v in A0_S.items()}},
         "r9-ldpm and r10-dpm a0-cal-2048 (rgn4, equal; the builder's scene check gave t10 and t18b "
         "rgn4's job byte for byte, so a control: rank-round19.md 2a [check])"),
        ("k0-pr1-2", "control", "safe", f"{prk} reads:nparts,knob ctl:nparts=1 ctl:knob=0x294", "rt",
         RTPRE + f"{T10} {PR_ARGS}", pr, src_pr),
        ("k0-z-t18b", "control", "safe", zk, "t18b", Z_ARGS, z, src_z + "; t18b's depth path is t10's"),
        ("k0-pr4", "heldout", "safe", "dbg:render_pb_pages=0xe2 expect:rc3-overflow", "rt",
         RTPRE + f"{T10} {PR_ARGS}", {"nparts": {"H-SAME": "4"}, "knob": {"H-SAME": "0xc0"}},
         "r13-dpm pr2-c4-1/2 (B60AB0B4, t10): 4 partial renders, knob 0xc0"),
    ]


def kg_rows():
    """Stage kg (4 rows, E1077's geometry form): t10 against t18b on this module, no kept twin."""
    geo = {"ovf1": {"H-SAME": "1"}, "knob": {"H-SAME": "0x6"}, "d35": {"H-E625": "0x4"},
           "d37": {"H-E625": "0x10006"}, "d38": {"H-E625": "0x20"},
           "pb1": {"H-SAME": "0x38,0x6,0x6,0x0"}, "same": {"H-SAME": "k0-geo-t10-1"}}
    geoc = {**geo, "ovf1": {"CTL": "1", "H-SAME": "1"}, "knob": {"CTL": "0x6", "H-SAME": "0x6"}}
    gk = "dbg:render_pb_pages=0x28 expectdiff"
    src_g = ("E625 (1024x768 U = 19 raised at P 0x23-0x2c, dword 35 thr0 - 2, 37 1 << 16 | thr0, 38 "
             "0x20); pb:10-13 the fork's thresholds at P 0x28; t18b's job = t10's (scene check)")
    return [
        ("k0-geo-t10-1", "control", "safe", f"{gk} reads:ovf1,knob ctl:ovf1=1 ctl:knob=0x6", "rt",
         RTPRE + f"{T10} {GEO_ARGS}", {k: v for k, v in geoc.items() if k != "same"}, src_g),
        ("k0-geo-t18b-1", "control", "safe", f"{gk} reads:ovf1,knob ctl:ovf1=1 ctl:knob=0x6", "rt",
         RTPRE + f"{T18B} {GEO_ARGS}", geoc, src_g),
        ("k0-geo-t10-2", "heldout", "safe", gk, "rt", RTPRE + f"{T10} {GEO_ARGS}", geo,
         "a replicate of k0-geo-t10-1; " + src_g),
        ("k0-geo-t18b-2", "heldout", "safe", gk, "rt", RTPRE + f"{T18B} {GEO_ARGS}", geo,
         "a replicate of k0-geo-t18b-1; " + src_g),
    ]


def f0_row(name, sset, risk, p, n, extra, nrend=2):
    """One f0 row: the geometry kick at P (dbg:render_pb_pages), the final at N."""
    knobs = f"dbg:render_pb_pages={hx(p)} expectdiff" + (f" {extra}" if extra else "")
    geo = "--geometry 1"
    args = (f"tri --width 1024 --height 768 -n {nrend} {geo} --final-pb-pages {hx(n)} {GEO}")
    return name, sset, risk, knobs, "rt", RTPRE + f"{T18B} {args}"


def f0_preds(p, n, back=False):
    """H-UPD's values (the kernel's arithmetic, fork 456404fcffe5) and the rivals' where they are
    fixed numbers. U = 19 pages at 1024x768 (E625): the geometry kick overflows iff P - 0x22 < 19.
    A final after a geometry kick that overflowed holds a few pages (2 left by the partial render,
    E625 gps_left, plus the second triangle's, a few) [infer], so it does not overflow at N - 0x22
    >= 0x3e; at N 0x30 (f0-down) it holds the 19 pages the geometry kick took, past the threshold
    0xe, and aborts at its first allocation [infer]. (The plan's N 0x28 became 0x30: the library
    mock overflows a 1024x768 final below 0x30 and the kit takes a kept overflow's `failed:` line
    for an unexpected end; 0x30 keeps the threshold below the pages the open scene holds.)"""
    ovf1 = int(thr(p) < 19)
    d = {"ovf1": {"H-UPD": str(ovf1), "H-IGN": str(ovf1), "H-LATE": str(ovf1)},
         "thr2": {"H-UPD": hx(thr(n)), "H-LATE": hx(thr(n)), "H-IGN": f"{hx(thr(p))}|{hx(thr(p) + RAISE)}"},
         "pb2": {"H-STORE": ",".join(hx(x) for x in pb_words(p, n)),
                 "H-NOSTORE": ",".join(hx(x) for x in (max(p, n) + 0x10, thr(p), thr(p), pds(p)))}}
    up = thr(n) >= 0x3E
    d["ovf2"] = {"H-UPD": "0" if up else "1"}
    d["nparts"] = {"H-UPD": str(ovf1 + (0 if up else 1)) if up else f">={ovf1 + 1}"}
    if not up:          # f0-down: the rivals complete the final at P's threshold 0xde
        d["ovf2"].update({"H-IGN": "0", "H-LATE": "0"})
        d["thr2"]["H-UPD"] = f"{hx(thr(n))}|{hx(thr(n) + RAISE)}"
        d["thr2"]["H-IGN"] = hx(thr(p))
        d["thr2"]["H-LATE"] = f"{hx(thr(n))}|{hx(thr(n) + RAISE)}"
    if back:
        d["ovf3"] = {"H-UPD": "1", "H-STICK": "0"}
        d["thr3"] = {"H-UPD": f"{hx(thr(p))}|{hx(thr(p) + RAISE)}", "H-STICK": hx(thr(n))}
        d["nparts"] = {"H-UPD": str(ovf1 + 1)}
    return d


F0 = (  # name, set, risk, P, N, extra knobs, renders, ctl words / reads
    ("f0-same-1", "control", "safe", 0x422, 0x200,
     "reads:ovf1,ovf2,thr2 ctl:ovf1=0 ctl:ovf2=0 ctl:thr2=0x1de", 2),
    ("f0-up-1", "control", "safe", 0x28, 0x100, "reads:ovf1,thr2 ctl:ovf1=1 ctl:thr2=0xde", 2),
    ("f0-same-2", "control", "safe", 0x422, 0x200,
     "reads:ovf1,ovf2,thr2 ctl:ovf1=0 ctl:ovf2=0 ctl:thr2=0x1de", 2),
    ("f0-up-2", "control", "safe", 0x28, 0x100, "reads:ovf1,thr2 ctl:ovf1=1 ctl:thr2=0xde", 2),
    ("f0-up-h1-1", "heldout", "safe", 0x30, 0x60, "", 2),
    ("f0-up-h2-1", "heldout", "safe", 0x24, 0x422, "", 2),
    ("f0-back-1", "heldout", "safe", 0x28, 0x100, "", 3),
    ("f0-up-h1-2", "heldout", "safe", 0x30, 0x60, "", 2),
    ("f0-up-h2-2", "heldout", "safe", 0x24, 0x422, "", 2),
    ("f0-back-2", "heldout", "safe", 0x28, 0x100, "", 3),
    ("f0-down-1", "heldout", "medium", 0x100, 0x30, "soft stop:jobfail", 2),
    ("f0-down-2", "heldout", "medium", 0x100, 0x30, "soft stop:jobfail", 2),
)


def f0_rows():
    out = []
    for name, sset, risk, p, n, extra, nr in F0:
        r = f0_row(name, sset, risk, p, n, extra, nr)
        pr = f0_preds(p, n, back=nr == 3)
        if sset == "control":
            for w in extra.split():
                if w.startswith("ctl:"):
                    k, v = w[4:].split("=")
                    pr.setdefault(k, {})["CTL"] = v
        out.append((*r, pr, f"fork 456404fcffe5 arithmetic at P {hx(p)}, N {hx(n)}; E625 U = 19"))
    return out


ROWS = {"k0": k0_rows, "kg": kg_rows, "f0": f0_rows}
HEAD = {
    "k0": ("# k0 (E1077, 6 jobs): module E0CC4027 with render_final_pb_pages 0 runs B60AB0B4's jobs "
           "byte for byte (H-SAME against H-DIFF), on the kept twins. Controls that can fail: "
           "k0-pr1-1/2 (r13-dpm pr2-c1: 1 partial render, 0x0624 0x294), k0-z-t10/t18b (r13-zls "
           "zb-c-ctl: depth-store.1.bin sha256 92f04c7c..., 2048 drawn, 2048 store dwords changed), "
           "k0-a0 (r10-dpm a0-cal-2048's param and tadata dumps, sha256 e366ead7... and ddf914f0...). "
           "Any control off stops the stage and the session (hook_check, rc 24, on_stop end: R19-1 a)."),
    "kg": ("# kg (E1077, 4 jobs): the geometry form (tri 1024x768 -n 2 --geometry 1 at P 0x28) on t10 "
           "and t18b, no kept twin: H-SAME (t10 = t18b: the final dumps, the overflow, the knob), "
           "H-E625 (TA3DCtl dwords 35, 37, 38 after the overflowing geometry kick). Controls "
           "k0-geo-t10-1/t18b-1: the geometry kick overflows and 0x0624 reads 0x6; off: rc 24, end."),
    "f0": ("# f0 (E1078, 12 jobs): does the EDM apply a TA command's thresholds (flag 0x2000, dwords "
           "10-13) at that kick? Geometry kick at P (render_pb_pages), the final at N (t18b "
           "--final-pb-pages). H-UPD (the final's 0x0624 = N - 0x22 and it follows N), H-IGN, H-LATE, "
           "H-STICK (f0-back), H-STORE (pb:10-13). Controls f0-same-1/2, f0-up-1/2 (fit): a control "
           "off stops the stage (rc 24). f0-down (medium, P 0x100 N 0x30: a threshold below the "
           "pages the open scene holds) last, soft, stop:jobfail: a final ending other than ok or "
           "overflowed stops the stage."),
}


def write(kp=KP):
    for st in STAGES:
        rows = ROWS[st]()
        lim = "#limit 0"
        lines = [f"#stage {st}", lim, HEAD[st]]
        for name, sset, risk, knobs, tool, args, _, _ in rows:
            lines.append(f"{name}|{sset}|{risk}|{knobs}|{tool}|{args}")
        with open(os.path.join(kp, "tables", f"{st}.txt"), "w") as f:
            f.write("\n".join(lines) + "\n")
        p = ["case\tquantity\tvalue\tmodel\tset\tsource"]
        for name, sset, _, _, _, _, preds, src in rows:
            for q, by in preds.items():
                for m, v in by.items():
                    p.append(f"{name}\t{q}\t{v}\t{m}\t{sset}\t{src}")
        with open(os.path.join(kp, "predictions", f"{st}.tsv"), "w") as f:
            f.write("\n".join(p) + "\n")


def extra_knobs():
    words = set()
    for st in STAGES:
        for r in ROWS[st]():
            words |= {w for w in r[3].split() if w.startswith(("ctl:", "stop:"))}
    return sorted(words)


if __name__ == "__main__":
    write()
    if "--extra" in sys.argv:
        print(extra_knobs())
