"""S1b job tables and frozen predictions: the S1 analysis's S1b items 1-9 (item 10, g-e8a, needs per-render pixel
programs: not here).  Each function returns (rows, preds, needs, head); gen/s1gen.py writes them.

Fit vs held out, honestly: every value S1 measured and S1's analysis read POST HOC (after the run, with code written
after the run) enters here only as a frozen hypothesis or as a control that reproduces a measured S1 value; the
`set` column says which.  Model names carry where a value came from: '(S1 post hoc)' = suggested by S1's data, now
tested on new runs; '(S1 frozen)' = an S1 frozen result reproduced as a control.
"""
from __future__ import annotations

import struct

import numpy as np

from s1common import BINS, REPO, RT_DPM, Row, f32, probe
import s1geo
import s1geo3
import s1pix
import b2model

GREEN_BIN = "$S/p1139-green.bin"


def bits(x: float) -> int:
    return struct.unpack("<I", struct.pack("<f", x))[0]


def fval(b: int) -> float:
    return struct.unpack("<f", struct.pack("<I", b))[0]


def recip(wbits: int) -> tuple[int, int]:
    """(RZ32, RN32) of the exact reciprocal of the float32 word wbits."""
    r = 1.0 / fval(wbits)
    rn = bits(r)
    rz = rn if fval(rn) <= r else rn - 1
    return rz, rn


# ------------------------------------------------------------------------------------------ p-f (item 1)
def p_f():
    rows, preds = [], []
    cmd_dpm = "tri -n 2 --keep-going --wait-ms 6000 --width 1024 --height 768 --keep-overflow"
    rows.append(Row("f-dpm-0", "control", "safe", "0x23", "alias_skip=0x0 stophang", "-", cmd_dpm,
                    "control that can fail: no buffer left out, P = 0x23: both renders overflow and every render "
                    "is exact (the reading the masks need)", "f-dpm-0"))
    preds.append(("f-dpm-0", "outcome", "exact", "partial renders exact", "control"))
    for c, mask, role in (("f-dpm-1e", "0x1e", "buffers 1 to 4 left out (S1's 0x1f without buffer 0)"),
                          ("f-dpm-dc0", "0xdc0", "buffers 6, 7, 8, 10, 11 left out (S1 post hoc: exact 2 of 2)")):
        for r in (1, 2):
            n = f"{c}-r{r}"
            rows.append(Row(n, "heldout" if r == 1 else "replicate", "safe", "0x23", f"alias_skip={mask} hypo:{c}:1", "-",
                            cmd_dpm, f"1024x768 partial renders, {role}", c))
            preds += [(n, "outcome", "exact", "HI", "heldout"), (n, "outcome", "fault", "HJ", "heldout")]
    rows.append(Row("f-ctl0", "control", "risky", "-", "alias_skip=0x1 hypo:f-ctl0:1", "-",
                    "tri -n 2 --keep-going --wait-ms 6000",
                    "control: buffer 0 left out faults 0x91000 (E573, S1 frozen 2 of 2): the knob bites; last", "f-ctl0"))
    preds.append(("f-ctl0", "outcome", "fault 0x91000", "E573 (S1 frozen)", "control"))
    head = """F (pixel, S1b item 1): Q076 under partial renders.  S1's f-dpm-1f (mask 0x1f) contained buffer 0, whose
own fault it reproduced: 0x1e is buffers 1 to 4.  f-dpm-dc0 repeats S1's job (scored 'split' by S1's regex; post hoc
exact 2 of 2: here a frozen repeat).  f-dpm-0 is the control that can fail (no mask: partial renders exact).  f-ctl0
(buffer 0, E573's fault) shows the knob bites; it faults by design: a hypothesis row, last.  The mask is written,
read back and marked in the kernel log before each job and put back to 0 after it.  Scorer: score_pix.score_f
(renders_exact accepts `tri: 0 of 2 renders ok, 2 overflowed` with every diff 0)."""
    return rows, preds, [], head


