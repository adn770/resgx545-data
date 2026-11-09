#!/usr/bin/env python3
"""Goal 1d: Q140's layout formula on E507's 12 sizes, with the factor f a free integer, from my
own transcription of sgx_render_layout / sgx_render_tadata_layout (linux fork, landed source).
The factor is the number of region-header arrays the TA writes at CR_TE_AA 0xe0000000."""
import sys
sys.dont_write_bytecode = True
up = lambda v, a: -(-v // a) * a
cd = lambda a, b: -(-a // b)


def layout(w, h):
    tx, ty = cd(w, 32), cd(h, 16)
    n = 4 if w * h >= 640 * 480 else 2
    mx, my = up(cd(tx, n), 4), up(cd(ty, n), 4)
    span = max(n * mx, n * my)
    side = 1
    while side < span:
        side <<= 1
    blocks = (mx // 4) * (my // 4)
    arr = 0xC0 * blocks
    rgn_size = arr * n * n
    tail = 4 * side * side
    t_tail = 0
    control = t_tail + up(tail, 4096)
    otpm = control + 4096
    state = otpm + 4096
    rgn = state + 4096
    zls = rgn + up(rgn_size, 4096)
    size = zls + up(rgn_size, 4096)
    return dict(n=n, mx=mx, my=my, blocks=blocks, rgn_size=rgn_size, rgn=rgn, zls=zls, size=size)


# E507 (landed): size -> completes? and the fault page when it does not
OBS = {(64, 64): None, (128, 64): None, (128, 128): None, (256, 128): None, (96, 48): None,
       (192, 96): None, (320, 160): 6, (384, 192): 6, (448, 224): 6, (512, 256): 6,
       (512, 384): 8, (640, 480): 0xA}


def predict(w, h, f):
    L = layout(w, h)
    end = L["rgn"] + f * L["rgn_size"]
    return None if end <= L["size"] else L["size"] >> 12


if __name__ == "__main__":
    for f in range(1, 9):
        ok = sum(predict(w, h, f) == o for (w, h), o in OBS.items())
        print(f"factor {f}: {ok} of 12 sizes (completes / fault page) agree")
    print("\nsize: rgn_size rgn size n blocks")
    for (w, h) in OBS:
        L = layout(w, h); print(f"  {w}x{h}: {L['rgn_size']:#x} {L['rgn']:#x} {L['size']:#x} n={L['n']} blocks={L['blocks']}")
    print("\nthe new sizes, per factor (None = completes, else fault page)")
    for w, h in ((256, 160), (288, 144), (320, 128), (256, 288), (256, 272), (512, 128), (384, 384), (576, 224)):
        print(f"  {w}x{h}:", {f: predict(w, h, f) for f in (3, 4, 5)}, layout(w, h)["rgn_size"])
