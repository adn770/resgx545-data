import gzip, importlib.util, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("q071_rule", os.path.join(HERE, "q071_rule.py"))
R = importlib.util.module_from_spec(spec); sys.dont_write_bytecode = True; spec.loader.exec_module(R)
D = "/Users/jtorra/src/resgx545-data/render/closing-r10-st1/out/20261113-103934/st1/"
def rd(n):
    return gzip.open(D + n + ".gz").read()
res = {}
for row in ("st1-b0", "st1-lane1", "q071-b0", "q071-l1"):
    fit = row.startswith("st1")
    txt = rd(row + ".txt").decode()
    img = R.pixels_drawn(txt, R.W, R.H)
    sst, ld = rd(row + ".stencil-store.1.bin"), rd(row + ".stencil.1.bin")
    fill = R.FILLS[row][0]
    ldok = all(ld[o] == R.fill_byte(fill, o) for o in range(R.BUF)) and len(ld) == R.BUF
    print(f"ROW {row} ({'control, E988 base' if fit else 'HELD-OUT'}): drawn {len(img)}, "
          f"store len {len(sst)}, loaded == fill pattern: {ldok}, "
          f"store first 2048 all 0xff: {all(b == 0xff for b in sst[:2048])}, "
          f"store past 2048 all deadbeef: {sst[2048:] == bytes((0xEF,0xBE,0xAD,0xDE)[o&3] for o in range(2048, R.BUF))}")
    for m in R.MODELS:
        pd, ps = R.predict(row, m)
        extra, miss = len(img - pd), len(pd - img)
        right = len(img & pd) + (R.W * R.H - len(img | pd))   # pixels agreeing
        sok = sum(1 for a, b in zip(sst, ps) if a == b)
        ok = img == pd and sst == ps
        res.setdefault(m, {})[row] = ok
        print(f"   {m:12s} pixels agree {right}/2048 (extra {extra}, missing {miss}); "
              f"store bytes agree {sok}/{R.BUF}; {'PASS' if ok else 'FAIL'}")
print()
for m in R.MODELS:
    h = [res[m][r] for r in ("q071-b0", "q071-l1")]
    c = [res[m][r] for r in ("st1-b0", "st1-lane1")]
    print(f"VERDICT {m}: held-out {sum(h)} held / {2-sum(h)} failed of 2; controls {sum(c)} of 2 held")
