# SPDX-License-Identifier: MIT
"""vdm.py: stage vdm (R8-4, Q271): E703's capacity form (probe --tri pixpds:12, 126 vertices, N
coordinates a vertex) with VDM word 7 SET by `--vdm 7=V` (src/tri_probe.c: N=V sets the word,
N^=V flips bits; E703 could only xor, so it had no forced = natural job).

The natural word 7 of each form, read from a dry run of the pinned tool source (resgx545 4623753,
sgxfive-test.c sha256 703cbcea..., built on the Mac against the library's mock, `--emit-scene`,
which writes the render's words after the pokes; debug/, not shipped): N = 8 0x03c00082, N = 2
0x02c00082, i.e. render.c's 1 << 24 | 3 << 22 | 1 << 7 | data rows, bits 31:24 set by tri_probe.c
to the rows (4 + N + 3) / 4 (3 and 2), bits 6:0 the PDS data rows of the vertex slot (2 for
vtx_c8.bin and vtx_c2.bin). tests/test_gen.py repeats the dry run when the mock build is there.
V (vertices a task) is set as E703 did, by flipping word 6's MAX_VERTICES (31:28, natural 15):
6^=((15 ^ (V - 1)) << 28).

N = 11 of the plan is replaced by N = 8 (natural rows 3, forced 2 below it): the N = 8 and N = 2
programs are published (render/closing-s1/bins, pinned); N = 11's are not, and E703 had both
forms. Frozen (relational: the image is the --pixels rows, its hash the scorer's sha256 of them):
  forced = natural (7 = the natural word): the image equals its natural twin's (the control of the
    forcing itself; H-FORCE-NEUTRAL), at N = 8 V = 4 and N = 2 V = 2
  forced = natural + 1 at N = 2, V = 2 (rows 3, product 6): H-COUNT (rows a count, the task's
    output holds R V rows, room for every vertex: the image equals the natural twin's) against
    H-LAYOUT (rows a stride: every vertex read at the forced stride, the image differs); twice
    (replicates)
  forced below natural at N = 8, V = 8 (rows 2, product 16): both rivals predict a changed image
    (H-COUNT: 16 rows hold 5 of 8 vertices of 3 rows; H-LAYOUT: the stride) [infer]; a reading
    for the fold's decoder (the render's memory is kept by --dump-render)."""
NATURAL7 = {8: 0x03c00082, 2: 0x02c00082}
ROWS = {8: 3, 2: 2}
BINS = ("pix_pa0.bin", "vtx_c8.bin", "vtx_c2.bin", "p1131-fmt-8__0.bin", "p1131-fmt-2__0.bin")
BINS_FROM = "render/closing-s1/bins"


def word7(n, rows):
    return (NATURAL7[n] & 0x00ffffff) | rows << 24


def flip6(v):
    return (15 ^ (v - 1)) << 28


def jobs():
    """[(name, set, N, V, rows or None, twin)]: twin is the natural job a row is compared with
    (run before it); the forced = natural rows are the controls (they can fail: a forcing that
    breaks a job changes the image), the natural jobs their references."""
    return [
        ("vdm-nat-n8-v4", "reference", 8, 4, None, None),
        ("vdm-set-n8-v4", "control", 8, 4, 3, "vdm-nat-n8-v4"),
        ("vdm-nat-n2-v2", "reference", 2, 2, None, None),
        ("vdm-set-n2-v2", "control", 2, 2, 2, "vdm-nat-n2-v2"),
        ("vdm-r3-n2-v2", "heldout", 2, 2, 3, "vdm-nat-n2-v2"),
        ("vdm-r3-n2-v2-r2", "replicate", 2, 2, 3, "vdm-nat-n2-v2"),
        ("vdm-nat-n8-v8", "reference", 8, 8, None, None),
        ("vdm-r2-n8-v8", "explore", 8, 8, 2, "vdm-nat-n8-v8"),
    ]


def args(n, v, rows):
    a = ["probe", "--tri", "pixpds:12", "--temps", "32", "--width", "64", "--height", "64",
         "--vertices", "126", "--vtx-coords", str(n), "--vdm", "6^=0x%08x" % flip6(v)]
    if rows is not None:
        a += ["--vdm", "7=0x%08x" % word7(n, rows)]
    return a + ["--pixels", "--dump-render", "$W", "--slot", "pixel=$S/bins/pix_pa0.bin",
                "--slot", "vtxuse=$S/bins/vtx_c%d.bin" % n, "$S/bins/p1131-fmt-%d__0.bin" % n]


def predicted(name, rows, n, twin):
    """{model: "same" | "differs"} against the twin."""
    if rows is None:
        return {}
    if rows == ROWS[n]:
        return {"H-FORCE-NEUTRAL": "same"}
    if rows > ROWS[n]:
        return {"H-COUNT": "same", "H-LAYOUT": "differs"}
    return {"H-COUNT": "differs", "H-LAYOUT": "differs"}
