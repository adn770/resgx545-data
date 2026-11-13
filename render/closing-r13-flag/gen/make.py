#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""make.py [--check]: r13-flag's tables, predictions and programs from gen/f1.py, f2.py, f3.py.
Writes tables/STAGE.txt, predictions/STAGE.tsv, predictions/f1/NAME.MODEL.txt (an image's 2048
tokens, raster order) and bins/*.bin; --check writes nothing and fails on any file that differs
(the generator is current). Every repository file read is read at session.toml's frozen commits
(gen/pins.py); the assembler is resgx545's usse-asm (tools/usse-asm/usse-asm of the main
checkout, /Users/jtorra/src/resgx545)."""
import hashlib
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import f1  # noqa: E402
import f2  # noqa: E402
import f3  # noqa: E402
import pins  # noqa: E402
import tex  # noqa: E402

KP = os.path.dirname(HERE)
HEAD = "case\tquantity\tvalue\tmodel\tset\tsource\n"


def digest(tokens):
    return hashlib.sha256(" ".join(tokens).encode()).hexdigest()


def toks(img):
    return ["%08x" % v for v in img]


def stage_f1(files):
    rows, preds = [], []
    src = {"H-E566": "E566 (tw32-ctl kept; tw32-t3b14 faulted)", "H-E561": "E561 tile law",
           "H-TWIDX": "plan H-TWMOVE (E1003 move in the twiddled index)",
           "H-TWX": "E1003 move in the texel column, tile law unwrapped [infer]",
           "H-TWX-WRAP": "E1003 move in the column, then wrap [infer]",
           "H-FAULTANY": "plan rival: bit 14 faults any twiddled read"}
    for name, sset, knobs, spec, models, pages in f1.jobs():
        files[f"bins/{name}.bin"] = tex.assemble(tex.text(spec))
        rows.append(f"{name}|{sset}|{'risky' if 'expectfault' in knobs else 'safe'}|{knobs}|t10p|"
                    f"{f1.args(name)}")
        for m, (end, what) in models.items():
            preds.append((name, "end", end, m, sset, src[m]))
            if end == "ok":
                t = toks(what)
                files[f"predictions/f1/{name}.{m}.txt"] = (" ".join(t) + "\n").encode()
                preds.append((name, "image", digest(t), m, sset, src[m]))
            elif what is not None:
                preds.append((name, "fpage", f"+{what:#x}", m, sset, src[m] + " (from the scratch)"))
    head = ["#stage f1", "#limit 2",
            "# r13-flag f1, Q078 T3 bit 14 on a twiddled 32 x 32 texture (rank-round13.md section 2 F1; "
            "PLANNED FAULTS, user OK R13-3 a). gen/f1.py.",
            "# Pair A: E566's tw32-ctl (control, its kept image) and tw32-t3b14 (u in (1, 2): move 4096; "
            "E566 faulted): H-TWIDX no fault (index + 4096, inside 16 pages) against H-TWX (fault at "
            "scratch + 0x40000), H-FAULTANY.",
            "# Pair B (held out): u = x / 4096 (move x texels), its bit-clear reference (control, the tile "
            "law): H-TWIDX / H-TWX / H-TWX-WRAP images, no fault; H-FAULTANY faults.",
            "# #limit 2 = the two planned bit-14 rows (expectfault); the controls do not expectfault (a fault "
            "there stops the stage, 4). Strict health after every fault; hook_fault stops on a fault without "
            "its kernel BIF line, a hang, or SGX recovery failed (24)."]
    return head + rows, preds


def stage_f2(files):
    for n, pin in f2.BINS.items():
        files[f"bins/{n}"] = pins.blob(pin)
    rows, preds = [], []
    src = {"H-FIXED": "E383 bit-12 mode 0 words (r13-tex sb12 H-FIXED)", "H-E383": "E383 (9 of 9 faulted)",
           "H-E383-PAGE": "E383 kernel log [infer: same heap layout]", "H-NOFAULT": "null"}
    for name, sset, knobs, args, q in f2.jobs(pins.blob):
        rows.append(f"{name}|{sset}|{'risky' if 'expectfault' in knobs else 'safe'}|{knobs}|t10|{args}")
        for quantity, mv in q.items():
            for m, v in mv.items():
                preds.append((name, quantity, v, m, sset, src[m]))
    words = f2.mode0_words(pins.blob)
    files["predictions/f2/words-m0.txt"] = (" ".join("%08x" % w for w in words) + "\n").encode()
    head = ["#stage f2", "#limit 3",
            "# r13-flag f2, Q046 sideband bit 11 (rank-round13.md section 2 F2; PLANNED FAULTS, user OK "
            "R13-3 a). gen/f2.py. E383's form, sideband 0x0a00 | mode in modes 0, 4, 8.",
            "# Control first: E383's bit-12 mode 0 (0x1200), inset >= 4055 of E383's words. Frozen: "
            "H-E383 (each faults), H-E383-PAGE (0x91000 at page 0x37001000), H-NOFAULT.",
            "# #limit 3 = the three planned rows; the third is the last row. hook_fault stops on a fault "
            "without its kernel BIF line, a hang, or SGX recovery failed (24)."]
    return head + rows, preds


def stage_f3(files):
    files["bins/p1131-green__0.bin"] = pins.blob(f3.GREEN)
    files["bins/p1131-blue__0.bin"] = tex.assemble(f3.blue_text(pins.blob))
    pins.blob(f3.PROGS)
    rows, preds = [], []
    p = f3.predictions()
    tool = {"fill": "t10", "plain": "t10"}
    for name, sset, knobs, args, job in f3.ROWS:
        risky = "expectfault" in knobs.split()
        rows.append(f"{name}|{sset}|{'risky' if risky else 'safe'}|{knobs}|{tool.get(job[0], 't10')}|{args}")
        for m, end in p[name].items():
            preds.append((name, "end", end, m, sset, "gen/f3.py simulate"))
    head = ["#stage f3", f"#limit {f3.LIMIT}",
            "# r13-flag f3, Q163 VDM_STATE1 bits 11:9 hang sequences (rank-round13.md section 2 F3; HANGS "
            "THE KERNEL RECOVERS, user OK R13-4 a). gen/f3.py. Kit words noreset and idle:S (0493e36).",
            "# Control first: E413's v = 7 pair (tri --poke vdm:1^=0xa00 twice: the second hangs; if it "
            "completes hook_check stops the stage). Then block-2 v = 1 at c = 0, 2, 5 (E700's two-block "
            "stream, grid bits 7:0 = 5), the 128 x 128 one-block pair, idle:60, a fill between, a reset "
            "row between, the health between.",
            "# #limit 8 = the eight planned rows (expectfault); the control's hang is not counted; the last "
            "planned row is the last row. Any other row that hangs stops the stage (4). hook_fault stops at "
            "the first failed recovery (SGX recovery failed), a hang without its kernel line, or a fault (24)."]
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
    for st, fn in (("f1", stage_f1), ("f2", stage_f2), ("f3", stage_f3)):
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
