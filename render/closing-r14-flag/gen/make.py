#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py [--check]: r14-flag's tables, predictions and programs from gen/f1.py and gen/f2.py.
Writes tables/STAGE.txt, predictions/STAGE.tsv, predictions/f1/NAME.MODEL.txt (an image's 2048
tokens, raster order), predictions/f2/NAME.MODEL.slots (every target tile's header slot) and
bins/*.bin; --check writes nothing and fails on any file that differs (the generator is current).
Every repository file read is read at session.toml's frozen commits (gen/pins.py); the assembler
is resgx545's usse-asm (tools/usse-asm/usse-asm of the main checkout, /Users/jtorra/src/resgx545)."""
import hashlib
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import f1  # noqa: E402
import f2  # noqa: E402
import tex  # noqa: E402

KP = os.path.dirname(HERE)
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"


def digest(tokens):
    return hashlib.sha256(" ".join(tokens).encode()).hexdigest()


def sha(text):
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def toks(img):
    return ["%08x" % v for v in img]


def stage_f1(files):
    rows, preds = [], []
    src = {"H-E566": "E566 (tw32-ctl kept)", "H-E561": "E561 tile law (E1033 f1-ref-b)",
           "H-TWP4096": "post hoc on E1033's fault pages: s + floor(4096 fr), pitch 4096 [infer]",
           "H-TWP4128": "post hoc on E1033's fault pages: s + floor(4096 fr), pitch W + 4096 [infer]",
           "H-TWP4096-NS": "post hoc on E1033's fault pages: floor(4096 fr), pitch 4096 [infer]",
           "H-FAULTANY": "E1033 (2 of 2): bit 14 faults any twiddled read",
           "H-MOVE0": "E1003's move is 0 at u = 0: the bit-clear image"}
    for name, sset, knobs, spec, models, pages in f1.jobs():
        files[f"bins/{name}.bin"] = tex.assemble(tex.text(spec))
        rows.append(f"{name}|{sset}|{'risky' if 'expectfault' in knobs else 'safe'}|{knobs}|t14|"
                    f"{f1.args(name, pages)}")
        for m, (end, what) in models.items():
            preds.append((name, "end", end, m, sset, src[m]))
            if end == "ok":
                t = toks(what)
                files[f"predictions/f1/{name}.{m}.txt"] = (" ".join(t) + "\n").encode()
                preds.append((name, "image", digest(t), m, sset, src[m]))
    head = ["#stage f1", "#limit 3",
            "# r14-flag f1, Q078 T3 bit 14 on a twiddled 32 x 32 texture with the reach mapped "
            "(rank-round14.md section 2 F1; PLANNED FAULTS, user OK R14-5 a). gen/f1.py. t14: probe "
            "--scratch-pages 256 (1 MiB: E1033's fault pages + 0x21000 and + 0x40000 inside it).",
            "# Controls first in each pair: f1-ref-a (E566's tw32-ctl, its kept image), f1-ref-b "
            "(u = x / 4096 bit clear, the tile law's column 0). Planned: f1-tw32 (E566's "
            "tw32-t3b14), f1-small (u = x / 4096), f1-zero (u = 0, held out).",
            "# Frozen: H-TWP4096, H-TWP4128, H-TWP4096-NS (post hoc on E1033's two pages: an "
            "image each), H-FAULTANY (a fault each), H-MOVE0 (f1-zero: the bit-clear image).",
            "# #limit 3 = the three planned bit-14 rows (expectfault); the controls do not "
            "expectfault (a fault there stops the stage, 4). Strict health after every fault; "
            "hook_fault stops on a fault without its kernel BIF line, a hang, or SGX recovery "
            "failed (24), and session.toml's on_stop = end ends the session there."]
    return head + rows, preds


def stage_f2(files):
    rows, preds = [], []
    src = {"all": "the rule's words (E1007, E959 baselines)",
           "H-EVEN": "E950 (8 floor(fx / 2) slots a block row; fitted)",
           "blkrow": "R7-BLK (E907, E944: 16 floor(fx / 4))",
           "H-LASTBLOCK": "E1007 H-FLAGSLOT: the flag on the last target tile in block order",
           "H-HIGHSLOT": "E1011's rival: the flag on the highest target slot",
           "H-COVER": "post hoc on 22 kept fx 2/3 mod 4 jobs: draws iff fx covers the target [infer]",
           "H-FAULT23": "the 19 kept faults at fx 2/3 mod 4 read as fx alone"}
    for name, sset, knobs, args, q, fs in f2.jobs():
        rows.append(f"{name}|{sset}|{'risky' if 'expectfault' in knobs else 'safe'}|{knobs}|t10|"
                    f"{args}")
        for fn, body in fs.items():
            files[f"predictions/f2/{fn}"] = body.encode()
        for quantity, mv in q.items():
            for m, v in mv.items():
                preds.append((name, quantity, v, m, sset, src.get(m, "the row's size")))
        for m in f2.SLOT_MODELS:
            preds.append((name, "slots", sha(fs[f"{name}.{m}.slots"]), m, sset, src[m]))
    head = ["#stage f2", "#limit 4",
            "# r14-flag f2, Q139 H-EVEN at fx 2 or 3 mod 4 (rank-round14.md section 2 F2; PLANNED "
            "FAULTS, user OK R14-5 a). gen/f2.py. r10-geo q139c's form on t10, CR_TE_MTILE1 poked "
            "(ta:143): 256 x 256 B2 = 14, 15; 768 x 640 B1 = 26, 27 (never run).",
            "# Controls first in each size: the unpoked 256 x 256 and 768 x 640 baselines (exact, "
            "every target tile's header: the header base). t10's tri dumps nothing after a failed "
            "render, so a planned row decodes only if it draws (H-COVER).",
            "# Frozen: H-EVEN against R7-BLK (slots, wrong tiles), H-LASTBLOCK against H-HIGHSLOT "
            "(the bit-7 header's slot, the image), H-COVER (draws) against H-FAULT23 (faults).",
            "# #limit 4 = the four planned rows (expectfault expectdiff); a control's fault stops "
            "the stage (4). hook_fault stops on a fault without its kernel BIF line, a hang, or SGX "
            "recovery failed (24)."]
    return head + rows, preds


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
    for st, fn in (("f1", stage_f1), ("f2", stage_f2)):
        table, preds = fn(files)
        readable(table)
        files[f"tables/{st}.txt"] = ("\n".join(table) + "\n").encode()
        files[f"predictions/{st}.tsv"] = (HEAD + "".join("\t".join(r) + "\n" for r in preds)).encode()
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
    for d in ("predictions/f1", "predictions/f2", "bins"):
        full = os.path.join(KP, d)
        for f in sorted(os.listdir(full)) if os.path.isdir(full) else []:
            if f"{d}/{f}" not in files:
                bad.append(f"{d}/{f} (not the generator's)")
    if bad:
        print("not current:" if check else "left over:", ", ".join(bad))
        return 1
    print("current" if check else f"written: {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
