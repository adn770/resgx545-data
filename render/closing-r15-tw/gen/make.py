#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py [--check]: r15-tw's table, predictions and programs from gen/tw.py. Writes
tables/tw14.txt, predictions/tw14.tsv, predictions/tw14/NAME.MODEL.txt (an image's 2048 tokens,
raster order: `XXXXXXXX` exact, `h:XXXX` the low 16 bits, `t:B0,B1,B2,B3` each byte within 1) and
bins/*.bin; --check writes nothing and fails on any file that differs (the generator is current).
Every repository file read is read at session.toml's frozen commits (gen/pins.py); the assembler
is resgx545's usse-asm (tools/usse-asm/usse-asm of the main checkout, /Users/jtorra/src/resgx545).
tw-zero's program is E1047's published f1-zero.bin, copied byte for byte."""
import hashlib
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pins  # noqa: E402
import tex  # noqa: E402
import tw  # noqa: E402

KP = os.path.dirname(HERE)
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
SRC = {
    "REF": "E561 tile law, bit clear (E1026: texels in u16)",
    "H-E1047": "E1047 f1-zero kept image (byte-for-byte rerun)",
    "H-TWP": "E1047 H-TWP4128 read as pitch W + 4096, frac(u) [infer: fitted at W 32]",
    "H-TWP4128": "E1047 H-TWP4128 read as a constant 4128-texel tile row",
    "H-CLAMP1": "u clamped to [0, 1] (E1003's strided clamp; refuted at W 32 by E1047 f1-tw32)",
    "H-WRAPW": "move = floor(128 W u) mod 4096, the texel coordinate's 12 bits [infer]",
    "H-TWP4096": "E1047's refuted 4096-texel tile row (negative)",
    "U16-TX": "H-TWP in u16 texels, 16 x 16 texel tiles (E1026, E1003)",
    "U16-T32": "tiles of 16 x 16 dwords, two texels a dword (rival)",
    "U16-DW": "move and widening in dwords (rival; E1003 measured texels)",
    "H-FOOT-TW": "every tap the bit-14 address of its wrapped texel (E1027 H-FOOT)",
    "H-FOOT-SHIFT": "the second column unwrapped in the wide layout (rival)",
    "H-POINT": "the filter dropped: H-TWP's point image (rival)",
}
TABLE_HEAD = [
    "#stage tw14", "#limit 0",
    "# r15-tw tw14, Q078 T3 bit 14 on twiddled W x 32 textures at W 16, 64, 128 (u past 1), a u16 "
    "32 x 32 and two bilinear rows (rank-round15.md section 2 r15-tw; SAFE CLASS, R15-2 a). "
    "gen/tw.py. t14: probe --scratch-pages 256 (1 MiB = dwords 0 to 262143).",
    "# Rows in ascending reach (the farthest dword of every frozen model, gen/tw.py reach(); the "
    "largest 134143, tests/test_gen.py): the four bit-clear references and tw-zero (E1047's "
    "f1-zero rerun) first, the controls every held-out row is gated by.",
    "# #limit 0, no expectfault: any fault or hang stops the stage (4); session.toml's on_stop = end "
    "ends the session on a hook stop (24): an ok row without its 32 pixel rows or its 1024 KiB "
    "scratch line.",
]


def digest(tokens):
    return hashlib.sha256(" ".join(tokens).encode()).hexdigest()


def stage(files):
    rows, preds = [], []
    for name, sset, knobs, sp, models in tw.jobs():
        files[f"bins/{name}.bin"] = pins.blob(tw.ZERO_BIN) if sp is None else \
            tex.assemble(tex.text(sp))
        rows.append(f"{name}|{sset}|safe|{knobs}|t14|{tw.args(name)}")
        for m, toks in models.items():
            files[f"predictions/tw14/{name}.{m}.txt"] = (" ".join(toks) + "\n").encode()
            preds.append((name, "end", "ok", m, sset, SRC[m]))
            preds.append((name, "image", digest(toks), m, sset, SRC[m]))
    return TABLE_HEAD + rows, preds


def readable(table):
    """scorekit.refuse_unreadable on the stage's controls: each reads a key its row produces."""
    sys.path.insert(0, os.path.join(KP, "kit"))
    sys.path.insert(0, os.path.join(KP, "score"))
    import score
    import scorekit
    ctl = {}
    for ln in table:
        if ln.startswith("#"):
            continue
        name, sset, risk, knobs, tool, args = ln.split("|", 5)
        if sset == "control":
            reads = next((w[6:].split(",") for w in knobs.split() if w.startswith("reads:")), [])
            ctl[name] = (tuple(reads), dict(name=name, args=args))
    scorekit.refuse_unreadable(ctl, score.producible)


def build():
    files = {}
    table, preds = stage(files)
    readable(table)
    files["tables/tw14.txt"] = ("\n".join(table) + "\n").encode()
    files["predictions/tw14.tsv"] = (HEAD + "".join("\t".join(r) + "\n" for r in preds)).encode()
    return files


def main(argv):
    files = build()
    check = "--check" in argv
    bad = []
    for rel, data in sorted(files.items()):
        p = os.path.join(KP, rel)
        old = open(p, "rb").read() if os.path.exists(p) else None
        if old == data:
            continue
        if check:
            bad.append(rel)
        else:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(data)
    for d in ("predictions/tw14", "bins", "tables", "predictions"):
        full = os.path.join(KP, d)
        for f in sorted(os.listdir(full)) if os.path.isdir(full) else []:
            if os.path.isfile(os.path.join(full, f)) and f"{d}/{f}" not in files:
                bad.append(f"{d}/{f} (not the generator's)")
    if bad:
        print("not current:" if check else "left over:", ", ".join(bad))
        return 1
    print("current" if check else f"written: {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
