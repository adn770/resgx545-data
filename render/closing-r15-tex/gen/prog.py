# SPDX-License-Identifier: MIT
"""prog.py: the probe programs of r15-tex. A job's coordinates (u in r24, v in r25, the LOD in r26),
its four T words (r20 to r23) and its sample instruction fill the published template
(resgx545-data texture/p1141/templates/tx_map.s, pinned) as the published builder does
(texture/p1141/support/build.py, pinned: its axis_code for `bits`, `map` and `lin`, its T-word
moves), plus one axis kind of this session:
  ("step", K, C)   K (1 + (y >> 2) / 8) + C: y >> 2 put in the mantissa of 1.0 (three bits down),
                   one fmad; K = 8 and C = c - 8 give (y >> 2) + c exactly (pa0 = (y << 16) | x,
                   y < 32, so pa0 >> 18 is y >> 2)
tests/test_gen.py checks that E562's two control programs rebuild byte for byte through this path
and that every pixel's coordinates are exact in float32 (gen/chain.py coord())."""
import pins
import tex


def step_code(spec, dst):
    _, kb, cb = spec
    return ["shr.skipinv r1, pa0, #18", "shl.skipinv r1, r1, #20",
            "or.skipinv r1, r1, #0x3f800000", "mov.skipinv r2, #0x%08x" % kb,
            "mov.skipinv r3, #0x%08x" % cb, "fmad.skipinv %s, r1, r2, r3" % dst]


def axis(spec, dst):
    if spec[0] == "step":
        return step_code(spec, dst)
    return pins.module(tex.BUILD).axis_code(list(spec), dst)


def text(job, base=0):
    """The program text of a job dict (gen/chain.py: u, v, lod, t0, t1, t3, smp)."""
    lines = axis(job["u"], "r24") + axis(job["v"], "r25") + axis(job["lod"], "r26")
    t2 = 0x5CAF0000 | base * 4
    lines += ["mov r20, #0x%08x" % job["t0"], "mov r21, #0x%08x" % job["t1"],
              "mov r22, #0x%08x" % t2, "mov r23, #0x%08x" % job["t3"]]
    return (pins.blob(tex.TEMPLATE).decode().replace("{PRE}", "")
            .replace("{SETUP}", "\n".join(lines)).replace("{SMP}", job["smp"]))
