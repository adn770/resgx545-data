# SPDX-License-Identifier: MIT
"""Stage p5-o4 (Q276: what the tag-5 word is; 58 jobs; plan closing5/pixel/exp-pixel-r5.md section 2, decisions R5-3 a / pixel D2 a,
D3 a: no E406 setup).  R4's p4-o4 shape, command and decode unchanged (C_BASE of R4's gen/r4_o4.py byte for byte: `probe --tri pixel
--temps 32 --pixels` on the default 64x64 triangle with the PDS iteration slot), the same word layout
    low 16 bits = marker << 6 | variant bits (5:4) << 4 | tag (3:0)     marker unique per job: x job m, y job m + 1
with the tags of R3 / R4 (o0 1, o1 12 then 2, o2 3, o3 4, o4 5, o5 6, o6 7, o7 8).
Rows (in this order):
  controls (8): c-e709 (E709's o4g-3 unchanged: G-o4 as R4), c-u (R4's own c-u program, byte for byte: G-o1), c-all4 (every output
                with bit 4: all nine models read 5:1; the control that can fail), c-v-a4 (R4's own c-v-a4 program: class A = 5:0, E838)
  walk (16, HELD OUT): w-0 .. w-7: o_j's word with bit 4, every other output's with bit 5
  independent (8, HELD OUT): z-o3 (o3 = tag 0), l-o4 (o4 = tag 4), l-o6 (o6 = tag 3), n-o4 (no o4 write)
  predicate (24, HELD OUT, gated by the walk): P4 p4-pa/ps-kK (p1 o4 = tag 5, !p1 o4 = tag 4), P3 p3-pa/ps-kK (p1 o3 = tag 4, !p1 o3 =
                tag 4 with bit 4), k = 0, 3, 7, x and y
  replicate (2): w-3 again.
Every row: knobs `stophang s2` (STATUS2 read after the reset and after the job; not 0x400 after the reset stops the stage), no
regtimeline.  Predictions: score/o5model.py."""
from __future__ import annotations

import sys

import r5common as K
from r5common import DATA, REPO, Row, build_bin

sys.path.insert(0, str(K.R5 / "score"))
import o5model as M  # noqa: E402

C_BASE = ('probe --tri pixel --temps 32 --pixels --dump-render "$W/dump" --width 64 --height 64 --vtx-coords 2 '
          '--blk 4=0x00030001 --slot pixpds="$S/pds_iter_xy.bin:12" --slot vtxuse="$S/vtx_coords.bin" "$S/{prog}.bin"')
KNOBS = "stophang s2"
STAGE = "p5-o4"
M0 = 0x140                     # first new marker (R4's reused programs carry 0x105, 0x106, 0x109, 0x10a); m * 64 + 0x3f < 0x8000
R4PIX = DATA / "render/closing-r4-pixel"
R4_REUSED = {"u": ("r4o-u", 261), "v-a4": ("r4o-v-a4", 265)}       # config -> (R4 program stem, R4 x marker: bins/p4o4-markers.tsv)


def program(ax, m, words, pred=None):
    """The pixel program of one job.  words: {j: low 6 bits of o_j's final word, or None (no write)}; o1 is written twice, tag 12
    then its word (R4's G-o1 shape), both with o1's variant bits.  pred: (pset, order, k): the predicate set's output is written
    twice under p1 / !p1, p1 = (g25 == k) set right after o0 (R4's predicate rows)."""
    pa = "pa0" if ax == "x" else "pa1"
    imm = lambda w6: f"#0x{m * 64 + w6:x}"
    ops = ["phas #0, #0, pixel, end, parallel", f"or.skipinv o0, {pa}, {imm(words[0])}"]
    pj = None
    if pred:
        pset, order, k = pred
        pj, wp1, wnp1 = M.PSETS[pset]
        ops.append(f"xor.testtaz.chan0 !c0, p1, g25, #{k}")
    ops += [f"or.skipinv o1, {pa}, {imm(12 | (words[1] & 0x30))}", f"or.skipinv o1, {pa}, {imm(words[1])}"]
    for j in range(2, 8):
        end = ".end" if j == 7 else ""
        if j == pj:
            seq = [("p1", wp1), ("!p1", wnp1)] if order == "pa" else [("!p1", wnp1), ("p1", wp1)]
            ops += [f"{p} or.skipinv o{j}, {pa}, {imm(w)}" for p, w in seq]
        elif words[j] is not None:
            ops.append(f"or.skipinv{end} o{j}, {pa}, {imm(words[j])}")
    assert ops[-1].startswith("or.skipinv.end o7"), "o7 is the last write"
    return "\n".join(ops) + "\n"


