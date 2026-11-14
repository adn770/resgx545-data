# SPDX-License-Identifier: MIT
"""fold/look.py: r16-zls's post hoc reads (not frozen): what bit 20 cleared changed in the format 6
and 7 depth dumps against their kept twins, and the bend rows of zoff.

  python3 fold/look.py OUT_ATTEMPT_DIR"""
import gzip
import os
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import z16 as Z  # noqa: E402


def rd(p):
    return gzip.decompress(open(p + ".gz", "rb").read())


def main(att):
    for n in ("zb4-20-f6", "zb4-20-f7"):
        got = Z.dwords(rd(os.path.join(att, "zbits4", n + ".depth.1.bin")))
        tw = Z.dwords(Z.kept(Z.ZB4_TWIN[n] + ".dep"))
        diff = [i for i in range(len(tw)) if got[i] != tw[i]]
        print(f"{n} vs {Z.ZB4_TWIN[n]}: {len(diff)} dwords differ; changed from the fill: row "
              f"{sum(v != Z.FILL_DEAD for v in got)}, twin {sum(v != Z.FILL_DEAD for v in tw)}")
        blocks = sorted({i // 512 for i in diff})
        print(f"  blocks {blocks}; per block {[sum(1 for i in diff if i // 512 == b) for b in blocks]}")
        for i in diff[:12]:
            print(f"  dword {i} (block {i // 512}, +{i % 512}): {tw[i]:#010x} -> {got[i]:#010x}")
        # the row's own form: does each block equal block 0, and which offsets carry values
        offs = sorted({i % 512 for i, v in enumerate(got[:2048]) if v != Z.FILL_DEAD})
        print(f"  row's written offsets in a block: {len(offs)}: {offs[:8]} ... {offs[-4:]}")
        same = all(got[512 * b:512 * b + 512] == got[:512] for b in range(4))
        print(f"  the four blocks alike: {same}")


if __name__ == "__main__":
    main(sys.argv[1])


def packed(att):
    """post hoc: bit 20 cleared moves the format 6 and 7 stores to dword 2048 on, the twin's
    per-tile records packed one after another"""
    for n in ("zb4-20-f6", "zb4-20-f7"):
        got = Z.dwords(rd(os.path.join(att, "zbits4", n + ".depth.1.bin")))
        tw = Z.dwords(Z.kept(Z.ZB4_TWIN[n] + ".dep"))
        recs = [tw[512 * b:512 * b + 512] for b in range(4)]
        recs = [[v for v in r if v != Z.FILL_DEAD] for r in recs]
        cat = [v for r in recs for v in r]
        idx = [i for i, v in enumerate(got) if v != Z.FILL_DEAD]
        print(f"{n}: written dwords {idx[0]}..{idx[-1]} ({len(idx)}, contiguous "
              f"{idx == list(range(idx[0], idx[0] + len(idx)))}); the twin's tile records "
              f"{[len(r) for r in recs]} packed in tile order equal them: "
              f"{[got[i] for i in idx] == cat}")
        tws = [i for i, v in enumerate(tw) if v != Z.FILL_DEAD]
        print(f"  twin offsets in block 0: {[i for i in tws if i < 512][:6]} ...")


if __name__ == "__main__" and len(sys.argv) > 2:
    packed(sys.argv[1])
