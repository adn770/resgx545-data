# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""A case's spec as USSE text: the PRE, SETUP and SMP inputs of templates/tx_map.s.

The program reads pa0 = (y << 16) | x of the fill (probe --coords), builds the coordinates the spec
names with integer and float instructions, loads the four state words, samples, and writes the result
as o0. It shares nothing with recompute/texmodel.py but the spec.
"""
from __future__ import annotations


def axis_code(spec, dst: str) -> list[str]:
    k = spec[0]
    if k == "bits":
        return [f"mov.skipinv {dst}, #0x{spec[1]:08x}"]
    if k == "map":
        _, ax, a, off, exp = spec
        out = ["and.skipinv r1, pa0, #0x3f" if ax == "x" else "shr.skipinv r1, pa0, #16"]
        if off:
            out.append(f"or.skipinv r1, r1, #{off}")
        out += [f"and.skipinv r1, r1, #{(1 << a) - 1}", "shl.skipinv r1, r1, #1", "or.skipinv r1, r1, #1",
                f"shl.skipinv r1, r1, #{22 - a}", f"or.skipinv {dst}, r1, #0x{exp:08x}"]
        return out
    if k == "lin":
        _, ax, kb, cb = spec
        out = ["and.skipinv r1, pa0, #0x3f" if ax == "x" else "shr.skipinv r1, pa0, #16",
               f"shl.skipinv r1, r1, #{17 if ax == 'x' else 18}", "or.skipinv r1, r1, #0x3f800000",
               f"mov.skipinv r2, #0x{kb:08x}", f"mov.skipinv r3, #0x{cb:08x}",
               f"fmad.skipinv {dst}, r1, r2, r3"]
        return out
    raise ValueError(spec)


def pre_code(inject: dict) -> str:
    if not inject:
        return ""
    lines, group = [], None
    for idx in sorted(int(k) for k in inject):
        g = idx // 64
        if g != group:
            lines.append(f"mov.skipinv r30, #0x5CAF{g * 256:04X}")
            group = g
        lines += [f"mov.skipinv r31, #0x{inject[str(idx)] & 0xFFFFFFFF:08x}", f"stad [r30,+#{idx % 64}], r31"]
    return "\n".join(lines + ["idf drc0, bif", "wdf drc0"])


def setup_code(spec: dict) -> str:
    ins = spec["ins"]
    lines = axis_code(spec["u"], "r24") + axis_code(spec["v"], "r25")
    if ins == "replace" or ins == "bias":
        lines += axis_code(spec["lod"], "r26")
    elif ins == "grad":
        for k, g in enumerate(spec["grad"]):
            lines += axis_code(g, f"r{26 + k}")
    elif ins == "3d":
        lines += axis_code(spec["w"], "r26")
    t2 = 0x5CAF0000 | spec["base"] * 4
    lines += [f"mov r20, #0x{spec['t0']:08x}", f"mov r21, #0x{spec['t1']:08x}", f"mov r22, #0x{t2:08x}",
              f"mov r23, #0x{spec['t3']:08x}"]
    return "\n".join(lines)


SMP = {"replace": "smp2dreplace r10, r24, r20, r26, drc0", "grad": "smp2dgrad r10, r24, r20, r26, drc0",
       "auto": "smp2d r10, r24, r20, drc0", "bias": "smp2dbias r10, r24, r20, r26, drc0",
       "3d": "smp3d r10, r24, r20, drc0", "none": "smp2d r10, r24, r20, drc0"}


def case_inputs(spec: dict) -> list[str]:
    return [pre_code(spec.get("inject", {})), setup_code(spec), SMP[spec["ins"]]]
