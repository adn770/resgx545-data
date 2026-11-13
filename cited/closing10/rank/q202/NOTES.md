# Q202 clause 1: E606 coverage on perspective triangles

Ran: `/Users/jtorra/src/resgx545/.venv/bin/python -I q202_cov.py > q202_cov.out` (numpy only for
float32). rule.json (rivals) hashed in rule.sha256 before any image pixel was compared; I had only
glanced at b-01's first background rows and its parameter header to learn the formats.

Jobs: g6-rwa 8 + g6-rw 106 = 114 (closing-r6-pixel, out/20261112-142113), 64x64, w from 2.5e-4 to
8027, 58 distinct snapped triangles, 112 distinct w triples. Vertices from the frozen
rwdesign*.py (VX, VY exact, w = C x + D, scale S, window = 32 + 32 S x / w); the stored window
coordinates decoded from the parameter buffers (packed block, dwords 21..28) equal the exact snapped
vertices for all 342 vertices (also the float32 rivals').

Result: all four rivals (H-EXACT, H-F32, H-F32R, H-STORED) 114/114 jobs, 0 of 466944 pixels off,
7296/7296 rows. Discriminating pixels (rivals predict differently): 0. So the images decide nothing
between the rivals; they confirm E606 given the vertex window coordinates (the TA's stored x/w
equals exact x/w snapped to 1/256 at every vertex) and that the ISP does no perspective-specific
thing in coverage.

Caveats: the window ratio max(w)/min(w) is 1.0 to 1.1 in 105 of 114 jobs (only 6 at 1.8, one at 3.0,
one at 1.4), so the w ramp is mild and the vertices' x/w are nearly the same across jobs; the float32
error of x/w (about 1e-6 px) would only matter for a pixel centre within that of an edge, and none
is (centres exactly on an edge, margin 0, are ties, same in all rivals). Not scored: g5 jobs (same
family, closing-r5-pixel).

Refutation: a job where H-STORED (or another rival) is exact and H-EXACT is not, or a covered pixel
off E606 given the stored vertices. None. Held out: E606 frozen 2026-11-09, jobs ran 2026-11-12;
the rivals were declared before the comparison. A discriminating test would need a perspective
triangle with a centre within about 1e-5 px of an edge, or one with a large w ramp and a long edge.