# ------------------------------------------------------------------------------------------ g-e4w (item 2)
def g_e4w():
    base = 'probe --tri pixel --vertices 15 --copy-depth --dump-render "$W/dump" --pixels {x}"$S/p1139-green.bin"'
    rows, preds = [], []
    rows.append(Row("ix-c", "control", "safe", "-", "stophang", "-", base.format(x=""),
                    "control: E414's five-copy object over the 16-bit list (S1 frozen)", "ix-c"))
    preds.append(("ix-c", "result", "same", "E414 (S1 frozen)", "control"))
    # review order: the unflipped header first, then bit 25, then bits 24 + 25; S1's fault control last
    conds = (("ix32-n", "--index-width 32 --vdm 2^=0x02000000 ", "32-bit list, bit 25 cleared (header says 16-bit)",
              (("not same", "HW32"), ("not same", "HX"))),
             ("ix32-25", "--index-width 32 ", "32-bit list, bit 25 set (the option)",
              (("same", "HW32"), ("fault", "HX"))),
             ("ix32-2425", "--index-width 32 --vdm 2^=0x01000000 ", "32-bit list, bits 24 and 25",
              (("same|hang", "HW32"), ("fault", "HX"))))
    for c, x, role, pr in conds:
        for r in (1, 2):
            n = f"{c}-r{r}"
            rows.append(Row(n, "heldout" if r == 1 else "replicate", "safe", "-", f"hypo:{c}:1", "-",
                            base.format(x=x), role, c))
            for v, m in pr:
                preds.append((n, "result", v, m, "heldout"))
    rows.append(Row("ix-25", "control", "safe", "-", "hypo:ix-25:1", "-", base.format(x="--vdm 2^=0x02000000 "),
                    "control: bit 25 over the 16-bit list faults 0xd0008 (S1 frozen 2 of 2); last", "ix-25"))
    preds.append(("ix-25", "result", "fault 0xd0008", "S1 frozen", "control"))
    head = """E4w (geometry, S1b item 2): Q112, the positive test of the index width.  Tool change: probe --tri
--index-width 32 writes the index list 0..14 as 32-bit words and sets VDM word 2 bit 25 (the bit S1's g-e4 left
with a HW signature: over the 16-bit list it faulted 0xd0008, 2 of 2); --vdm 2^=V flips bits after it.
HW32 (bit 25 selects 32-bit indices): ix32-25 draws E414's object word for word 2 of 2, and ix32-n (bit 25 cleared
over the 32-bit list: read as 16-bit, indices 0,0,1,0,2,0,...) does not; ix32-2425 'same' or a hang (bit 24 alone hung
in S1).  HX (bit 25 is something else): ix32-25 faults as the 16-bit job.  Expected hangs and faults are hypotheses:
every row but ix-c is a hypo row (measured, at most its group's events); ix-25 (the S1 fault, a control) last.
Knob proof: the probe line's '32-bit indices' and tests/emit_checks.py (the words, with the tool's mock)."""
    return rows, preds, ["$S/p1139-green.bin"], head


# ------------------------------------------------------------------------------------------ g-e5 (item 3)
def g_e5():
    cap = lambda n, f, a: (
        f'probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords {n} '
        + (f'--vdm 6^=0x{(15 ^ f) << 28:08x} ' if f != 15 else '')
        + (f'--vdm 7^=0x{(a << 7) ^ 0x80:08x} ' if a != 1 else '')
        + f'--dump-render "$W/dump" --slot "pixel=$S/pix_pa0.bin" --slot "vtxuse=$S/vtx_c{n}.bin" '
        f'"$S/p1131-fmt-{n}__0.bin"')
    rows, preds = [], []
    rows.append(Row("r-n8-a1", "control", "risky", "-", "stophang", "-", cap(8, 10, 1), "control: E702's base", "r-n8-a1"))
    preds.append(("r-n8-a1", "o0_mixed_x", "2288", "E702 (S1 frozen)", "control"))
    rows.append(Row("r-n2-a9", "control", "risky", "-", "stophang", "-", cap(2, 15, 9), "control: E702's hang-row base",
                    "r-n2-a9"))
    preds.append(("r-n2-a9", "o0_mixed_x", "2821", "E702 (S1 frozen)", "control"))
    a8 = [("o0_mixed_x", "2288", "HO (the base)"), ("lost_ids", "", "HO (the base)"),
          ("o0_mixed_x", "2156", "HL70 (S1 post hoc)"), ("lost_ids", "70", "HL70 (S1 post hoc)")]
    for tag, knobs, role in (("r", "stophang", "a = 8 with a reset before (as S1)"),
                             ("nr", "noreset stophang", "a = 8 with NO reset before: the previous a8 job's state carries")):
        for r in (1, 2, 3):
            n = f"r-n8-a8{'' if tag == 'r' else '-nr'}-r{r}"
            rows.append(Row(n, "heldout" if r == 1 else "replicate", "risky", "-", knobs, "-", cap(8, 10, 8), role,
                            n[:-3]))
            for q, v, m in a8:
                preds.append((n, q, v, m, "heldout"))
    for r in (1, 2):
        n = f"r-n8-a12-r{r}"
        rows.append(Row(n, "heldout" if r == 1 else "replicate", "risky", "-", "stophang", "-", cap(8, 10, 12),
                        "a = 12: E702's change or S1's", "r-n8-a12"))
        for q, v, m in (("o0_mixed_x", "2028", "HD (E702)"), ("o0_mixed_x", "2288", "HO (the base)"),
                        ("o0_mixed_x", "2582", "HS1 (S1 post hoc: 2582 x3)"), ("lost_ids", "", "HS1 (S1 post hoc: 2582 x3)")):
            preds.append((n, q, v, m, "heldout"))
    head = """E5 (geometry, S1b item 3): Q272/Q164, the a = 8 and a = 12 events.  HO is the base histogram (2288, no
vertex lost), as the proposal defined it (S1's scorer called any 0 of 3 'HO').  a8: S1 lost vertex 70 in 2 of 3 runs
(post hoc, q164_fate): HL70 is that reading frozen (count 2156, lost 70); three runs with the runner's reset before
each (as S1) and three with no reset before (noreset: the state of the previous a8 job carries).  HC (state carry):
the two triples differ.  a12: E702's 2028 (HD), the base (HO), S1's 2582 (HS1, post hoc).  The vertex fate is scored
with q164_fate's functions on the PB dump (lost ids).  Programs as S1 (probes/ta p1131-progs.toml)."""
    needs = ["$S/pix_pa0.bin", "$S/vtx_c8.bin", "$S/vtx_c2.bin", "$S/p1131-fmt-8__0.bin", "$S/p1131-fmt-2__0.bin"]
    return rows, preds, needs, head


