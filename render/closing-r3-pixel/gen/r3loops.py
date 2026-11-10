# SPDX-License-Identifier: MIT
"""R3-pixel loop programs (decision R3-P1: the program-side loop fix only, no tool change).

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

R3 = pathlib.Path(__file__).resolve().parent.parent
TEMPLATES = R3 / "templates"

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
           f"; {name}: N = {n}, body {BODY_LEN[kind]} instructions; R3-pixel (Q082): RELATIVE backward branch, MARK proof",
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


VBODY = {"b8v": (5, 8), "b16v": (13, 16), "b4v": (1, 4)}


def vertex_loop_source(kind: str, n: int, zb: int = 0x3E800000):
    """(name, text): the vertex loop of templates/vtx_loop.s, N iterations, relative branch, depth proof."""
    if kind not in VBODY:
        raise LoopError(f"unknown vertex kind {kind}")
    nimae, body = VBODY[kind]
    imae = "\n".join("        " + IMAE.format(d=4 + i % 5) for i in range(nimae))
    t = (TEMPLATES / "vtx_loop.s").read_text()
    text = (t.replace("{PH2}", str(14 + body)).replace("{BODY}", str(body)).replace("{IMAE}", imae)
            .replace("{BACK}", f"0x{body - 1:08x}").replace("{N}", str(n)).replace("{ZB}", f"0x{zb:08X}"))
    assert_no_ba(text, "a vertex slot")
    return f"vloop-{kind}-i{n}", text
