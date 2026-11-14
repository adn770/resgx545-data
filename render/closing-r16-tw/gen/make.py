#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py [--check]: r16-tw's table, predictions and programs from gen/tw16.py. Writes
tables/tw16.txt, predictions/tw16.tsv, predictions/tw16/NAME.MODEL.txt (an image's 2048 tokens,
raster order: `XXXXXXXX` exact, `t:B0,B1,B2,B3` each byte within 1), and bins/*.bin; --check writes nothing and fails on any
file that differs (the generator is current). Every repository file read is read at
session.toml's frozen commits (gen/pins.py); the assembler is resgx545's usse-asm
(tools/usse-asm/usse-asm of the main checkout, /Users/jtorra/src/resgx545). bl32r's program is
E1049's published tw-bl32.bin, copied byte for byte (tests: the spec rebuilds it)."""
import hashlib
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pins  # noqa: E402
import tex  # noqa: E402
import tw16  # noqa: E402

KP = os.path.dirname(HERE)
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
SRC = {
    "REF": "E561 tile law, bit clear (tiles min(W, 16) x min(H, 16))",
    "H-E1049": "E1049 tw-bl32 kept image (byte-for-byte rerun, each byte within 1)",
    "H-TWP-H": "E1049 H-TWP with E561's tile height, tile rows t div 16 [infer: fitted at H 32]",
    "H-TWP-T16": "the wide layout keeps 16 x 16 tiles at H 8 (rival)",
    "H-MOVEH": "move floor(128 H frac u), tile row W + 128 H (rival) [infer]",
    "H-TWP-V32": "the wide layout spans 32 texel rows: t mod 32 (rival)",
    "H-TWP-STRIP": "the 4096 added once: one 4096 x H strip after the texture (refuted at H 32)",
    "H-TWP4128": "a constant 4128-texel tile row (refuted at H 32 by E1049)",
    "F-FRAC": "taps X mod W + m, X + 1 + m, X = floor(W frac u - 1/2), rows wrapped (E1049 post hoc)",
    "F-VNEXT": "F-FRAC with the second row H: the next tile row of the wide layout (rival)",
    "H-FOOT-SHIFT": "taps x0 mod W + m, x0 mod W + 1 + m (E1049 rival, 1 of 2)",
    "H-FOOT-TW": "taps at their wrapped columns + m; = the plan's F-WRAP2 (E1049 rival, 0 of 2)",
    "H-POINT": "the filter dropped: H-TWP-H's point image (rival)",
}
TABLE_HEAD = [
    "#stage tw16", "#limit 0",
    "# r16-tw tw16, Q078 T3 bit 14 on twiddled textures: E1049's post hoc bilinear form held out "
    "(inside, left edge, right edge, v edge, H 16) and point reads at H 8, 16 and 64 "
    "(rank-round16.md section 2 r16-tw; SAFE CLASS, R16-2 a). gen/tw16.py. t14: probe "
    "--scratch-pages 256 (1 MiB = dwords 0 to 262143).",
    "# Rows in ascending reach (the farthest dword of every frozen model, gen/tw16.py reach(); the "
    "largest 224351, tests/test_gen.py); the H 64 rows last. The H 16 rows print their sentinel "
    "dword (run/hooks.sh, tests) or hook_check stops the stage before any farther row.",
    "# #limit 0, no expectfault: any fault or hang stops the stage (4); session.toml's on_stop = end "
    "ends the session on a hook stop (24): an ok row without its 32 pixel rows, its 1024 KiB "
    "scratch line or (H 16 rows) its sentinel.",
]


def digest(tokens):
    return hashlib.sha256(" ".join(tokens).encode()).hexdigest()


def stage(files):
    rows, preds = [], []
    for name, sset, knobs, sp, models in tw16.jobs():
        files[f"bins/{name}.bin"] = pins.blob(tw16.BL32_BIN) if name == tw16.BL32 else \
            tex.assemble(tex.text(sp))
        rows.append(f"{name}|{sset}|safe|{knobs}|t14|{tw16.args(name)}")
        for m, toks in models.items():
            files[f"predictions/tw16/{name}.{m}.txt"] = (" ".join(toks) + "\n").encode()
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
    files["tables/tw16.txt"] = ("\n".join(table) + "\n").encode()
    files["predictions/tw16.tsv"] = (HEAD + "".join("\t".join(r) + "\n" for r in preds)).encode()
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
    for d in ("predictions/tw16", "bins", "tables", "predictions"):
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
