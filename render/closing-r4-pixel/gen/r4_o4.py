# SPDX-License-Identifier: MIT
"""Stage p4-o4 (Q276, the o4 clause; 36 jobs; plan section 3.4 of closing4/pixel/exp-pixel-r4.md, decision R4 9a).
Same job shape and decode as R3's p-c3 (gen r3_c.py of closing-r3-pixel: `probe --tri pixel --temps 32 --pixels` on the default 64x64
triangle with the PDS iteration slot), a new word layout: the low 16 bits of every output word are
    (marker m) << 6 | (variant bits) << 4 | tag          marker bits 15:6 (unique per job: x job m, y job m + 1),
                                                          variant bits 5:4 (0 except in the o4 variants below), tag bits 3:0
with the tags of r3_c (o0 1, o1 2 / 12, o2 3, o3 4, o4 5 / 13, o5 6, o6 7, o7 8) and the o4 words
    A = tag 5, A3 = tag 13 (bit 3: E808's 5'), A4 = tag 5 with bit 4, A5 = tag 5 with bit 5.
E709's program (c-e709) is the landed one, unchanged, with no marker (its words are decoded by tag only).
Rows: 8 bridge controls (c-e709, c-o4-u, c-o4s-u, c-u, x and y), 14 value jobs (7 configurations), 12 predicate jobs
(p1 A / !p1 A4 = `pa`, and the swapped order `ps`, k = 0, 3, 7), 2 replicates of c-o4-u.  Predictions: score/o4model.py."""
from __future__ import annotations

import sys

import r4common as K
from r4common import DATA, REPO, Row, build_bin

sys.path.insert(0, str(K.R4 / "score"))
import o4model as M  # noqa: E402

C_BASE = ('probe --tri pixel --temps 32 --pixels --dump-render "$W/dump" --width 64 --height 64 --vtx-coords 2 '
          '--blk 4=0x00030001 --slot pixpds="$S/pds_iter_xy.bin:12" --slot vtxuse="$S/vtx_coords.bin" "$S/{prog}.bin"')
KNOBS = "stophang"
STAGE = "p4-o4"
M0 = 0x100                                   # first marker; m * 64 + 0x3f stays below 0x8000 for m < 0x200

VALUE_NAMES = {"a3": "single write A3 (tag 13)", "a4": "single write A4", "a-a4": "A then A4", "a4-a": "A4 then A",
               "a-a5": "A then A5", "a5-a": "A5 then A", "a3-a4": "A3 then A4"}
WORD = {M.A: "A", M.A3: "A3", M.A4: "A4", M.A5: "A5"}


def program(kind, ax, m, writes=None, k=None, order=None):
    """kind u | o4-u | o4s-u | value (writes = o4 words in program order) | pred (order pa / ps, k)."""
    pa = "pa0" if ax == "x" else "pa1"
    t = lambda j, extra=0: f"#0x{m * 64 + extra + j:x}"
    w4 = lambda w6: t(w6 & 0xf, w6 & 0x30)
    ops = ["phas #0, #0, pixel, end, parallel", f"or.skipinv o0, {pa}, {t(1)}"]
    pre = []
    if kind == "pred":
        pre = [f"xor.testtaz.chan0 !c0, p1, g25, #{k}"]
    ops += pre + [f"or.skipinv o1, {pa}, {t(12)}", f"or.skipinv o1, {pa}, {t(2)}", f"or.skipinv o2, {pa}, {t(3)}",
                  f"or.skipinv o3, {pa}, {t(4)}"]
    if kind == "u":
        ops += [f"or.skipinv o4, {pa}, {t(5)}"]
    elif kind == "o4-u":
        ops += [f"or.skipinv o4, {pa}, {w4(M.A3)}", f"or.skipinv o4, {pa}, {w4(M.A)}"]
    elif kind == "o4s-u":
        ops += [f"or.skipinv o4, {pa}, {w4(M.A)}", f"or.skipinv o4, {pa}, {w4(M.A3)}"]
    elif kind == "value":
        ops += [f"or.skipinv o4, {pa}, {w4(w)}" for w in writes]
    else:
        for p, w in M.PRED_ORDERS[order]:
            ops += [f"{'!p1' if p == '!p1' else 'p1'} or.skipinv o4, {pa}, {w4(w)}"]
    ops += [f"or.skipinv o5, {pa}, {t(6)}", f"or.skipinv o6, {pa}, {t(7)}", f"or.skipinv.end o7, {pa}, {t(8)}"]
    return "\n".join(ops) + "\n"


