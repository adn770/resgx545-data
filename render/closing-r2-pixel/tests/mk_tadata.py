"""mk_tadata.py W H MW MH SLOTS SIZE OUT: a fake TA data dump for the mock tool: the size of the MW x MH
layout (or SIZE when not 0), SLOTS region-header arrays of the W x H target's rgn_size written from rgn on
(the first 64 dwords of each non-zero), everything else zero."""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "score"))
import r2lib as L  # noqa: E402

w, h, mw, mh, slots, size = (int(x, 0) for x in sys.argv[1:7])
t, m = L.layout(w, h), L.layout(mw, mh)
size = size or m["size"]
b = bytearray(size)
for k in range(slots):
    off = m["rgn"] + k * t["rgn_size"]
    for i in range(64):
        if off + 4 * i + 4 <= size:
            struct.pack_into("<I", b, off + 4 * i, 0x10000000 | (k << 8) | i)
open(sys.argv[7], "wb").write(bytes(b))
