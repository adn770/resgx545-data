# SPDX-License-Identifier: MIT
"""oq069.py: the offline gate OQ069 of round 16's plan (section 5, decision R16-8 (a)), run before
zoff froze. E987's zw-0125 (w = 0.125) and E981's z2-a-f0 (w = 0.25), both format 0 at 256 x 128
G 7 with the viewport's z scale at t10's 0.5, replayed through:
  H-POLYCLIP  E1056's polygon cut at z = 0 of z = t + w - 0.5 (sgx-pipe isp::depth_cut_image:
              gen/oq069rs, its output gen/oq069rs.out; z16.zoff_pixel is the same cut in Python,
              the counts checked equal by tests/test_gen.py)
  H-LIN       E987's (1.6 w + 0.2) t, within 1e-5 relative [fitted on these two rows]
A form passes the gate when it reproduces the kept dwords. H-POLYCLIP leaves pixels undrawn that
both kept rows drew; H-LIN reproduces every dword but one set of 912 pixels, the same in both rows
(E987's bend). gen/make.py writes the report to gen/oq069.out."""
import z16 as Z


def report():
    lines = [__doc__.splitlines()[0], ""]
    sets = {}
    for key, w in (("zw-0125.dep", 0.125), ("z2-a-f0.dep", 0.25)):
        dep = Z.dwords(Z.kept(key))
        drawn = sum(1 for y in range(128) for x in range(256)
                    if dep[Z.store_dword(x, y, 7)] != Z.FILL_DEAD)
        cov = Z.zoff_drawn("H-POLYCLIP", w, 0.5)
        sets[key] = Z.bend(dep, w)
        held, txt = Z.zoff_fit(dep, "H-LIN", w, 0.5)
        held_out, txt_out = Z.zoff_fit(dep, "H-LIN", w, 0.5, frozenset(sets[key]))
        poly = Z.zoff_fit(dep, "H-POLYCLIP", w, 0.5)
        lines += [f"{key[:-4]} (w {w}): kept {drawn} of 32768 dwords written",
                  f"  H-POLYCLIP covers {cov} of 32768 (the cut at t = {0.5 - w}): dwords {poly[1]}"
                  f" -> {'reproduces' if poly[0] else 'fails'}",
                  f"  H-LIN {txt} dwords; outside its {len(sets[key])} off pixels {txt_out}"
                  f" -> {'reproduces' if held_out else 'fails'} outside them",
                  f"  off pixels: min x/512 + y/256 = "
                  f"{min((x + 0.5) / 512 + (y + 0.5) / 256 for x, y in sets[key]):.4f}"]
    same = sets["zw-0125.dep"] == sets["z2-a-f0.dep"]
    lines += ["", f"the off sets of the two rows are {'the same' if same else 'different'} "
              f"({len(sets['zw-0125.dep'])} pixels): BEND",
              "gate: H-POLYCLIP fails (coverage); H-LIN reproduces every kept dword outside BEND"
              if same else "gate: no form reproduces the kept dwords"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(report(), end="")