# ------------------------------------------------------------------------------------------ p-d (item 4)
def p_d():
    import json
    import tomllib
    pr = tomllib.loads((s1pix.TEXD / "probes/p1141-addr.toml").read_text())["probe"][0]
    labels = pr["labels"]
    src = REPO / "probes/texture/templates"
    base = dict(name="s1d", question="s1", source="tx_map.s", coords=True, pixels=True, params={},
                inputs=["PRE", "SETUP", "SMP"])
    rows, preds, needs, built, a4rows = [], [], [], {}, []

    def build(label):
        if label not in built:
            nm = "s1d-" + label.replace("ad-", "")
            p = probe._probe({**base, "name": nm.lower(), "cases": [pr["cases"][labels.index(label)]]}, "s1-d.toml")
            probe.build(p, BINS, src)
            built[label] = p.name
            needs.append(f"$S/{p.name}__0.bin")
        return built[label]

    def job(nm, label, pages, st, knobs, role, outcomes):
        b = build(label)
        rows.append(Row(nm, st, "risky" if "hypo" in knobs else "safe", "-", knobs, "-",
                        f'probe --temps 32 --coords --pixels --scratch-pages {pages} "$S/{b}__0.bin"', role, nm))
        preds.append((nm, "scratch_line", f"({pages * 4} KiB)", "knob", st))
        px = s1pix.a4_pixels(label, pages)
        oob = sum(1 for v in px if v == s1pix.OOB)
        a4rows.append((nm, label, pages, px))
        preds.append((nm, "a4_oob_pixels", str(oob), f"A4 at {pages} pages", st))
        if not oob:
            preds.append((nm, "pix_sha256_if_complete", s1pix.pix_hash(px), f"A4 at {pages} pages", st))
        for m, v in outcomes:
            preds.append((nm, "outcome", v, m, st))

    job("d-ok-64", "ad-tw128x32-L0e2", 64, "control", "stophang", "control: E722's passing case at 64 pages (S1 frozen)",
        [("A4", "complete")])
    big = "the three extents E722 faulted at 16 pages; A4 at 64 pages fit S1's images post hoc: a frozen repeat"
    for nm, lab in (("d-L2e2-64", "ad-tw64x64-L2e2"), ("d-L3e3-64", "ad-tw64x64-L3e3"), ("d-st-L3e2-64", "ad-st128x32-L3e2")):
        job(nm, lab, 64, "heldout", "hypo:hx:3", big, [("HB-A4", "complete"), ("HX", "fault")])
    job("d-L2e2-21", "ad-tw64x64-L2e2", 21, "heldout", "hypo:hx:3", "84 KiB scratch = the extent",
        [("HB-A4", "complete"), ("HX", "fault")])
    job("d-L2e2-20", "ad-tw64x64-L2e2", 20, "heldout", "hypo:hm:3",
        "80 KiB: S1 completed with untagged words read past the scratch (the dump of what lies there; repeat)",
        [("HM (S1 post hoc)", "complete"), ("HB-end", "fault")])
    for p in (19, 18, 17):
        job(f"d-L2e2-{p}", "ad-tw64x64-L2e2", p, "heldout", "hypo:hm:3",
            f"{p * 4} KiB: the fault follows the mapping (HM) or the scratch's end (HB-end)",
            [("HM (S1 post hoc)", "complete"), ("HB-end", "fault")])
    job("d-L2e2-16", "ad-tw64x64-L2e2", 16, "control", "hypo:d16:1",
        "control: E722's job unchanged, faults 0x90002 (S1 frozen); last", [("E722", "fault 0x90002")])
    head = """D (pixel, S1b item 4): Q281.  S1's A4 hashes were cases.json's, rendered for 16 pages (all OOB at 64):
here A4 (E722's model, tex2.predict with cat1141.py's options) is rendered at each job's OWN scratch pages
(predictions/p-d-A4.tsv: every pixel; a4_oob_pixels = where the model reads past the scratch).  64 and 21 pages: no
OOB pixel, the A4 hash is frozen (it fit S1's images post hoc: a frozen repeat, not held out in the strong sense).
17 to 20 pages: S1 post hoc read 'the fault follows the mapping' (16 pages faulted at scratch + 80 KiB, 20 pages read
past the scratch without a fault): HM predicts completion with A4 exact on every in-scratch pixel; HB-end a fault.
d-L2e2-20 is also the dump past the scratch (its pixels are the words read there).  Every job that may fault under a
stated hypothesis is a hypo row; d-L2e2-16 (E722's fault) last."""
    return rows, preds, needs, head, a4rows


