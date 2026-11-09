#!/usr/bin/env python3
"""Generator of the 11.34 case tables, programs and declared predictions (written before any run).
python3 gen/gen_p1134.py  -> stage-bins/*.bin, gen/table-*.txt, declared.tsv, predictions-declared.tsv"""
import pathlib, subprocess, math, sys
P = pathlib.Path(__file__).resolve().parent.parent
ASM = pathlib.Path.home() / "src/resgx545/tools/usse-asm"
OUT = P / "stage-bins"; OUT.mkdir(exist_ok=True)

def asm(text, name, isa="usse"):
    r = subprocess.run([str(ASM / ("pds-asm" if isa == "pds" else "usse-asm")), "-l", "-o", str(OUT / name), "-"],
                       input=text, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"{name}: {r.stderr}\n{text}")
    return r.stdout

# fixed helpers
for src, isa in (("pds_iter_xy.s", "pds"), ("vtx_coords.s", "usse")):
    lst = asm((P / "templates" / src).read_text(), src[:-2] + ".bin", isa)
pds_data = sum(1 for l in asm((P / "templates/pds_iter_xy.s").read_text(), "pds_iter_xy.bin", "pds").splitlines() if l.endswith("\tdata"))

declared, preds = [], []
def D(case, script, sset, size): declared.append((case, script, sset, size))
def Pr(case, q, v, model): preds.append((case, q, v, model))

# ---------------------------------------------------------------- o23-tiles (Q023)
O23 = [  # (tag, W, H, size field, set, extra)
    ("w64-s3", 64, 64, 3, "fit", ""), ("w64-s0", 64, 64, 0, "fit", ""),
    ("w128-s3", 128, 128, 3, "heldout", ""), ("w128-s0", 128, 128, 0, "heldout", ""),
    ("w128-s1", 128, 128, 1, "heldout", ""), ("w128-s2", 128, 128, 2, "heldout", ""),
    ("w96x64-s3", 96, 64, 3, "heldout", ""), ("w64x128-s3", 64, 128, 3, "heldout", ""),
    ("w160x48-s3", 160, 48, 3, "heldout", ""), ("w32x96-s3", 32, 96, 3, "heldout", ""),
    ("w256x128-s3", 256, 128, 3, "heldout", ""), ("w128-s3-rep", 128, 128, 3, "control", ""),
    ("w128-four", 128, 128, 3, "explore", "--blk 1=0x05d00200 --kpoke rd:9=1"),
]
lines = []
m = 0
for tag, W, H, S, sset, extra in O23:
    for ax in "xy":
        m += 1
        pa = "pa0" if ax == "x" else "pa1"
        ops = "\n".join(f"or.skipinv{'.end' if k == 8 else ''} o{k-1}, {pa}, #0x{m*16+k:x}" for k in range(1, 9))
        asm("phas #0, #0, pixel, end, parallel\n" + ops + "\n", f"o23-m{m}.bin")
        name = f"o23-{tag}-{ax}"
        blk4 = f"--blk 4=0x{(S << 16) | 1:08x} "
        args = (f"probe --tri pixel --temps 32 --pixels --width {W} --height {H} --vtx-coords 2 {blk4}{extra} "
                f"--slot pixpds=$S/pds_iter_xy.bin:{pds_data} --slot vtxuse=$S/vtx_coords.bin $S/o23-m{m}.bin")
        lines.append(f"{name}|{sset}|{W}|{H}|{' '.join(args.split())}|{m}|{ax}")
        D(name, "o23-tiles", sset, f"{W}x{H}")
        tw = math.ceil(W / 32)
        if sset != "explore":
            for k in (2, 3, 4):
                Pr(name, f"disp-tag{k}-tile-back", "all", "H23-T")   # src tile index = dest tile index + (k-1), raster, same in-tile place
                Pr(name, f"disp-tag{k}-tile-back", "not-all", f"H23-0")
        else:
            for k in (2, 3, 4):
                Pr(name, f"disp-tag{k}-tile-back", "?", "H23-T")
(P / "gen/table-o23-tiles.txt").write_text("\n".join(lines) + "\n")
(P / "gen/o23-markers.tsv").write_text("".join(f"{l.split('|')[0]}\t{l.split('|')[5]}\n" for l in lines))
O23_JOBS = m

