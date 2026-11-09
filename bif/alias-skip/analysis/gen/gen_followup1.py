#!/usr/bin/env python3
"""Follow-up 1 (declared after the first o23-tiles run, before it runs): the same 13 configs, x and y, with
--dump-render, so that the region order of the TA data can be read; programs with new markers 101..126."""
import pathlib, subprocess, math, sys
P = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(P / "gen"))
ASM = pathlib.Path.home() / "src/resgx545/tools/usse-asm"
O23 = [l.split("|") for l in (P / "gen/table-o23-tiles.txt").read_text().splitlines()]
out, preds, decl = [], [], []
m = 100
for l in O23:
    name, sset, w, h, args, _m, ax = l
    m += 1
    pa = "pa0" if ax == "x" else "pa1"
    ops = "\n".join(f"or.skipinv{'.end' if k == 8 else ''} o{k-1}, {pa}, #0x{m*16+k:x}" for k in range(1, 9))
    r = subprocess.run([str(ASM / "usse-asm"), "-o", str(P / f"stage-bins/o23d-m{m}.bin"), "-"],
                       input="phas #0, #0, pixel, end, parallel\n" + ops + "\n", capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    a = args.replace(f"o23-m{_m}.bin", f"o23d-m{m}.bin").replace("--width", "--dump-render \"$W/dump\" --width", 1)
    nn = name.replace("o23-", "o23d-", 1)
    out.append(f"{nn}|{'explore' if sset in ('fit', 'control') else 'heldout'}|{w}|{h}|{a}|{m}|{ax}")
    decl.append((nn, "o23-order", "heldout" if sset != "explore" else "explore", f"{w}x{h}"))
(P / "gen/table-o23-order.txt").write_text("\n".join(out) + "\n")
(P / "gen/o23d-markers.tsv").write_text("".join(f"{l.split('|')[0]}\t{l.split('|')[5]}\n" for l in out))
with open(P / "declared-followup1.tsv", "w") as f:
    f.write("case\tscript\tset\tsize\n" + "".join("\t".join(r) + "\n" for r in decl))
print(len(out))
