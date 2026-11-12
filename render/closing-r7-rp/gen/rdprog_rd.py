# SPDX-License-Identifier: MIT
"""rdprog_rd.py: the pixel programs of stages p7-rdc and p7-rd (r7-rp, Q276).  `program` and `special` are R6's generator method
copied unchanged from closing6/r6-pixel/gen/r6_rd.py (program(), special(): the same text for the same configuration and marker; the
generator re-assembles R6's own configurations with them and must get R6's bins byte for byte).  `clean_pred` is the one new text
shape: cl-p4, cl-4's program with its o4 write under `p1` (p1 = (g25 == k) set right after o0, R6's predicate shape) and no
unpredicated o4 write."""
from __future__ import annotations


def program(ax, m, cfg):
    """The pixel program of a readback configuration (rdmodel.config)."""
    pa = "pa0" if ax == "x" else "pa1"
    imm = lambda w6: f"#0x{m * 64 + w6:x}"
    w, j_read, pred = cfg["words"], cfg["read"], cfg["pred"]
    ops = ["phas #0, #0, pixel, end, parallel", f"or.skipinv o0, {pa}, {imm(w[0])}"]
    if pred:
        ops.append(f"xor.testtaz.chan0 !c0, p1, g25, #{pred[1]}")
    if w[1] is not None:
        ops += [f"or.skipinv o1, {pa}, {imm(12 | (w[1] & 0x30))}", f"or.skipinv o1, {pa}, {imm(w[1])}"]
    for j in range(2, 8):
        if pred and j == pred[0]:
            ops += [f"or.skipinv o{j}, {pa}, {imm(w[j])}", f"p1 or.skipinv o{j}, {pa}, {imm(w[j] | 0x10)}"]
        elif w[j] is not None:
            ops.append(f"or.skipinv o{j}, {pa}, {imm(w[j])}")
    ops += [f"mov.skipinv r10, o{j_read}", "mov.skipinv.end o0, r10"]
    return "\n".join(ops) + "\n"


def special(ax, m, name):
    """c-ow, c-rd-0, c-prd-0-kK (plan 2.2).  c-prd-0 ends with an UNPREDICATED write (o7, tag 8) carrying .end: no row of this
    session ends on a predicated instruction (the plan's `p1 or.skipinv.end o0` would end the task under a predicate, a form no kept
    job ran; the deviation is in README.md)."""
    pa = "pa0" if ax == "x" else "pa1"
    imm = lambda w6: f"#0x{m * 64 + w6:x}"
    head = "phas #0, #0, pixel, end, parallel"
    if name == "c-ow":
        ops = [head, f"or.skipinv o0, {pa}, {imm(0x21)}", f"or.skipinv.end o0, {pa}, {imm(0x11)}"]
    elif name == "c-rd-0":
        ops = [head, f"or.skipinv o0, {pa}, {imm(0x21)}", "mov.skipinv r10, o0", f"or.skipinv o0, {pa}, {imm(0x31)}",
               "mov.skipinv.end o0, r10"]
    elif name.startswith("c-prd-0-k"):
        k = int(name[len("c-prd-0-k"):])
        ops = [head, f"or.skipinv o0, {pa}, {imm(0x21)}", f"xor.testtaz.chan0 !c0, p1, g25, #{k}",
               f"p1 or.skipinv o0, {pa}, {imm(0x11)}", f"or.skipinv.end o7, {pa}, {imm(0x08)}"]
    else:
        raise ValueError(name)
    return "\n".join(ops) + "\n"


def clean_pred(ax, m, cfg):
    """cl-p4: o0 = word A; p1 = (g25 == k); `p1 or.skipinv oJ` = word B (the only write to oJ); then R6's readback of oJ."""
    pa = "pa0" if ax == "x" else "pa1"
    imm = lambda w6: f"#0x{m * 64 + w6:x}"
    w, j, (pj, k) = cfg["words"], cfg["read"], cfg["pred"]
    assert pj == j and all(w[i] is None for i in range(1, 8) if i != j)
    ops = ["phas #0, #0, pixel, end, parallel", f"or.skipinv o0, {pa}, {imm(w[0])}",
           f"xor.testtaz.chan0 !c0, p1, g25, #{k}", f"p1 or.skipinv o{j}, {pa}, {imm(w[j])}",
           f"mov.skipinv r10, o{j}", "mov.skipinv.end o0, r10"]
    return "\n".join(ops) + "\n"