# ------------------------------------------------------------------------------------------ p-b2 (item 5)
B2_TRI = ((0, 0), (512, 0), (0, 512))


def b2_jobs():
    zx = lambda L: (0.125, 0.125 + L / 8192, 0.125)       # the same plane A = 1/8192, B = 0 (dyadic) for every L
    t = lambda L, dx=0, dy=0: ((dx, dy), (L + dx, dy), (dx, L + dy))
    return [("d-ctl", "control", 256, 128, t(512), zx(512), "control: dp-ax-b2 (E731; S1 frozen reproduction)"),
            ("d-ctl-r2", "replicate", 256, 128, t(512), zx(512), "replicate of the control"),
            ("d-shift", "heldout", 256, 128, t(512, 64, 32), zx(512), "triangle moved (64, 32): HT region fixed, HV moves"),
            ("d-t192", "heldout", 256, 192, t(512), zx(512), "target 256 x 192"),
            ("d-t256", "heldout", 256, 256, t(512), zx(512), "target 256 x 256"),
            ("d-tall", "heldout", 256, 512, t(512), zx(512), "target 256 x 512 (S1's d-tall)"),
            ("d-L448", "heldout", 256, 128, t(448), zx(448), "the same plane from a smaller triangle (448)"),
            ("d-L384", "heldout", 256, 128, t(384), zx(384), "the same plane from a smaller triangle (384)")]


def p_b2():
    rows, preds = [], []
    ctl = b2model.ctl_model([])                       # writes p-b2-set-{ctl,ht_shift,hv_shift}.bits (E731's map)
    ctlset = {r[2] for r in ctl if r[0] == "d-ctl" and r[1] == "dev_counts"}
    for nm, st, w, h, V, Z, role in b2_jobs():
        cmd = s1pix.tri_depth_cmd(w, h, V, Z) + ' --dump-render "$W/dump"'
        # the tool's own one-triangle check (1/16-pixel CPU reference) is not B2's measure: a held-out geometry whose
        # edge pixels differ from it (rc 1 with a diff line) is not a failure; the control must pass it as in S1 (rc 0)
        kn = "stophang" if nm.startswith("d-ctl") else "stophang expectdiff"
        rows.append(Row(nm, st, "safe", "-", kn, "-", cmd, role, "d-ctl" if nm.startswith("d-ctl") else nm))
        if nm.startswith("d-ctl"):
            preds.append((nm, "dev_set", "ctl", "E731 (S1 frozen)", "control"))
            preds.append((nm, "dev_counts", next(iter(ctlset)), "E731 (S1 frozen)", "control"))
            continue
        ht = "ht_shift" if nm == "d-shift" else "ctl"
        preds.append((nm, "dev_set_window", ht, "HT (target-tied)", "heldout"))
        if nm == "d-shift":
            preds.append((nm, "dev_set_window", "hv_shift", "HV (vertex-tied)", "heldout"))
        elif nm.startswith("d-t"):
            preds.append((nm, "dev_set_window", "ctl", "HV (vertex-tied)", "heldout"))
        preds.append((nm, "dev_iff_clipped", "yes", "HCLIP (S1 post hoc: plane from the clipped polygon)", "heldout"))
        if nm in ("d-shift", "d-tall"):
            preds.append((nm, "dev_pixels", "0", "S1 post hoc (no deviating pixel)", "heldout"))
    head = """B2 (pixel, S1b item 5): Q200, where the lower-binade deviation region comes from.  Coverage fix
(b2model.py: the clear 1.0 is not covered).  Every job keeps its parameter buffer (--dump-render) so the stored
(clipped) polygon is read.  HT: the region is fixed in target coordinates (every job's map inside 256 x 128 equals
d-ctl's, d-shift's the d-ctl map on its coverage); HV: it moves with the triangle; HCLIP (S1 post hoc candidate,
frozen here): the plane is set up from the clipped polygon, so a job deviates iff its stored polygon is not the
original triangle, and two jobs with the same stored polygon deviate alike.  Target ladder 128/192/256/512 and a
smaller triangle (448, 384) carrying the same dyadic plane (A = 1/8192); d-shift and d-tall repeat S1's (post hoc: no
deviating pixel)."""
    return rows, preds, [], head