# ---------------------------------------------------------------- q053-vtx (Q053, vertex task)
GROUPS = {"A": [16, 17, 18, 19, 20, 21, 22, 23], "B": [24, 25, 26, 27, 28, 29, 30, 31], "C": [39, 40, 41, 42, 43, 17, 18, 19]}
PIXEL_CONST = {16: 0, 19: 0, 20: 1, 26: 0, 27: 0, 28: 0, 29: 0, 30: 0, 31: 0, 40: 0, 41: 1, 42: 0x3f800000, 43: 0xff000000}
VARY = {17, 18, 21, 22, 23, 24, 25, 39}
vl = []
mk = 0
for rep in (1, 2):
    for grp, regs in GROUPS.items():
        mk += 1
        marker = 0x3f000000 + mk
        body = ["phas #17, #0, pixel, vcull, parallel", "nop.nosched",
                "and.skipinv.testtanz.chan0 !r0, p0, #0x00000000, #0",
                "p0 ldad.skipinv.fetch4 pa0, [pa0,+#0], drc0", "wdf drc0",
                "mov.skipinv.repeat4 o0, pa0", "mov.skipinv.repeat2 o4, pa0"]
        for i, g in enumerate(regs):
            body.append(f"mov.skipinv o{6+i}, g{g}")
        body += [f"mov.skipinv o14, #0x{marker:08X}", "emitvcbvtx.end.twopart #0, #0",
                 "phas #0, #0, pixel, end, parallel", "emitmtevtx.end.twopart.freep #0, #0, #0"]
        asm("\n".join(body) + "\n", f"q053-vtx-m{mk}.bin")
        name = f"q053-vtx-{grp}{rep}"
        args = (f"probe --tri pixpds:12 --temps 32 --width 64 --height 64 --vertices 126 --vtx-coords 11 "
                f"--vdm 6^=0x80000000 --dump-render \"$W/dump\" --slot \"pixel=$S/pix_pa0.bin\" "
                f"--slot \"vtxuse=$S/q053-vtx-m{mk}.bin\" \"$S/p1131-fmt-11__0.bin\"")
        vl.append(f"{name}|{'fit' if False else 'heldout'}|64|64|{args}|{mk}|{marker:#x}|{','.join(map(str,regs))}")
        D(name, "q053-vtx", "heldout", "64x64")
        for g in regs:
            if g in PIXEL_CONST:
                Pr(name, f"g{g}-const", f"{PIXEL_CONST[g]:#x}", "H53-same")
                Pr(name, f"g{g}-const", "0x0", "H53-zero")
            else:
                Pr(name, f"g{g}-const", "?", "H53-same")
(P / "gen/table-q053-vtx.txt").write_text("\n".join(vl) + "\n")

# ---------------------------------------------------------------- q053-eot (Q053, end-of-tile task; risky)
el = []
ALLG = [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 39, 40, 41, 42, 43]
for rep, (name, regs) in enumerate((("eot-A1", ALLG[:11]), ("eot-B1", ALLG[11:]), ("eot-A2", ALLG[:11]), ("eot-B2", ALLG[11:])), start=1):
    marker = 0x4e000000 + rep
    # second form (the first, with r8 as the address, faulted at 0x42: only r0-r3 are the EOT's): the stores sit between
    # the two emits, r1 (free after emitpix1) the address, the job's marker the scratch offset (m * 256 bytes)
    body = ["phas #0, #0, pixel, end, parallel"] + ["mov.skipinv r0, #0x00000000"] * 4
    body += ["emitpix1.freep #0 /* incp */, r0, r1", f"mov.skipinv r1, #0x{0x5CAF0000 + rep * 256:08X}"]
    for i, g in enumerate(regs):
        body.append(f"stad [r1,+#{i}], g{g}")
    body += ["idf drc0, bif", "wdf drc0", "emitpix2.end.freep #0 /* incp */, r2, r3, r0, #0x00000000"]
    asm("\n".join(body) + "\n", f"q053-eot-m{rep}.bin")
    args = (f"probe --tri pixel --temps 32 --pixels --width 64 --height 64 "
            f"--slot pixpds=$S/pds_iter_xy.bin:{pds_data} --slot vtxuse=$S/vtx_coords.bin --vtx-coords 2 "
            f"--slot eot=$S/q053-eot-m{rep}.bin $S/pix_pa0.bin")
    el.append(f"q053-{name}|explore|64|64|{args}|{rep}|{marker:#x}|{','.join(map(str,regs))}")
    D(f"q053-{name}", "q053-eot", "explore", "64x64")
    for g in regs:
        Pr(f"q053-{name}", f"g{g}-const", f"{PIXEL_CONST[g]:#x}" if g in PIXEL_CONST else "?", "H53-same")
