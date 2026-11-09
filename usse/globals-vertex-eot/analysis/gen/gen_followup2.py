#!/usr/bin/env python3
"""Follow-up 2 (declared after follow-up 1, before it runs): the offset of o2 and o3 against PDS_SIZE, on new
target shapes, with --dump-render. Markers 201..."""
import pathlib, subprocess
P = pathlib.Path(__file__).resolve().parent.parent
ASM = pathlib.Path.home() / "src/resgx545/tools/usse-asm"
CFG = [("w96-s0", 96, 96, 0), ("w96-s1", 96, 96, 1), ("w96-s2", 96, 96, 2), ("w96-s3", 96, 96, 3),
       ("w192x96-s0", 192, 96, 0), ("w192x96-s3", 192, 96, 3), ("w64x96-s2", 64, 96, 2), ("w64x96-s3", 64, 96, 3)]
pds = 12
out, decl, preds = [], [], ["case\tquantity\tvalue\tmodel"]
m = 200
for tag, W, H, S in CFG:
    for ax in "xy":
        m += 1
        pa = "pa0" if ax == "x" else "pa1"
        ops = "\n".join(f"or.skipinv{'.end' if k == 8 else ''} o{k-1}, {pa}, #0x{m*16+k:x}" for k in range(1, 9))
        r = subprocess.run([str(ASM / "usse-asm"), "-o", str(P / f"stage-bins/o23e-m{m}.bin"), "-"],
                           input="phas #0, #0, pixel, end, parallel\n" + ops + "\n", capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        name = f"o23e-{tag}-{ax}"
        a = (f"probe --tri pixel --temps 32 --pixels --dump-render \"$W/dump\" --width {W} --height {H} --vtx-coords 2 "
             f"--blk 4=0x{(S << 16) | 1:08x} --slot pixpds=$S/pds_iter_xy.bin:{pds} --slot vtxuse=$S/vtx_coords.bin $S/o23e-m{m}.bin")
        out.append(f"{name}|heldout|{W}|{H}|{a}|{m}|{ax}")
        decl.append((name, "o23-size", "heldout", f"{W}x{H}"))
        preds.append(f"{name}\to2-dominant-offset\t{1 if S == 3 else 2}\tH23-S")
        preds.append(f"{name}\to3-dominant-offset\t{ {0: 2, 1: 2, 2: '?', 3: 1}[S] }\tH23-S")
        preds.append(f"{name}\to1-dominant-offset\t1\tH23-S")
(P / "gen/table-o23-size.txt").write_text("\n".join(out) + "\n")
(P / "gen/o23e-markers.tsv").write_text("".join(f"{l.split('|')[0]}\t{l.split('|')[5]}\n" for l in out))
(P / "declared-followup2.tsv").write_text("case\tscript\tset\tsize\n" + "".join("\t".join(r) + "\n" for r in decl))
(P / "predictions-followup2.tsv").write_text("\n".join(preds) + "\n")
print(len(out))