# ------------------------------------------------------------------------------------------ g-e8b (item 6)
def g_e8b():
    cmd = ('probe --tri pixel --vertices 6 --obj2 3 --obj2-pixel "$S/pix-red.bin" '
           '--blk 1={i1} --obj2-blk 1={i2} --obj2-blk 10={z2} --dump-render "$W/dump" --pixels "$S/p1139-green.bin"')
    OPQ, OPQ_ALW, TRL_ALW = "0x00400200", "0x01c00200", "0x03c00200"     # DCMP bits 24:22: 1 less, 7 always
    NEAR, FAR = "0x3e800000", "0x3f400000"                                # obj2 at 0.25 / 0.75 (obj1 at 0.5)
    # winners under HL (list order), HD (depth order), HP (translucent pass after the opaque), HN (pass type changes nothing)
    cases = [("t-opq-near", OPQ, OPQ, NEAR, "control", "both opaque less, second nearer (S1 frozen): red", "red"),
             ("t-opq-far", OPQ, OPQ, FAR, "control", "both opaque less, second farther (S1 frozen): green", "green"),
             ("o-2-alw-far", OPQ, OPQ_ALW, FAR, "control", "second opaque ALWAYS, farther: it draws (list order): red", "red"),
             ("t-2-alw-far", OPQ, TRL_ALW, FAR, "heldout", "translucent ALWAYS second, farther", None),
             ("t-2-alw-far-r2", OPQ, TRL_ALW, FAR, "replicate", "replicate", None),
             ("t-1-alw-far", TRL_ALW, OPQ, NEAR, "heldout", "translucent ALWAYS first (0.5), opaque second nearer", None),
             ("t-1-alw-far-r2", TRL_ALW, OPQ, NEAR, "replicate", "replicate", None)]
    win = {"t-2-alw-far": dict(HL="red", HD="green", HP="red", HN="red"),
           "t-1-alw-far": dict(HL="red", HD="red", HP="green", HN="red")}
    names = {"HL": "HL-list-order", "HD": "HD-depth-order", "HP": "HP-pass-order",
             "HN": "HN-pass-type-changes-nothing (S1 post hoc)"}
    rows, preds = [], []
    for nm, i1, i2, z2, st, role, ctlwin in cases:
        rows.append(Row(nm, st, "safe", "-", "stophang", "-", cmd.format(i1=i1, i2=i2, z2=z2), role, nm.replace("-r2", "")))
        if ctlwin:
            preds.append((nm, "overlap_winner", ctlwin, "all", "control"))
        else:
            for h, v in win[nm.replace("-r2", "")].items():
                preds.append((nm, "overlap_winner", v, names[h], st))
    head = """E8b (geometry, S1b item 6): Q073/Q241, a table where HD and HP differ.  S1's six jobs had HD and HP
predict the same winner everywhere, and the translucent images equal the opaque ones (post hoc).  Here the
translucent object's compare is ALWAYS (ISP0 bits 24:22 = 7, pass type 1: 0x03c00200) and it is the farther one:
t-2 (translucent second): HD green, HL/HP/HN red; t-1 (translucent first): HP green, HL/HD/HN red.  HN ('pass type
changes nothing', S1 post hoc) predicts as the opaque control o-2-alw-far (list order).  Controls: S1's two opaque
jobs and o-2-alw-far (an opaque ALWAYS second object draws although farther)."""
    return rows, preds, ["$S/p1139-green.bin", "$S/pix-red.bin"], head


