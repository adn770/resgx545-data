#!/usr/bin/env python3
"""Follow-up 4 (declared after q053-vtx and before it runs): the vertex task's per-vertex globals against the vertices a
task holds (VDM_TASK0.MAX_VERTICES field 3 -> 4 vertices, 5 -> 6), 126 vertices, new markers. q053-vtx (V = 8) is the fit."""
import pathlib, subprocess
P = pathlib.Path(__file__).resolve().parent.parent
ASM = pathlib.Path.home() / "src/resgx545/tools/usse-asm/usse-asm"
GROUPS = {"A": [16, 17, 18, 19, 20, 21, 22, 23], "B": [24, 25, 26, 27, 28, 29, 30, 31], "C": [39, 40, 41, 42, 43, 17, 18, 19]}
FIELDS = {3: "0xc0000000", 5: "0xa0000000"}
lines, decl, preds = [], [], ["case\tquantity\tvalue\tmodel"]
mk = 10
for f, xor in FIELDS.items():
    for grp, regs in GROUPS.items():
        mk += 1
        marker = 0x3f000000 + mk
        body = ["phas #17, #0, pixel, vcull, parallel", "nop.nosched", "and.skipinv.testtanz.chan0 !r0, p0, #0x00000000, #0",
                "p0 ldad.skipinv.fetch4 pa0, [pa0,+#0], drc0", "wdf drc0", "mov.skipinv.repeat4 o0, pa0", "mov.skipinv.repeat2 o4, pa0"]
        body += [f"mov.skipinv o{6+i}, g{g}" for i, g in enumerate(regs)]
        body += [f"mov.skipinv o14, #0x{marker:08X}", "emitvcbvtx.end.twopart #0, #0", "phas #0, #0, pixel, end, parallel",
                 "emitmtevtx.end.twopart.freep #0, #0, #0"]
        r = subprocess.run([str(ASM), "-o", str(P / f"stage-bins/q053v2-m{mk}.bin"), "-"], input="\n".join(body) + "\n", capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        name = f"q053v2-f{f}-{grp}"
        a = (f"probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 11 --vdm 6^={xor} "
             f"--dump-render \"$W/dump\" --slot \"pixel=$S/pix_pa0.bin\" --slot \"vtxuse=$S/q053v2-m{mk}.bin\" \"$S/p1131-fmt-11__0.bin\"")
        lines.append(f"{name}|heldout|64|64|{a}|{mk}|{marker:#x}|{','.join(map(str, regs))}|{f + 1}")
        decl.append((name, "q053-vtx2", "heldout", "64x64"))
        for g in regs:
            if g in (17, 22, 24, 25, 39):
                preds.append(f"{name}\tg{g}-sequence\tall\tH53-Q")
                preds.append(f"{name}\tg{g}-sequence\tall\tH53-F")
(P / "gen/table-q053-vtx2.txt").write_text("\n".join(lines) + "\n")
(P / "declared-followup4.tsv").write_text("case\tscript\tset\tsize\n" + "".join("\t".join(r) + "\n" for r in decl))
(P / "predictions-followup4.tsv").write_text("\n".join(preds) + "\n")
print(len(lines))
