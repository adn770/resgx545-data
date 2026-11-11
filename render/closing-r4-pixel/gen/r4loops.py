# SPDX-License-Identifier: MIT
"""R4-pixel loop programs (R3-pixel's, extended) (decision R3-P1: the program-side loop fix only, no tool change).

Why E770's pixel loops wrote a fraction of the pixels: R1-events closed them with an ABSOLUTE branch `p0 ba #4`, which counts
from the code base, and a `--tri pixel` program sits at index 0x20 of the pixel page (a fill's at the heap base, index 0).  Here
every loop that is not a q-f0 abs control closes with the RELATIVE `p0 br -#(BODY-1)` and proves itself with a MARK: a
prologue `mov r30, #(0xC0DE0000 | N)` and the last instruction `xor.end o0, r1, r30` (r1 is 0 when the loop ended), so o0 =
MARK exactly where the counter reached zero and an unwritten output register (E770) cannot pass.

Bodies (instruction counts include the counter update and the branch):
  b16  14 multiply-adds (imae.u r4..r17)    b12  10 imae (r4..r13)    b8  6 imae (r4..r9; E431's body)
  b4   2 imae                               b2   none                 b8n 6 `or` on temporaries, no imae
  ld8  ldad.bypassl1 + wdf + 4 imae (E769's load body; r29 = the scratch address the tool patches)
Vertex loops (templates/vtx_loop.s): b8v (5 imae, E784's), b16v (13), b4v (1); z = 0.25 + 4N ulp so the stored depth word is
0x3f200000 + N exactly.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import pathlib  # noqa: E402

R4 = pathlib.Path(__file__).resolve().parent.parent
TEMPLATES = R4 / "templates"

BODIES = {"b2": 0, "b4": 2, "b8": 6, "b12": 10, "b16": 14, "b8n": 0, "ld8": 4}
BODY_LEN = {"b2": 2, "b4": 4, "b8": 8, "b12": 12, "b16": 16, "b8n": 8, "ld8": 8}
IMAE = "imae.u r{d}, r3.low, r3.low, r3, u32"
ORN = "or.skipinv r{d}, r3, r3"


class LoopError(Exception):
    pass


def mark(n: int) -> int:
    return 0xC0DE0000 | n


def assert_no_ba(text: str, where: str) -> None:
    """Decision R3-P1: a `ba` (absolute branch) in a program placed in a --tri slot (or a vertex slot) lands in other code."""
    for ln in text.splitlines():
        code = ln.split(";")[0].strip()
        toks = code.replace(",", " ").split()
        if any(t == "ba" or t.startswith("ba.") for t in toks):
            raise LoopError(f"a `ba` (absolute branch) in {where}: {code!r}")


def pixel_loop_source(kind: str, n: int, form: str = "rel"):
    """(name, text, info): a pixel loop of N iterations.  form 'rel' (relative br + MARK; fills and --tri slots) or 'abs'
    (E431's `ba` loop, kind b8 only: the q-f0 abs control, a FILL; o0 = 0 at the end)."""
    if kind not in BODY_LEN:
        raise LoopError(f"unknown kind {kind}")
    if n < 1 or n > 0xFFFF:
        raise LoopError(f"N {n} out of range")
    if form == "abs":
        if kind != "b8":
            raise LoopError("the abs form exists for b8 only (E431's control)")
        name = f"loop-abs-b8-i{n}"
        head = ["; SPDX-License-Identifier: MIT",
                f"; {name}: E431's body 8 with its ABSOLUTE branch `ba` (the q-f0 abs control: a fill only; never in a --tri slot)",
                "phas #0, #0, pixel, end, parallel",
                f"mov.skipinv r1, #{n}", "mov.skipinv r2, #0xFFFFFFFF", "mov.skipinv r3, #0x00000003"]
        first = sum(1 for ln in head if not ln.startswith(";"))
        body = [IMAE.format(d=4 + i) for i in range(6)] + ["iadd32.skipinv.testtanz.chan0 r1, p0, r1, r2",
                                                          f"p0 ba #{first:#010x}"]
        text = "\n".join(head + body + ["mov.skipinv.end o0, r1"]) + "\n"
        return name, text, {"prologue": first, "body": 8, "form": "abs", "n": n}
    if form != "rel":
        raise LoopError(f"unknown form {form}")
    name = f"loop-rel-{kind}-i{n}"
    out = ["; SPDX-License-Identifier: MIT",
           f"; {name}: N = {n}, body {BODY_LEN[kind]} instructions; R3-pixel (Q082), reused by R4-pixel: RELATIVE backward branch, MARK proof",
           "phas #0, #0, pixel, end, parallel",
           f"mov.skipinv r1, #{n}", "mov.skipinv r2, #0xFFFFFFFF", "mov.skipinv r3, #0x00000003",
           f"mov.skipinv r30, #0x{mark(n):08X}                    ; the loop proof: o0 = MARK at the end"]
    if kind == "ld8":
        out.append("mov.skipinv r29, #0x5CAF0000                     ; the scratch buffer's address (patched by the tool)")
    prologue = sum(1 for ln in out if not ln.startswith(";"))
    body = []
    if kind == "ld8":
        body += ["ldad.bypassl1 r10, [r29,+#0], drc0", "wdf drc0"]
    if kind == "b8n":
        body += [ORN.format(d=4 + i) for i in range(6)]
    else:
        body += [IMAE.format(d=4 + i) for i in range(BODIES[kind])]
    body += ["iadd32.skipinv.testtanz.chan0 r1, p0, r1, r2", f"p0 br -#0x{BODY_LEN[kind] - 1:08x}"]
    assert len(body) == BODY_LEN[kind], (kind, len(body))
    text = "\n".join(out + body + ["xor.skipinv.end o0, r1, r30"]) + "\n"
    assert_no_ba(text, "a relative loop")
    return name, text, {"prologue": prologue, "body": BODY_LEN[kind], "form": "rel", "n": n}


VBODY = {"b8v": (5, 8), "b16v": (13, 16), "b4v": (1, 4), "b12v": (10, 13)}   # b12v (R4): 10 imae + depth accumulator + counter + branch


def vertex_loop_source(kind: str, n: int, zb: int = 0x3E800000):
    """(name, text): the vertex loop of templates/vtx_loop.s, N iterations, relative branch, depth proof.  b2v (R4): the loop of two
    instructions (counter and branch only, templates/vtx_loop2.s), proof by the counter reaching zero: o2 = (0.25 + 4 N ulp) xor
    counter, so the stored depth word is 0x3f200000 + N only if the counter ended at 0 (the same word as the other bodies)."""
    if kind == "b2v":
        t = (TEMPLATES / "vtx_loop2.s").read_text()
        text = t.replace("{N}", str(n)).replace("{ZN}", f"0x{zb + 4 * n:08X}")
        assert_no_ba(text, "a vertex slot")
        return f"vloop-b2v-i{n}", text
    if kind not in VBODY:
        raise LoopError(f"unknown vertex kind {kind}")
    nimae, body = VBODY[kind]
    imae = "\n".join("        " + IMAE.format(d=4 + i % 5) for i in range(nimae))
    t = (TEMPLATES / "vtx_loop.s").read_text()
    text = (t.replace("{PH2}", str(14 + body)).replace("{BODY}", str(body)).replace("{IMAE}", imae)
            .replace("{BACK}", f"0x{body - 1:08x}").replace("{N}", str(n)).replace("{ZB}", f"0x{zb:08X}"))
    assert_no_ba(text, "a vertex slot")
    return f"vloop-{kind}-i{n}", text


# ---- R4 (q4-f): a load and a wait with an ALU loop after it (decision: Q082 plan 3.2)
def load_mark(k: int, m=None) -> int:
    """0xC0DE0000 | K for the one-load program (m None), 0xC0DE8000 | M << 8 | K for the nested one: distinct from every R3 mark."""
    return 0xC0DE8000 | k if m is None else 0xC0DE0000 | m << 8 | k


def pixel_load_source(k: int, m=None):
    """(name, text, info): ld0 (m None): ONE load and wait, then the b8 loop (6 imae, counter, branch) K times; ldo (m = M): M times
    (load, wait, reload the counter, b8 loop K times), two counters (r1 inner, r20 outer); o0 = MARK only when BOTH counters ended
    at 0 (the last instructions or the counters, then xor with the mark).  Relative branches only (inner -#7, outer -#12).
    r29 = the scratch address the tool patches (0x5CAF0000), as the ld8 body of R3."""
    if not 1 <= k <= 0xFF or (m is not None and not 1 <= m <= 0x7F):
        raise LoopError(f"K {k} or M {m} out of range")
    name = f"loop-rel-ld0-k{k}" if m is None else f"loop-rel-ldo-k{k}-m{m}"
    mk = load_mark(k, m)
    out = ["; SPDX-License-Identifier: MIT",
           f"; {name}: " + (f"one load and wait, then the b8 loop K = {k} times" if m is None else
                            f"M = {m} times (load, wait, reload, the b8 loop K = {k} times)") + "; R4-pixel q4-f (Q082)",
           "phas #0, #0, pixel, end, parallel",
           f"mov.skipinv r1, #{k}", "mov.skipinv r2, #0xFFFFFFFF", "mov.skipinv r3, #0x00000003",
           f"mov.skipinv r30, #0x{mk:08X}                    ; the loop proof: o0 = MARK at the end",
           "mov.skipinv r29, #0x5CAF0000                     ; the scratch buffer's address (patched by the tool)"]
    if m is not None:
        out += [f"mov.skipinv r20, #{m}                           ; outer counter", f"mov.skipinv r21, #{k}                           ; inner count, reloaded"]
    prologue = sum(1 for ln in out if not ln.startswith(";"))
    body = ["ldad.bypassl1 r10, [r29,+#0], drc0", "wdf drc0"]
    if m is not None:
        body.append("mov.skipinv r1, r21")
    head = len(body)
    body += [IMAE.format(d=4 + i) for i in range(6)]
    body += ["iadd32.skipinv.testtanz.chan0 r1, p0, r1, r2", "p0 br -#0x00000007"]
    tail = []
    if m is not None:
        body += ["iadd32.skipinv.testtanz.chan0 r20, p1, r20, r2", f"p1 br -#0x{len(body) + 1:08x}"]
        tail = ["or.skipinv r1, r1, r20"]
    text = "\n".join(out + body + tail + ["xor.skipinv.end o0, r1, r30"]) + "\n"
    assert_no_ba(text, "a relative loop")
    steps = (prologue + 2 + 8 * k + 1) if m is None else (prologue + m * (head + 8 * k + 2) + 2)
    return name, text, {"prologue": prologue, "k": k, "m": m, "form": "rel", "mark": mk, "steps": steps}