# ------------------------------------------------------------------------------------------ g-e1 (item 7)
def g_e1():
    cmd = lambda v: (f'probe --tri pixel --width 4096 --height 4096 --vertices {v} '
                     f'--dump-render "$W/dump" "$S/p1139-green.bin"')
    rows, preds = [], []

    def job(name, v, P, st, role, cond=None):
        rows.append(Row(name, st, "safe", P, "stophang", RT_DPM, cmd(v), role, cond or name))
        thr0 = (int(P, 16) - 0x22) if int(P, 16) < 0x422 else 0x400
        preds.append((name, "knob0624_first", hex(thr0), "knob", st))

    job("c-1500-0x422", 1500, "0x422", "control", "negative control: E704's words, no raise (S1 frozen)")
    preds.append(("c-1500-0x422", "raise", "no", "E704 (S1 frozen)", "control"))
    job("p-1350-0x300", 1350, "0x300", "control", "positive control: raised in S1 (thr0 0x2de -> 0x2fe), these exact words")
    preds.append(("p-1350-0x300", "raise", "yes", "S1 frozen", "control"))
    for P in (0x320, 0x340, 0x360, 0x380, 0x3a0, 0x3c0):
        for V in (1350, 1500):
            n = f"x-{V}-{P:#x}"
            job(n, V, hex(P), "heldout", f"{V} vertices at P = {P:#x}: below or above the step")
            preds += [(n, "raise", "monotone, one step P for both scenes", "HP1 (S1 post hoc limit 0x2fe <= C < 0x3de)", "heldout"),
                      (n, "raise", "monotone, the step P differs by scene", "HPS", "heldout")]
    for V, dw in ((1350, 2), (1380, 3)):
        n = f"s-{V}-0x3e0"
        job(n, V, "0x3e0", "heldout", f"dword 36 at P = 0x3e0 (S1 post hoc: {dw})")
        preds.append((n, "dw36", str(dw), "S1 post hoc", "heldout"))
    head = """E1 (geometry, S1b item 7): Q273/Q210, where the raise stops below P = 0x3e0.  S1 (post hoc): raises
at thr0 <= 0x2de, none at thr0 >= 0x3be, for 1350 and 1500 alike.  Here 1350 and 1500 at P = 0x320 .. 0x3c0.  HP1:
one step P for both scenes (raise below a P*, none from P* on, the same P* for both; S1's post-hoc limit on the raised
threshold, 0x2fe <= C < 0x3de, says the same); HPS: the step differs by scene.  Controls ONLY from raises and
non-raises already measured under these exact words (S1's design used a held-out prediction as a control): the
negative c-1500-0x422 and the positive p-1350-0x300.  Knob proof per job: the job's own 0x0624 rows (not the first
sample, which is the previous job's).  s-1350/s-1380 at 0x3e0 repeat S1's dword-36 step (post hoc 2 -> 3)."""
    return rows, preds, ["$S/p1139-green.bin"], head