def build():
    rows, preds, needs = [], [], []
    P = lambda n, q, v, mdl, st: preds.append((n, q, v, mdl, st))
    pds = (REPO / "probes/usse/templates/pds_iter_xy.s").read_text()
    K.BINS.mkdir(exist_ok=True)
    K.probe._assemble(pds, K.BINS / "pds_iter_xy.bin", "pds")
    K.probe._assemble((REPO / "probes/usse/templates/vtx_coords.s").read_text(), K.BINS / "vtx_coords.bin")
    needs += ["$S/pds_iter_xy.bin", "$S/vtx_coords.bin"]
    PD = DATA / "vdm/verification-1141ta/programs"
    for ax in "xy":                                             # E709's own programs, byte for byte
        build_bin(f"r4o-e709-{ax}", (PD / f"o4g-3-{ax}.s").read_text())
        needs.append(f"$S/r4o-e709-{ax}.bin")
    state = {"m": M0}
    markers = {}

    def job(cfg, ax, st, role, kind=None, **kw):
        jn = f"c-{cfg}-{ax}"
        if cfg == "e709":
            prog = f"r4o-e709-{ax}"
        else:
            state["m"] += 1
            m = state["m"]
            prog = f"r4o-{cfg}-{ax}"
            build_bin(prog, program(kind, ax, m, **kw))
            needs.append(f"$S/{prog}.bin")
            markers[jn] = m
        rows.append(Row(jn, st, K.SAFE, KNOBS, "-", C_BASE.format(prog=prog), role))
        return jn

    def pair(cfg, st, role, kind=None, **kw):
        jx = job(cfg, "x", st, role, kind, **kw)
        job(cfg, "y", st, role + " (the y job of the pair: source pixel identity)", kind, **kw)
        if jx in markers:
            P(jx, "marker", f"{markers[jx]:#x}", "frozen program marker (x job; the y job's is +1): ((word & 0xffff) >> 6)", st)
        return jx

    # ------------------------------------------------------------- bridge controls (8)
    jx = pair("e709", "control", "G-o4 control: E709's o4g-3 unchanged (no marker)")
    g4 = lambda j: [P(j, "g_o4_words", "10..100", "G-o4 structural (26 runs of R1 p-c2 and S1b p-c; R3 p-c3: tag-5 words in the x and y job)", "control"),
                    P(j, "g_o4_pairs", "5..60", "G-o4 structural (pairs 8..42)", "control"),
                    P(j, "g_o4_parity", "even,even", "G-o4 structural (every pair source (even x, even y))", "control"),
                    P(j, "g_o4_tag5p_max", "2", "G-o4 structural (no tag-13 word in the x job)", "control")]
    g4(jx)
    jx = pair("o4-u", "control", "G-o4 control: both o4 writes unpredicated, A3 (tag 13) first, A last", kind="o4-u")
    g4(jx)
    P(jx, "o4_class", "A", "E808 / R3 (tag 5 whichever of 5 and 5' is written last or first)", "control")
    jx = pair("o4s-u", "control", "swapped-order control: A first, A3 last (E808: 5 read, 2 of 2)", kind="o4s-u")
    P(jx, "o4_class", "A", "E808 (the o4 words read tag 5 with 5' written last)", "control")
    jx = pair("u", "control", "G-o1 control: the o1 pair unpredicated (the second, tag 2, wins); o4 one write A", kind="u")
    P(jx, "ctl_min_frac", "0.98", "frozen criterion (R1 / S1b / R3: tag-2 fraction 0.990 to 0.996)", "control")
    # ------------------------------------------------------------- value jobs (14), HELD OUT
    models = M.models()
    for cfg, writes in M.VALUE.items():
        jx = pair("v-" + cfg, "heldout", f"HELD OUT: {VALUE_NAMES[cfg]}", kind="value", writes=writes)
        for m in models:
            P(jx, "o4_class", M.value_pred(m, cfg), f"{M.name(m)} (single-write path {m[0]}, combine {m[1]})", "heldout")
    # ------------------------------------------------------------- predicate jobs (12), HELD OUT
    for order, ordtxt in (("pa", "p1 A, !p1 A4"), ("ps", "!p1 A4, p1 A (swapped order)")):
        for k in M.PRED_K:
            cfg = M.pred_name(order, k)
            jx = pair(cfg, "heldout", f"HELD OUT: predicate k = {k}: {ordtxt}", kind="pred", order=order, k=k)
            for m in models:
                for g in ("gated", "ignored"):
                    P(jx, "o4_class", M.pred_lands(m, g, order, k), f"{M.name(m)}+{g}", "heldout")
    # ------------------------------------------------------------- replicates (2): c-o4-u again
    for ax in "xy":
        src = next(r for r in rows if r.name == f"c-o4-u-{ax}")
        rows.append(Row(f"c-o4-u-{ax}-rep", "replicate", K.SAFE, KNOBS, "-", src.args, f"replicate of c-o4-u-{ax} (same program: identical job)"))
    P("c-o4-u-x-rep", "o4_class", "A", "replicate of c-o4-u (same class)", "replicate")
    P("c-o4-u-x-rep", "marker", f"{markers['c-o4-u-x']:#x}", "frozen program marker (identical program)", "replicate")
    P("@p4-o4", "family", ",".join(M.name(m) for m in models), "the 12 models that fit E808 (V1 x 5 rules, V2 x 5 rules, V3 x and, min)", "heldout")
    P("@p4-o4", "predicate_rows", "cannot tell when c-v-a-a4 and c-v-a4-a read the same class",
      "plan 3.4: the 14 value jobs gate the 12 predicate jobs", "heldout")
    (K.BINS / "p4o4-markers.tsv").write_text("".join(f"{k}\t{v}\n" for k, v in markers.items()))
    head = """Q276 o4 clause (pixel), stage p4-o4: which o4 word lands.  E808: with 5' (tag 13, bit 3) and 5 written in both orders every o4 word read
tag 5.  Model family: single-write path V1 (drops bit 3), V2 (a word with bit 3 does not land), V3 (as written) x combine last, first, and,
or, min, the 12 that fit E808 (score/o4model.py).  Words differ in other bits too: A4 = tag 5 + bit 4, A5 = tag 5 + bit 5; the job marker
sits at bits 15:6.  Rows: 8 controls (c-e709, c-o4-u, c-o4s-u, c-u: G-o4, tag 5, tag 5, G-o1), 14 value jobs (7 configurations x x/y: A3,
A4, A then A4, A4 then A, A then A5, A5 then A, A3 then A4), 12 predicate jobs (p1 A / !p1 A4 and the swapped order, k = 0, 3, 7: gated =
only the instance whose lane equals k writes through p1, ignored = both writes run), 2 replicates of c-o4-u.  The predicate rows are read
only if the bit-4 pairs read two classes in the two orders.  No fault is expected; any fault or hang stops the stage."""
    return rows, preds, list(dict.fromkeys(needs)), head


if __name__ == "__main__":
    r, p, n, h = build()
    K.write_table(STAGE, r, n, h)
    K.write_preds(STAGE, p)
    print(f"{STAGE}: {len(r)} jobs, {len(p)} prediction rows, {len(n)} programs")