def frozen_words(cfg):
    """The low-6 output words the plan sets for a configuration (None for the reused and E709 programs)."""
    if cfg == "all4":
        return M.all4()
    if cfg.startswith("w-"):
        return M.walk(int(cfg[2:]))
    if cfg in M.INDEP:
        return M.indep(cfg)
    return M.base()                                   # predicate rows: the base words, the predicate set's output overridden


def build():
    rows, preds, needs = [], [], []
    P = lambda n, q, v, mdl, st: preds.append((n, q, v, mdl, st))
    K.BINS.mkdir(exist_ok=True)
    K.probe._assemble((REPO / "probes/usse/templates/pds_iter_xy.s").read_text(), K.BINS / "pds_iter_xy.bin", "pds")
    K.probe._assemble((REPO / "probes/usse/templates/vtx_coords.s").read_text(), K.BINS / "vtx_coords.bin")
    needs += ["$S/pds_iter_xy.bin", "$S/vtx_coords.bin"]
    PD = DATA / "vdm/verification-1141ta/programs"
    for ax in "xy":                                             # E709's own programs, byte for byte (as R4)
        build_bin(f"r4o-e709-{ax}", (PD / f"o4g-3-{ax}.s").read_text())
    for cfg, (stem, _m) in R4_REUSED.items():                   # R4's own programs, byte for byte (copied from the published bins)
        for ax in "xy":
            (K.BINS / f"{stem}-{ax}.bin").write_bytes((R4PIX / "bins" / f"{stem}-{ax}.bin").read_bytes())
    state = {"m": M0}
    markers, words_of = {}, {}

    def job(cfg, ax, st, role, pred=None, name=None):
        jn = name or f"{cfg}-{ax}"
        if cfg == "c-e709":
            prog = f"r4o-e709-{ax}"
        elif cfg[2:] in R4_REUSED:
            stem, mx = R4_REUSED[cfg[2:]]
            prog = f"{stem}-{ax}"
            markers[jn] = mx + (ax == "y")
        else:
            state["m"] += 1
            m = state["m"]
            prog = f"r5o-{cfg}-{ax}"
            w6 = frozen_words(cfg[2:] if cfg.startswith("c-") else cfg)
            words_of[jn] = (w6, pred)
            build_bin(prog, program(ax, m, w6, pred))
            markers[jn] = m
        needs.append(f"$S/{prog}.bin")
        rows.append(Row(jn, st, K.SAFE, KNOBS, "-", C_BASE.format(prog=prog), role))
        return jn

    def pair(cfg, st, role, pred=None):
        jx = job(cfg, "x", st, role, pred)
        job(cfg, "y", st, role + " (the y job: source pixel identity)", pred)
        if jx in markers:
            P(jx, "marker", f"{markers[jx]:#x}", "frozen program marker (x job; the y job's is +1): ((word & 0xffff) >> 6)", st)
        return jx

    # ------------------------------------------------------------- controls (8)
    jx = pair("c-e709", "control", "G-o4 control: E709's o4g-3 unchanged (no marker), as R4")
    for q, v, why in (("g_o4_words", "10..100", "tag-5 words in the x and y job (R1, S1b, R3, R4: 22 to 63)"),
                      ("g_o4_pairs", "5..60", "pairs (R4: 8 to 42)"), ("g_o4_parity", "even,even", "every pair source (even x, even y)"),
                      ("g_o4_tag5p_max", "2", "no tag-13 word in the x job")):
        P(jx, q, v, "G-o4 structural, as R4 (" + why + ")", "control")
    P(jx, "bits54_x", "3", "E850: bits 5:4 set at every tag-5 word of c-e709-x (0xcf5, 39 of 39); reported, not gating", "control")
    jx = pair("c-u", "control", "G-o1 control: R4's own c-u program byte for byte (o1 12 then 2, o4 one write A)")
    P(jx, "ctl_min_frac", "0.98", "frozen criterion (R1 / S1b / R3 / R4: tag-2 fraction 0.990 to 0.996)", "control")
    jx = pair("c-all4", "control", "the control that can fail: every output's word with bit 4; all nine models read 5:1")
    for mdl in M.MODELS:
        P(jx, "o4_word", M.predict(mdl, M.all4()), mdl, "control")
    jx = pair("c-v-a4", "control", "bridge to E838: R4's own c-v-a4 program (o4 = tag 5 with bit 4, alone), read class A = 5:0")
    P(jx, "o4_word", "5:0", "E838 / E850: c-v-a4 read class A (tag 5, bits 5:4 clear) in both jobs", "control")
    # ------------------------------------------------------------- the walk (16), HELD OUT
    for j in range(8):
        jx = pair(f"w-{j}", "heldout", f"walk: o{j}'s word with bit 4, every other output's with bit 5")
        for mdl in M.MODELS:
            P(jx, "o4_word", M.predict(mdl, M.walk(j)), mdl, "heldout")
        if j in (0, 1):
            tag = M.TAG[j]
            P(jx, "pos_ctl", f"tag{tag}:bit4>=0.95", f"positive control: >= 95% of the {'own-pixel tag-1' if j == 0 else 'tag-2'} "
              f"words carry bit 4 (o{j}'s own bit shows where its word lands)", "control")
    # ------------------------------------------------------------- independent rows (8), HELD OUT
    for cfg, txt in (("z-o3", "o3 = tag 0"), ("l-o4", "o4 = tag 4"), ("l-o6", "o6 = tag 3"), ("n-o4", "no o4 write")):
        jx = pair(cfg, "heldout", f"independent row: {txt}")
        for mdl in M.MODELS:
            P(jx, "o4_word", M.predict(mdl, M.indep(cfg)), mdl, "heldout")
    # ------------------------------------------------------------- predicate rows (24), HELD OUT, gated by the walk's model
    for pset, txt in (("p4", "p1 o4 = tag 5, !p1 o4 = tag 4"), ("p3", "p1 o3 = tag 4, !p1 o3 = tag 4 with bit 4")):
        for order in M.ORDERS:
            for k in M.PRED_K:
                cfg = f"{pset}-{order}-k{k}"
                jx = pair(cfg, "heldout", f"predicate {pset.upper()} k = {k}, {'p1 first' if order == 'pa' else '!p1 first'}: {txt}",
                          pred=(pset, order, k))
                for mdl in M.MODELS:
                    for g in ("gated", "ignored"):
                        P(jx, "o4_word", M.predict(mdl, M.pred_words(pset, order, k, g)), f"{mdl}+{g}", "heldout")
    # ------------------------------------------------------------- replicate (2): w-3 again
    for ax in "xy":
        src = next(r for r in rows if r.name == f"w-3-{ax}")
        rows.append(Row(f"w-3-{ax}-rep", "replicate", K.SAFE, KNOBS, "-", src.args, f"replicate of w-3-{ax} (same program)"))
    P("w-3-x-rep", "marker", f"{markers['w-3-x']:#x}", "frozen program marker (identical program)", "replicate")
    for mdl in M.MODELS:
        P("w-3-x-rep", "o4_word", M.predict(mdl, M.walk(3)), mdl, "replicate")
    P("@p5-o4", "family", " ".join(M.MODELS), "E850 (resgx545 main): the nine bitwise models of 821 that fit every kept configuration of E808 and E838; R-CLR refuted", "heldout")
    P("@p5-o4", "p4_gate", " ".join(M.READS_O4), "P4 is scored only if the walk's model reads o4", "heldout")
    P("@p5-o4", "p3_gate", " ".join(M.READS_O3), "P3 is scored only if the walk's model reads o3", "heldout")
    P("@p5-o4", "class_rule", ">=10 words in both jobs, <=2 of any other; d1 10..100 displaced tag-1 pairs",
      "R4's rule; the displaced tag-1 count of R4's 17 configurations is 0 (tests/test_replay.py)", "heldout")
    (K.BINS / "p5o4-markers.tsv").write_text("".join(f"{k}\t{v}\n" for k, v in markers.items()))
    (K.BINS / "p5o4-words.tsv").write_text("".join(
        f"{k}\t{','.join('-' if w[0][j] is None else f'{w[0][j]:#04x}' for j in range(8))}\t{w[1] or '-'}\n" for k, w in words_of.items()))
    head = """Q276 (pixel), stage p5-o4: what the tag-5 word is.  Nine bitwise models of one instance's outputs fit every kept configuration of
E808 and E838 (OR(o0,o3), AND(o4,o6), XOR(o0,o2,o6), XOR(o3,o5,o6), MUX(o4;o0/o2/o3/o5/o6)).  R4's shape and decode; word low 16 bits =
marker << 6 | bits 5:4 << 4 | tag.  Walk w-j (bit 4 on o_j, bit 5 on the rest): nine different vectors of bits 5:4 at the tag-5 words.
Independent rows z-o3, l-o4, l-o6, n-o4; predicate sets P4 (o4) and P3 (o3), k = 0, 3, 7, both orders, scored only if the walk's model
reads that output.  Controls first: c-e709 (G-o4), c-u (G-o1), c-all4 (5:1 in all models; 5:0 voids the stage), c-v-a4 (R4's program,
class A).  Replicate w-3.  No fault is expected; any fault, hang or STATUS2 other than 0x400 after a reset stops the stage."""
    return rows, preds, list(dict.fromkeys(needs)), head


if __name__ == "__main__":
    r, p, n, h = build()
    K.write_table(STAGE, r, n, h)
    K.write_preds(STAGE, p)
    print(f"{STAGE}: {len(r)} jobs, {len(p)} prediction rows, {len(n)} programs")