# ------------------------------------------------------------------------------------------ g-e3 subset (item 8)
def g_e3():
    rows, preds, needs = [], [], ["$S/p1139-green.bin"]
    T = s1geo3.E3_TEMPLATES

    def add(p, st, role, cond=None):
        rows.append(Row(p.name, st, "safe", "-", "stophang", "-", s1geo3._cmd_of(p, T), role, cond or p.name))
        needs.append(f"$S/{p.name}__0.bin")

    P = lambda n, q, v, m, st: preds.append((n, q, v, m, st))
    hx = s1geo3._hx
    orig = [(8.0, 8.0), (56.0, 20.0), (20.0, 56.0)]
    xy = lambda pts: ";".join(f"{x:.6g},{y:.6g}" for x, y in pts)
    # e3i: the w scan inside the guard band: x, y scaled by w (vtx_wclip S = w, A = 0, B = w), so x/w is the original
    p = s1geo3._p3("e3i-ctl", "vtx_wclip.s", "vtxuse", ["S", "A", "B"], [hx(0x3f800000), hx(0), hx(0x3f800000)])
    add(p, "control", "control: in-band program with w = 1 (E651's object, S1 frozen e3c-w1)")
    P("e3i-ctl", "object_equals_default", "yes", "E651 (S1 frozen)", "control")
    for tag, w in (("w3", 3.0), ("w7", 7.0), ("w0p003", 0.003), ("w3em5", 3e-5)):
        wb = bits(w)
        n = f"e3i-{tag}"
        p = s1geo3._p3(n, "vtx_wclip.s", "vtxuse", ["S", "A", "B"], [hx(wb), hx(0), hx(wb)])
        add(p, "heldout", f"in band, every vertex w = {w:g} (x, y scaled by w): 1/w RZ32 vs RN32 differ")
        rz, rn = recip(wb)
        for mdl, word in (("RZ32(1/w) [fit: mte/rhw 9 vertices]", rz), ("RN32(1/w)", rn)):
            P(n, "object", "present", mdl, "heldout")
            P(n, "rhw_word", hex(word), mdl, "heldout")
        P(n, "xy_near", xy(orig), "in band: x/w = the original", "heldout")
    # e3z: the z cut by vertex identity
    for n, a, b, st, role in (("e3z-flat099", 0, f32(0.99), "control", "control: flat z 0.99 (E651, S1 frozen)"),
                              ("e3z-cut-p", 0x40000000, 0x3F800000, "heldout", "z = 2x + 1: cut at z = +w"),
                              ("e3z-cut-m", 0x40000000, 0xBF800000, "heldout", "z = 2x - 1: cut at z = -w")):
        p = s1geo3._p3(n, "vtx_zab.s", "vtxuse", ["A", "B"], [hx(a), hx(b)], temps=8, vtx_coords=2,
                       slots={"pixel": "pix_green.s"})
        probe.build_helpers([p], BINS, T)
        add(p, st, role)
        needs.append("$S/pix_green.bin")
        if st == "control":
            P(n, "object_equals_default", "yes", "E651 (S1 frozen)", "control")
        else:
            P(n, "orig_xy", xy(orig), "-", "heldout")
            P(n, "nvert", ">=4", "HC-poly (S1 post hoc: both cuts clipped polygons)", "heldout")
            P(n, "nvert", "3", "HC-orig", "heldout")
    # e3k: the w clamp (block word 14).  Control: S1's e3k-ctl as measured (replace, not remove)
    W5 = 0x3727c5ac
    p = s1geo3._p3("e3k-ctl", "vtx_w.s", "vtxuse", ["W"], [hx(W5)], blk={14: 0x3a83126f})
    add(p, "control", "control: E194's w 1e-5 under clamp 1e-3 as S1 measured it: an object, 1/w = 1/clamp")
    for q, v in (("object", "present"), ("rhw_word", "0x4479ffff"), ("xy_box", "31.5,32.5")):
        P("e3k-ctl", q, v, "HREP (S1 frozen e3k-ctl)", "control")
    for tag, cb in (("c1e5", W5), ("c3e5", bits(3e-5)), ("c1e4", bits(1e-4)), ("c3e4", bits(3e-4)), ("c1e3", 0x3a83126f)):
        n = f"e3k-i-{tag}"
        p = s1geo3._p3(n, "vtx_wclip.s", "vtxuse", ["S", "A", "B"], [hx(W5), hx(0), hx(W5)], blk={14: cb})
        add(p, "heldout", f"in band, w = 1e-5, clamp {fval(cb):.3g}")
        eq = cb == W5
        rz, rn = recip(W5 if eq else cb)
        s = 1.0 if eq else float(np.float32(fval(W5)) / np.float32(fval(cb)))
        pts = [(32 + (x - 32) * s, 32 + (y - 32) * s) for x, y in orig]
        m = "HREP (S1 post hoc: w below the clamp is replaced by it, 1/w = 1/clamp)"
        for r_, word in ((" RZ", rz), (" RN", rn)):
            P(n, "object", "present", m + r_, "heldout")
            P(n, "rhw_word", hex(word), m + r_, "heldout")
        # the position clause apart: S1's e3k-ctl square is not what it gives for vtx_w (PREFLIGHT inconsistency 6)
        P(n, "xy_near", xy(pts), "HREP-xy (x, y divided by the clamp: the triangle shrinks by w/clamp)", "heldout")
        P(n, "object", "present" if eq else "none", "HREM (E194's image read as removal)", "heldout")
    head = """E3 subset (geometry, S1b item 8): Q230, gated PER GROUP (a group counts only if its own controls hold).
e3i: the w scan inside the guard band (x, y scaled by w, so no clip-made vertex; S1's w = 1e-3/1e-5 jobs were
clipped, which hid the reciprocal rule), with w where RZ32 and RN32 of 1/w differ.  e3z: the z cut scored by vertex
identity (S1 post hoc: both cuts are clipped polygons; HC-orig requires the ORIGINAL three).  e3k: the w clamp; the
control is S1's e3k-ctl predicted as S1 measured it ('replace': an object with 1/w = 1/clamp, inside 31.5..32.5);
a clamp ladder 1e-5 .. 1e-3 over w = 1e-5 in band: HREP (S1 post hoc) predicts 1/w = 1/clamp and x, y divided by the
clamp (the triangle shrinks by w/clamp about the centre); HREM the object removed."""
    return rows, preds, list(dict.fromkeys(needs)), head


