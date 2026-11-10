#!/usr/bin/env python3
"""fake_k.py: helpers of the fake tool (tests/fake_tool.sh): the frozen layout model and the images of the split flow.
  fake_k.py fits W H MW MH F        prints `ok` or `fault PAGE` (do four arrays of the target's rgn_size fit the (MW x MH, F) layout)
  fake_k.py tadata W H MW MH F OUT  a TA data dump of the (MW x MH, F) layout with four arrays written
  fake_k.py param X X OWN OUT [I=V..]  a parameter-buffer dump (OWN 1: TE 0x40 words, else the twin's) with the pokes applied
  fake_k.py image HYP TE [I=V..]    prints the image kind (empty|full|partial) of a split-flow job for the hypothesis"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "score"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "gen"))
import klib as L  # noqa: E402
import kgen as G  # noqa: E402


def main(a):
    m = a[1]
    if m == "fits":
        w, h, mw, mh, f = (int(x) for x in a[2:7])
        t, lay = L.layout(w, h), L.layout(mw, mh, f)
        need = lay["rgn"] + 4 * t["rgn_size"]
        print("ok" if need <= lay["size"] else "fault %#x" % (0x20000 + lay["size"] // 4096))
    elif m == "tadata":
        w, h, mw, mh, f = (int(x) for x in a[2:7])
        t, lay = L.layout(w, h), L.layout(mw, mh, f)
        b = bytearray(lay["size"])
        for k in range(4):
            off = lay["rgn"] + k * t["rgn_size"]
            for i in range(64):
                if off + 4 * i + 4 <= len(b):
                    struct.pack_into("<I", b, off + 4 * i, 0x10000000 | (k << 8) | i)
        open(a[7], "wb").write(bytes(b))
    elif m == "param":
        import numpy as np
        own, twin = G.pb_words()
        words = own if a[4] == "1" else twin
        arr = np.zeros(1150976, dtype="<u4")
        for i, v in words.items():
            arr[i] = v
        for p in a[6:]:
            i, v = p.split("=")
            arr[int(i)] = int(v, 0)
        open(a[5], "wb").write(arr.tobytes())
    elif m == "image":
        hyp, te, pokes = a[2], int(a[3], 16), a[4:]
        p = {int(x.split("=")[0]): int(x.split("=")[1], 0) for x in pokes}
        if te & (1 << 29):
            print("full")
        elif not p:
            print("empty")
        else:
            _, twin = G.pb_words()
            is_twin = all(p.get(i) == twin[i] for i in range(11, 27))
            if hyp == "old":
                print("full" if is_twin else "empty")
            elif hyp == "field":
                print("partial" if p.get(11) == 0xffffffff else "empty")
            elif hyp == "bothempty":
                print("empty")
            else:
                print("full" if is_twin else ("partial" if p.get(11) == 0xffffffff else "empty"))


main(sys.argv)
