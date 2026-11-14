#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py: r16-tex's generator (r15-tex's, the ty stage only). Writes tables/ty.txt,
predictions/ty.tsv, the per-pixel predictions predictions/ty/NAME.MODEL.txt (one token a pixel,
raster order; score/score.py says how each token is compared) and the programs bins/NAME.bin (+ .s
for the generated ones; the control's is the published bin), every input read at the commits
session.toml's [freeze] names (gen/pins.py).

  python3 gen/make.py          write everything
  python3 gen/make.py --check  exit 1 when a written file differs from what it would write now
Inputs: RESGX545_DATA (default /Users/jtorra/src/resgx545-data), RESGX545_MAIN (default
/Users/jtorra/src/resgx545, for tools/usse-asm/usse-asm)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import pins  # noqa: E402
import scorekit  # noqa: E402
import tex  # noqa: E402
import ty as TY  # noqa: E402

HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"
ORDER = ("ty",)
TOOL = "t10"
HEADERS = {
    "ty": """# r16-tex ty, Q177 (rank-round16.md section 2, R16-7 a): texture types 1, 3, 4 (E567's programs) at 8 x 8, 64 x 64 and
# 64 x 16, each mode 4 row right after its mode 0 reference; type 1 modes 5 at 8 x 8 and 64 x 64, 6 and 7 at 64 x 64; 32 pages,
# base 0. Frozen (gen/ty.py): E1055's fit N13 = 39 W + 52 + (x mod W) (types 1 and 3), N4 = 40 W + 20 + (x mod W), halved names,
# against NQ13 / NQ4 (c0 + k W^2) and, at 64 x 16, N13-H; modes 6 and 7: L13 (the last column) against LQ13 and H-AS-U4; the
# references R-W (types 1, 3), R-32 (type 4) against the other strides. Control that can fail: E1055's ty-ty1u4r rerun (kept
# image). Stop: any fault or hang; the second row without its pixel rows.""",
}


def line(*f):
    return "\t".join(str(x) for x in f) + "\n"


def body(tokens):
    return "".join(t + "\n" for t in tokens)


def put(files, pred, stage, name, model, st, tokens, src):
    b = body(tokens)
    files[f"predictions/{stage}/{name}.{model}.txt"] = b.encode()
    pred.append(line(name, "pixels", "sha256:" + pins.sha(b), model, st, src))


def probe_row(name, st, pages=None):
    knobs = "reads:pixels" if st == "control" else "-"
    pg = f" --scratch-pages {pages}" if pages and pages != 16 else ""
    return f'{name}|{st}|safe|{knobs}|{TOOL}|{tex.PROBE}{pg} "$S/bins/{name}.bin"'


def spec_prog(files, name, text):
    files[f"bins/{name}.s"] = text.encode()
    files[f"bins/{name}.bin"] = tex.assemble(text)


def ty(files):
    rows, pred = [], [HEAD]
    for name, st, sp, binpin, pix, other, src in TY.jobs():
        if binpin:
            files[f"bins/{name}.bin"] = pins.blob(binpin)
        else:
            spec_prog(files, name, tex.text(sp))
        rows.append(probe_row(name, st, TY.PAGES))
        for m, toks in pix.items():
            put(files, pred, "ty", name, m, st, toks, src)
        for m, (q, v) in other.items():
            pred.append(line(name, q, v, m, st, src))
    return rows, pred


def build():
    files, tables = {}, {}
    tables["ty"] = ty(files)
    import score as SC
    for stage in ORDER:
        rows, pred = tables[stage]
        files[f"tables/{stage}.txt"] = (f"#stage {stage}\n#limit 0\n{HEADERS[stage]}\n"
                                        + "\n".join(rows) + "\n").encode()
        files[f"predictions/{stage}.tsv"] = "".join(pred).encode()
        controls = {}
        for r in rows:
            name, st, _, knobs, tool, args = r.split("|", 5)
            if st == "control":
                reads = [w[6:].split(",") for w in knobs.split() if w.startswith("reads:")]
                controls[name] = (tuple(reads[0]) if reads else (),
                                  dict(name=name, args=args, stage=stage))
        scorekit.refuse_unreadable(controls, SC.producible)
    return files


def main(argv):
    files = build()
    check = "--check" in argv
    bad = []
    for rel, b in sorted(files.items()):
        p = os.path.join(KP, rel)
        if check:
            if not os.path.exists(p) or open(p, "rb").read() != b:
                bad.append(rel)
            continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b)
    if check:
        for d in ("bins", "tables") + tuple(f"predictions/{s}" for s in ORDER):
            full = os.path.join(KP, d)
            for n in sorted(os.listdir(full)) if os.path.isdir(full) else []:
                if f"{d}/{n}" not in files:
                    bad.append(f"{d}/{n} (not written by the generator)")
        print("\n".join(f"differs: {b}" for b in bad) or f"generator current: {len(files)} files")
        return 1 if bad else 0
    print(f"wrote {len(files)} files; pins read: {', '.join(sorted(pins.READ))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
