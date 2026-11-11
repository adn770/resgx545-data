"""Kernel batch, Q140: the kernel's TA data layout (formula transcribed from the linux fork,
branch resgx545, sgx_render.c sgx_render_layout / sgx_render_tadata_layout) against every 4x
size on record (E507 12 sizes, E729 5, E788 a5/a6), under f = 4 arrays of the target's rgn_size
from td.rgn (E788). Read-only, no data files: the outcomes are typed from the records' text.
Prints: per size, whether 4 arrays fit the layout made for (max_w, max_h), the first page past
the layout (the predicted fault page, slot 0 at 0x20000), the record's outcome, and the layout
the proposed knob render_rgn_arrays=4 gives. Then the largest maxima that still fit the 2 MiB
TA-data slot with 4 arrays."""
def rup(a, m): return (a + m - 1) // m * m
def layout(w, h, f=1):
    tx, ty = (w + 31) // 32, (h + 15) // 16
    n = 4 if w * h >= 640 * 480 else 2
    mx, my = rup((tx + n - 1) // n, 4), rup((ty + n - 1) // n, 4)
    span = max(n * mx, n * my); side = 1
    while side < span: side <<= 1
    rgn_size = 0xc0 * (mx // 4) * (my // 4) * n * n
    rgn = rup(4 * side * side, 4096) + 3 * 4096
    zls = rgn + rup(f * rgn_size, 4096)
    return rgn_size, rgn, zls, zls + rup(rgn_size, 4096)
# (target, context maximum, outcome on record: None = completed, else the fault page)
ROWS = [((64, 64), None, None, "E507"), ((128, 64), None, None, "E507"), ((128, 128), None, None, "E507"),
        ((256, 128), None, None, "E507"), ((96, 48), None, None, "E507"), ((192, 96), None, None, "E507"),
        ((320, 160), None, 0x20006, "E507"), ((384, 192), None, 0x20006, "E507"),
        ((448, 224), None, 0x20006, "E507"), ((512, 256), None, 0x20006, "E507"),
        ((512, 384), None, 0x20008, "E507"), ((640, 480), None, 0x2000a, "E507"),
        ((256, 160), None, None, "E729"), ((320, 128), None, None, "E729"),
        ((288, 144), None, 0x20006, "E729"), ((256, 288), None, 0x20006, "E729"),
        ((384, 384), None, 0x20008, "E729"),
        ((320, 400), (544, 400), None, "E788 a5"), ((320, 400), None, 0x20008, "E788 a6")]
ok = 0
for (t, mx, seen, rec) in ROWS:
    m = mx or t
    rs, _, _, _ = layout(*t)
    _, rgn, zls, size = layout(*m)
    need = rgn + 4 * rs
    pred = None if need <= size else 0x20000 + size // 4096
    _, rgn4, zls4, size4 = layout(*m, f=4)
    good = pred == seen
    ok += good
    print("%-8s %4dx%-4d max %4dx%-4d rgn_size %#7x size %#7x need %#7x pred %-8s seen %-8s %s | knob 4: size %#7x fits %s" % (
        rec, t[0], t[1], m[0], m[1], rs, size, need, hex(pred) if pred else "complete",
        hex(seen) if seen else "complete", "ok" if good else "MISMATCH", size4,
        rgn4 + 4 * layout(*t)[0] <= zls4))
print("model agrees with %d of %d rows" % (ok, len(ROWS)))
SLOT = 0x200000
for m in [(1024, 768), (1920, 1080), (2048, 2048), (4096, 2048), (4096, 4096)]:
    print("max %dx%d: size f=1 %#x, f=4 %#x, fits the 2 MiB slot %s" % (m[0], m[1], layout(*m)[3], layout(*m, 4)[3], layout(*m, 4)[3] <= SLOT))
