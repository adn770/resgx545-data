#!/usr/bin/env python3
"""Follow-up 3 (declared after the q053-eot, eotcap and eotst runs, before it runs): one global register a job in the
end-of-tile task. eotst showed a store (stad of r2 or g43) lands in the scratch and the job then faults (3 of 3
with a store, 0 of 5 without). One register per job, the address (scratch + 16 * job number) the marker."""
import pathlib, subprocess
P = pathlib.Path(__file__).resolve().parent.parent
ASM = pathlib.Path.home() / "src/resgx545/tools/usse-asm/usse-asm"
ALL = [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 39, 40, 41, 42, 43]
VARY = [17, 18, 21, 22, 23, 24, 25, 39]
PIX = {16: 0, 19: 0, 20: 1, 26: 0, 27: 0, 28: 0, 29: 0, 30: 0, 31: 0, 40: 0, 41: 1, 42: 0x3f800000, 43: 0xff000000}
VTX = {16: 0, 19: 0, 20: 1, 26: 0, 27: 0, 28: 0, 29: 0, 30: 0, 31: 0, 40: 0, 41: 0xf, 42: 0x3f800000, 43: 0xdf000000}
jobs = [(g, 64, 64) for g in ALL] + [(g, w, h) for g in VARY for (w, h) in ((32, 16), (128, 128))]
lines, decl, preds = [], [], ["case\tquantity\tvalue\tmodel"]
for m, (g, w, h) in enumerate(jobs, start=1):
    body = ["phas #0, #0, pixel, end, parallel"] + ["mov.skipinv r0, #0x00000000"] * 4
    body += ["emitpix1.freep #0 /* incp */, r0, r1", f"mov.skipinv r1, #0x{0x5CAF0000 + m * 16:08X}", f"stad [r1,+#0], g{g}",
             "idf drc0, bif", "wdf drc0", "emitpix2.end.freep #0 /* incp */, r2, r3, r0, #0x00000000"]
    r = subprocess.run([str(ASM), "-o", str(P / f"stage-bins/eot2-m{m}.bin"), "-"], input="\n".join(body) + "\n", capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    name = f"eot2-g{g}-{w}x{h}"
    lines.append(f"{name}|{'fit' if g == 43 and (w, h) == (64, 64) else 'heldout'}|{w}|{h}|probe --tri pixel --temps 32 --pixels --width {w} --height {h} "
                 f"--slot pixpds=$S/pds_iter_xy.bin:12 --slot vtxuse=$S/vtx_coords.bin --vtx-coords 2 --slot eot=$S/eot2-m{m}.bin $S/pix_pa0.bin|{m}|{g}|{0x100000000 if False else m * 16}")
    decl.append((name, "q053-eot2", "fit" if g == 43 and (w, h) == (64, 64) else "heldout", f"{w}x{h}"))
    if g in PIX:
        preds.append(f"{name}\tg{g}\t{PIX[g]:#x}\tH53-pix")
        preds.append(f"{name}\tg{g}\t{VTX[g]:#x}\tH53-vtx")
    else:
        preds.append(f"{name}\tg{g}\t?\tH53-pix")
(P / "gen/table-q053-eot2.txt").write_text("\n".join(lines) + "\n")
(P / "declared-followup3.tsv").write_text("case\tscript\tset\tsize\n" + "".join("\t".join(r) + "\n" for r in decl))
(P / "predictions-followup3.tsv").write_text("\n".join(preds) + "\n")
print(len(lines))
