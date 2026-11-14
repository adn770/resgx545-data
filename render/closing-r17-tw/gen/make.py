#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py [--check]: r17-tw's table, predictions and programs from gen/tw17.py. Writes
tables/tw17.txt, predictions/tw17.tsv, predictions/tw17/NAME.MODEL.txt (an image's 2048 tokens,
raster order: `XXXXXXXX` exact, `t:B0,B1,B2,B3` each byte within 1), and bins/*.bin; --check writes nothing and fails on any
file that differs (the generator is current). Every repository file read is read at
session.toml's frozen commits (gen/pins.py); the assembler is resgx545's usse-asm
(tools/usse-asm/usse-asm of the main checkout, /Users/jtorra/src/resgx545). bl64leftr's program is
E1058's published bl64left.bin, copied byte for byte (tests: the spec rebuilds it)."""
import hashlib
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pins  # noqa: E402
import tex  # noqa: E402
import tw17  # noqa: E402

KP = os.path.dirname(HERE)
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
SRC = {
    "REF": "E561 tile law, bit clear (16 x min(H, 16) tiles, a new width)",
    "H-E1058": "E1058 bl64left kept image (byte-for-byte rerun, each byte within 1)",
    "H-WIDE": "sample over W + 4096 texels at frac u, columns mod W' (post hoc E1049+E1058, gen/derive.py)",
    "H-WIDE-G": "H-WIDE with column -1 at W - 1 (rival; exact bytes only, LEFT-WRAP rule)",
    "H-WIDE-NEXT": "H-WIDE with column W' unwrapped, the next tile row (rival)",
    "UNWRAP-G": "columns X + m, X + 1 + m, weights from W frac u, -1 at W - 1 (E1058 post hoc, rival)",
    "F-FRAC": "columns X mod W + m, X + 1 + m (E1049 post hoc, refuted by E1058, carried)",
    "H-POINT": "the filter dropped: H-WIDE-PT's point image (rival)",
    "H-WIDE-PT": "point: column floor((W + 4096) frac u) of the wide layout",
    "H-TWP": "point: column floor(W frac u) + floor(4096 frac u) (E1049/E1058 H-TWP-H, rival off grid)",
}
LEFT_RULE = {"H-WIDE": ">=0.9", "H-WIDE-G": "<=0.1"}
TABLE_HEAD = [
    "#stage tw17", "#limit 0",
    "# r17-tw tw17, Q078 T3 bit 14 under a bilinear sample at a twiddled texture's left and right "
    "edges, on and off the 1/4096 grid, and off-grid point reads (rank-round17.md section 2 r17-tw; "
    "SAFE CLASS, R17-1..4 a). gen/tw17.py. t14: probe --scratch-pages 256 (1 MiB = dwords 0 to "
    "262143).",
    "# Rows in the plan's order: E1058's bl64left rerun, the W <= 128 rows, then the bit-clear "
    "references of the new widths before their rows, the widths 256, 512 and 2048 last. Every "
    "frozen form's farthest dword is below 150000 (tests/test_gen.py). A reference prints its "
    "sentinel dword (run/hooks.sh) or hook_check stops the stage before its width's rows.",
    "# #limit 0, no expectfault: any fault or hang stops the stage (4); session.toml's on_stop = end "
    "ends the session on a hook stop (24): an ok row without its 32 pixel rows, its 1024 KiB "
    "scratch line or (references) its sentinel.",
]


def digest(tokens):
    return hashlib.sha256(" ".join(tokens).encode()).hexdigest()


def stage(files):
    rows, preds = [], []
    for name, sset, knobs, sp, models in tw17.jobs():
        files[f"bins/{name}.bin"] = pins.blob(tw17.BL64L_BIN) if name == tw17.CTL_REP else \
            tex.assemble(tex.text(sp))
        rows.append(f"{name}|{sset}|safe|{knobs}|t14|{tw17.args(name)}")
        for m, toks in models.items():
            files[f"predictions/tw17/{name}.{m}.txt"] = (" ".join(toks) + "\n").encode()
            preds.append((name, "end", "ok", m, sset, SRC[m]))
            preds.append((name, "image", digest(toks), m, sset, SRC[m]))
            if m in LEFT_RULE:
                n = sum(a != b for a, b in zip(models["H-WIDE"], models["H-WIDE-G"]))
                preds.append((name, "leftwrap", f"exact{LEFT_RULE[m]} of {n}", m, sset,
                              "LEFT-WRAP rule (R17-3 a): exact bytes at the pixels the two part"))
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
    files["tables/tw17.txt"] = ("\n".join(table) + "\n").encode()
    files["predictions/tw17.tsv"] = (HEAD + "".join("\t".join(r) + "\n" for r in preds)).encode()
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
    for d in ("predictions/tw17", "bins", "tables", "predictions"):
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