(P / "gen/table-q053-eot.txt").write_text("\n".join(el) + "\n")


# ---------------------------------------------------------------- bif-alias (Q076)
# alias_skip masks; each case twice (-1, -2), a render pair under regtimeline on the BIF registers
B76 = [("control", 0x0, "safe"), ("id12", 1 << 12, "safe"), ("id13", 1 << 13, "safe"), ("id14", 1 << 14, "safe"),
       ("id15", 1 << 15, "safe"), ("ids6-7", 0xc0, "safe"), ("ids8-10", 0x500, "safe"), ("ids10-11", 0xc00, "safe"),
       ("ids6-7-8-10-11", 0xdc0, "safe"),
       ("id0", 1 << 0, "risky"), ("id1", 1 << 1, "risky"), ("id2", 1 << 2, "risky"), ("id3", 1 << 3, "risky"),
       ("id4", 1 << 4, "risky"), ("id5", 1 << 5, "risky")]
bl = []
for nm, mask, risk in B76:
    for r in (1, 2):
        name = f"b76-{nm}-{r}"
        bl.append(f"{name}|{'control' if nm == 'control' else 'heldout'}|{risk}|0x{mask:x}")
        D(name, "bif-alias-" + risk, "control" if nm == "control" else "heldout", "64x64")
        if nm == "control":
            Pr(name, "outcome", "exact", "H76-A"); Pr(name, "base1-is-client-pd", "equal", "H76-D")
        elif risk == "safe":
            Pr(name, "outcome", "exact", "H76-A"); Pr(name, "base1-is-client-pd", "equal", "H76-D")
        else:
            Pr(name, "outcome", "fault", "H76-A"); Pr(name, "base1-is-client-pd", "?", "H76-D")
        Pr(name, "outcome", "exact" if risk == "safe" else "fault", "H76-N")
(P / "gen/table-bif-alias.txt").write_text("\n".join(bl) + "\n")

# ---------------------------------------------------------------- dpm-bit2 (Q036/Q045): DPM timelines 0x0600-0x0750
# 4096x4096, vertices N, pb pages; 3 runs each; fit = the cases E443 ran
DP = [("v300-p100", 300, 0x100, "fit", "safe"), ("v900-p422", 900, 0x422, "fit", "safe"),
      ("v3-p422", 3, 0x422, "fit", "safe"), ("v150-p100", 150, 0x100, "heldout", "safe"),
      ("v225-p100", 225, 0x100, "heldout", "safe"), ("v300-p180", 300, 0x180, "heldout", "safe"),
      ("v300-p200", 300, 0x200, "heldout", "safe"), ("v450-p200", 450, 0x200, "heldout", "safe"),
      ("v600-p300", 600, 0x300, "heldout", "safe"), ("v600-p422", 600, 0x422, "heldout", "safe"),
      ("v450-p100", 450, 0x100, "heldout", "risky"), ("v600-p100", 600, 0x100, "heldout", "risky")]
dl = []
for nm, n, pg, sset, risk in DP:
    for r in (1, 2, 3):
        name = f"d36-{nm}-r{r}"
        dl.append(f"{name}|{sset}|{risk}|{n}|0x{pg:x}")
        D(name, "dpm-bit2-" + risk, sset, "4096x4096")
        if nm == "v300-p100":
            Pr(name, "bit2-clears", "yes", "H36-DET"); Pr(name, "hi-halves-zero", "yes", "H36-Z")
        elif nm == "v900-p422":
            Pr(name, "bit2-clears", "?", "H36-DET"); Pr(name, "hi-halves-zero", "yes", "H36-Z")
        elif nm == "v3-p422":
            Pr(name, "bit2-clears", "no", "H36-DET"); Pr(name, "hi-halves-zero", "yes", "H36-Z")
        else:
            Pr(name, "bit2-clears", "?", "H36-DET"); Pr(name, "hi-halves-zero", "yes", "H36-Z")
(P / "gen/table-dpm-bit2.txt").write_text("\n".join(dl) + "\n")

with open(P / "declared.tsv", "w") as f:
    f.write("case\tscript\tset\tsize\n" + "".join("\t".join(r) + "\n" for r in declared))
with open(P / "predictions-declared.tsv", "w") as f:
    f.write("case\tquantity\tvalue\tmodel\n" + "".join("\t".join(r) + "\n" for r in preds))
print("o23 jobs", O23_JOBS, "vtx", len(vl), "eot", len(el), "declared", len(declared), "predictions", len(preds))
