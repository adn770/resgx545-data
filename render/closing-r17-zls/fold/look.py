# SPDX-License-Identifier: MIT
"""fold/look.py: r17-zls's post hoc reads (not frozen): what the failed rows read.
  zb20-b-6-96: the 396 dwords it wrote against the twin's 352 (the twin's tile 7 holds no record).
  zo2-s-65: the 363 stencil bytes beyond the extent that H-OVL-PASS-EDGE got wrong.

  python3 fold/look.py OUT_ATTEMPT_DIR"""
import gzip
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import z17 as Z  # noqa: E402


def rd(att, stage, n, suf):
    return gzip.decompress(open(os.path.join(att, stage, n + suf + ".gz"), "rb").read())


def zb20(att):
    tw = Z.dwords(rd(att, "zb20", "zb20-t-6-96", ".depth.1.bin"))
    row = Z.dwords(rd(att, "zb20", "zb20-b-6-96", ".depth.1.bin"))
    recs = Z.records(tw, 9)
    print("twin records per slot", [len(r) for r in recs])
    idx = [i for i, v in enumerate(row) if v != Z.FILL_DEAD]
    print("row written", len(idx), idx[0], idx[-1])
    # split the row's run into 44-dword records and match each to the twin's records
    run = [row[i] for i in idx]
    chunks = [run[44 * k:44 * k + 44] for k in range(len(run) // 44)]
    for k, c in enumerate(chunks):
        m = [s for s, r in enumerate(recs) if r == c]
        print(f"  packed record {k} (dwords {2048 + 44 * k}): twin slot {m}")
    cat = [v for r in recs for v in r]
    print("twin concat equals the run minus the extra record at k=7:",
          run[:44 * 7] + run[44 * 8:] == cat, "; run[:308] == twin[:308]:", run[:308] == cat[:308])
    print("record 7 values vs record 6:", chunks[7] == chunks[6], "vs record 8:", chunks[7] == chunks[8])
    print("record 7 first values", [hex(v) for v in chunks[7][:6]])
    print("twin slot 7 non-fill", sum(v != Z.FILL_DEAD for v in tw[512 * 7:512 * 8]),
          "twin blocks beyond slot 8", sum(v != Z.FILL_DEAD for v in tw[512 * 9:]))
    # the twin's other tiles of the 96 x 48 target: the tile (1, 2) of 3 x 3
    print("tile (c=1, r=2) is slot", 2 * 3 + 1)


def zos65(att):
    st = rd(att, "zovs2", "zo2-s-65", ".stencil-store.1.bin")
    w, h, g = Z.OVS_ROWS["zo2-s-65"]
    own = Z.owners(w, h, g)
    tw, th = Z.tiles(w, h)
    pred, _ = Z.ovs_predict(w, h, g, "H-OVL-PASS-EDGE")
    pc, _ = Z.ovs_predict(w, h, g, "H-EDGE-CLIP")
    bad = [p for p, v in pred.items() if st[p] != v]
    print("zo2-s-65: bytes off PASS-EDGE", len(bad))
    by_tile = {}
    for y in range(th * 16):
        for x in range(tw * 32):
            if x < w and y < h:
                continue
            p = Z.st_pos(x, y, g)
            t = (x >> 5, y >> 4)
            if own[(y >> 4) * (g + 1) + (x >> 5)] != t:
                continue
            ld = Z.fill_byte("bytes", p)
            rdv = st[p]
            kind = ("inverted" if rdv == ld ^ 0xFF else "loaded" if rdv == ld else
                    "dead" if rdv == (Z.FILL_DEAD >> (8 * (p % 4)) & 0xFF) else "other")
            by_tile.setdefault(t, {}).setdefault(kind, []).append((x, y, ld & 1, pred[p] == st[p]))
    for t, d in sorted(by_tile.items()):
        print(" owner tile", t, {k: len(v) for k, v in d.items()})
        for k, v in d.items():
            # beyond-extent bytes: does the byte follow 'tested' (passes when bit 0 of the load is 0)
            ok = sum(1 for x, y, b0, hit in v if (k == "inverted") == (b0 == 0))
            print("   ", k, len(v), "of them consistent with the test (bit 0 of the load 0 <=> inverted):", ok,
                  "rows x range", sorted({y for x, y, _, _ in v})[:3], sorted({x for x, y, _, _ in v})[:3])


if __name__ == "__main__":
    zb20(sys.argv[1])
    zos65(sys.argv[1])


def band(x, y, w, h):
    """sgx-pipe zls::in_band (E831): x + 0.5 < 1.25 W and y + 0.5 < 1.25 H"""
    return x * 4 + 2 < w * 5 and y * 4 + 2 < h * 5


def stencil_band(att):
    """post hoc: H-OVL-PASS-EDGE with the pixels beyond E831's band keeping their load"""
    for n in ("zo2-s-65", "zo2-s-63"):
        w, h, g = Z.OVS_ROWS[n]
        st = rd(att, "zovs2", n, ".stencil-store.1.bin")
        own = Z.owners(w, h, g)
        tw, th = Z.tiles(w, h)
        hit = tot = 0
        for ty in range(th):
            for tx in range(tw):
                if own[ty * (g + 1) + tx] != (tx, ty):
                    continue
                for yy in range(16):
                    for xx in range(32):
                        x, y = 32 * tx + xx, 16 * ty + yy
                        p = Z.st_pos(x, y, g)
                        ld = Z.fill_byte("bytes", p)
                        tested = (x < w and y < h) or band(x, y, w, h)
                        e = ld ^ 0xFF if tested and ld & 1 == 0 else ld
                        hit += st[p] == e
                        tot += 1
        print(f"{n}: H-OVL-PASS-EDGE with the pixels beyond the band (x + 0.5 < 1.25 W, y + 0.5 < 1.25 H) "
              f"keeping their load: {hit}/{tot} bytes")


def zb20_all(att):
    """post hoc: the twin's records are every non-fill dword of the twin in address order"""
    for fmt, w, h, g in sorted({(v[0], v[1], v[2], v[3]) for v in Z.ZB20_ROWS.values()}):
        n = f"zb20-b-{fmt}-{w}"
        tn = f"zb20-t-{fmt}-{w}"
        tw = Z.dwords(rd(att, "zb20", tn, ".depth.1.bin"))
        row = Z.dwords(rd(att, "zb20", n, ".depth.1.bin"))
        cat = [v for v in tw if v != Z.FILL_DEAD]
        idx = [i for i, v in enumerate(row) if v != Z.FILL_DEAD]
        slots = sorted({i // 512 for i, v in enumerate(tw) if v != Z.FILL_DEAD})
        print(f"{n}: twin's non-fill dwords {len(cat)} in slots {slots}; row's run {idx[0]}..{idx[-1]} "
              f"({len(idx)}), equal to the twin's dwords in address order from 2048: "
              f"{[row[i] for i in idx] == cat and idx[0] == 2048}")


if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[2] == "post":
    stencil_band(sys.argv[1])
    zb20_all(sys.argv[1])