# ------------------------------------------------------------------------------------------ p-c (item 9)
def p_c():
    rows, preds, needs = [], [], []
    probe._assemble((REPO / "probes/usse/templates/pds_iter_xy.s").read_text(), BINS / "pds_iter_xy.bin", "pds")
    probe._assemble((REPO / "probes/usse/templates/vtx_coords.s").read_text(), BINS / "vtx_coords.bin")
    needs += ["$S/pds_iter_xy.bin", "$S/vtx_coords.bin"]
    PD = s1pix.DATA / "vdm/verification-1141ta/programs"
    for ax in "xy":
        probe._assemble((PD / f"o4g-3-{ax}.s").read_text(), BINS / f"s1c-e709-{ax}.bin")
        needs.append(f"$S/s1c-e709-{ax}.bin")
    m = 0x210
    progs = {}
    for cfg in ("u", "k7", "k0", "k3", "g23"):
        for ax in "xy":
            m += 1
            probe._assemble(s1pix.c_program(cfg, ax, m), BINS / f"s1c-{cfg}-{ax}.bin")
            needs.append(f"$S/s1c-{cfg}-{ax}.bin")
            progs[(cfg, ax)] = f"s1c-{cfg}-{ax}"
    cmd = lambda prog: s1pix.C_BASE.format(prog=prog)
    S1C = "(16,25);(16,27);(17,27);(18,27);(19,27)"

    def pair(nm, prog_of, st, role, pr):
        for ax in "xy":
            n = f"{nm}-{ax}"
            rows.append(Row(n, st, "safe", "-", "stophang", "-", cmd(prog_of(ax)), role, n))
            for q, v, mdl, s in pr:
                preds.append((n, q, v, mdl, s))
    pair("c-e709", lambda ax: f"s1c-e709-{ax}", "control", "control: E709's o4g-3 (17 to 29 tag-5 pairs, S1 frozen 22)",
         [("tag5_pairs", "17-29", "E709", "control")])
    for nm, st in (("c-u", "control"), ("c-u-r2", "control"), ("c-u-r3", "control")):
        pair(nm, lambda ax: progs[("u", ax)], st, "order control: both writes unpredicated, the second (tag 2) wins",
             [("ctl_min_frac", "0.98", "frozen criterion (S1: 0.990)", "control"),
              ("first_write_sources", S1C, "HCL (S1 post hoc: the 5-source cluster keeps the first write)", "heldout")])
    hq = "HQ (S1 post hoc: g25 = the lane in the 2x2 quad)"
    pair("c-k7", lambda ax: progs[("k7", ax)], "heldout", "g25 == 7 never holds",
         [("frac_tag2_of_o1", "0.0", hq, "heldout"), ("tag2_parity", "none", hq, "heldout"),
          ("frac_tag2_of_o1", "1.0", "HN", "heldout")])
    rows.append(Row("c-k7-x-rep", "replicate", "safe", "-", "stophang", "-", cmd(progs[("k7", "x")]),
                    "replicate of c-k7-x (compared: S1 found 36 dwords different)", "c-k7-x"))
    preds.append(("c-k7-x-rep", "frac_tag2_of_o1", "same as c-k7-x within 0.07", "repeat", "replicate"))
    for cfg, par in (("k0", "0,0"), ("k3", "1,1")):
        pair(f"c-{cfg}", lambda ax, c=cfg: progs[(c, ax)], "heldout", f"g25 == {cfg[1]}",
             [("frac_tag2_of_o1", "0.25", hq, "heldout"), ("tag2_parity", par, hq, "heldout"),
              ("frac_tag2_of_o1", "0|1", "HA", "heldout"), ("frac_tag2_of_o1", "1.0", "HN", "heldout")])
    pair("c-g23", lambda ax: progs[("g23", ax)], "heldout", "and.testtanz g23 & 0x10",
         [("frac_tag2_of_o1", "0.25", "HP-g23 (refrozen from S1's 0.253: S1 post hoc)", "heldout"),
          ("frac_tag2_of_o1", "0|1", "HA", "heldout"), ("frac_tag2_of_o1", "1.0", "HN", "heldout")])
    head = """C (pixel, S1b item 9): Q276.  The order control c-u runs three times and passes by a FROZEN criterion
(tag-2 fraction >= 0.98; S1 required exactly 1.0 and saw 0.990: five sources (16,25), (16,27), (17..19,27) kept the
first write; HCL names that cluster as a hypothesis).  The replicate c-k7-x-rep is compared with c-k7-x (S1's scorer
dropped it).  HQ (S1 post hoc): the predicate gates o1 per lane, g25 = the pixel's lane in its 2x2 quad: k7 no tag 2,
k0 a quarter all at (even, even) sources, k3 a quarter all at (odd, odd).  g23's HP value is refrozen from S1's
0.253 (fit data; S1's 0.5 was the generator's guess).  HA, HN as in S1."""
    return rows, preds, needs, head
