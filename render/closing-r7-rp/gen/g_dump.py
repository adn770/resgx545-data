#!/usr/bin/env python3
"""g_dump.py: the r7-rp `dump` area's generator: stages q293 (4 jobs) and q139 (24 jobs), both tool t4 (plan
closing7/a/exp-pixel-r7.md sections 3.5 and 3.6).  `PY gen/g_dump.py` writes tables/q293.txt, tables/q139.txt,
predictions/q293.tsv, predictions/q139.tsv and gen/data/sources-dump.lst.  Deterministic.

q293 (Q293's last item, E897 post hoc, held out here): three renders in one scene at 64 x 64, CR_TE_AA 0x40000000, renders
1 and 2 geometry only, render 3 draws; the kernel pokes before render 3 reach render 2's own object (dump dwords 27 to 53).
  u1 control  no poke: objects at 0, 27, 54, each with a zero at +11 and the format word at +12; render 3 0 triangle pixels
  u2 control  E888's t7 again (-n 2, 2:par:11=0x00000001): its kept dump head (dwords 0-63) and image
  u3 heldout  3:par:38..53 = E829's p3 words (its 2:par:11..26, read from E829's kept cases.tsv) shifted by 27: 4096 triangle
  u4 heldout  3:par:38=0xffffffff: 0 triangle pixels
q139 (Q139, E877's misses): the datasets' own command token for token (ta/mtile-fields*/scripts: `tri --tri-full --pixels
--width W --height H --max-width W --max-height H $args --wait-ms 20000`) plus `--keep-going --dump-render "$W/dump"`.
--keep-going is a deviation from the plan's row shape, needed: without it t4 (4623753 sgxfive-test.c, the tri loop) breaks
on a render that does not check and never reaches dump_render ("if (!ret && o->dump_dir)"), so every wrong image would keep
no dump (needdump: rc 23).  With one render it changes only the tool's last line ("tri: 0 of 1 renders ok").
"""
import hashlib
import os
import re
import shlex
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
import lib_dump as L  # noqa: E402
import scorekit  # noqa: E402

DATA = "/Users/jtorra/src/resgx545-data"
SAFE = DATA + "/ta/mtile-fields"
RISKY = DATA + "/ta/mtile-fields-risky"
E888_T = DATA + "/render/closing-r6-render4x/out/20261112-144822/t"
E888_TABLE = "/Users/jtorra/src/scratch/resgx545/closing6/r6-render4x/tables/t.txt"
E829_CASES = DATA + "/render/closing-r4-q285/out/20261111-081210/a-pb/cases.tsv"
E877_SCORE = "/Users/jtorra/src/scratch/resgx545/closing6/fold-misc/q139/q139_score.out"
T7 = "t7-tri-te40-poke11"

HEADER = "case\tquantity\tvalue\tmodel\tset\tsrc\n"

# ---- q293 ----------------------------------------------------------------------------------------------------------------------
Q293_BASE = ("tri --tri-full --keep-going --wait-ms 20000 --width 64 --height 64 --max-width 64 --max-height 64 -n 3 "
             "--geometry 1 --geometry 2 --poke cmd:1=0x40000000 --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 "
             "--poke cmd:16=0xeaa26e26")
DUMP = '--dump-render "$W/dump"'
Q293_KNOBS = "expectdiff rgn:1 needdump"
U1, U2, U3, U4 = "q293-u1-ctl-n3", "q293-u2-ctl-t7", "q293-u3-obj2-twin", "q293-u4-obj2-ffff"


def e829_p3():
    """E829's p3 kpokes (pb-p3a-twin's args in its kept cases.tsv): [(dword, value)], dwords 11 to 26."""
    rows = L.read_cases(os.path.dirname(E829_CASES))
    sp = re.findall(r"--kpoke-render 2:par:(\d+)=(0x[0-9a-f]{8})", rows["pb-p3a-twin"]["args"])
    out = [(int(d), int(v, 16)) for d, v in sp]
    assert [d for d, _ in out] == list(range(11, 27)), out
    return out


def e888_t7_args():
    """E888's t7 command, exactly as its table froze it (r6-render4x tables/t.txt) and as its kept cases.tsv ran it."""
    for ln in open(E888_TABLE).read().splitlines():
        if ln.startswith(T7 + "|"):
            args = ln.split("|", 5)[5]
            ran = L.read_cases(E888_T)[T7]["args"]
            assert ran == args, (ran, args)
            return args
    raise KeyError(T7)


def q293_rows():
    u3 = " ".join("--kpoke-render 3:par:%d=0x%08x" % (d + 27, v) for d, v in e829_p3())
    return [
        (U1, "control", "risky", Q293_KNOBS, "t4", "%s %s" % (Q293_BASE, DUMP)),
        (U2, "control", "safe", Q293_KNOBS, "t4", e888_t7_args()),
        (U3, "heldout", "risky", Q293_KNOBS, "t4", "%s %s %s" % (Q293_BASE, u3, DUMP)),
        (U4, "heldout", "risky", Q293_KNOBS, "t4", "%s --kpoke-render 3:par:38=0xffffffff %s" % (Q293_BASE, DUMP)),
    ]


def q293_predictions():
    t7txt = L.read_text(os.path.join(E888_T, T7 + ".txt.gz"))
    t7par = L.read_bytes(os.path.join(E888_T, T7 + ".tri.param.bin.gz"))
    src_txt = os.path.join(E888_T, T7 + ".txt.gz")
    src_par = os.path.join(E888_T, T7 + ".tri.param.bin.gz")
    head = ",".join("%08x" % x for x in L.dwords(t7par, 64))
    d = L.diff_count(t7txt)
    p3 = e829_p3()
    out = [
        (U1, "objects", "0,27,54", "H-LAYOUT", "control", "plan 3.5; E897 (objects at 0 and 27 in 13 of 13 kept dumps)"),
        (U1, "inserted", "+11 zero, +12 0x00040101 (each object)", "H-LAYOUT", "control", "plan 3.5; E897"),
        (U1, "tri3_triangle", "0", "H-LAYOUT", "control", "plan 3.5; E897 (11 of 11 displaced jobs draw nothing)"),
        (U2, "dump_head", head, "E888", "control", src_par),
        (U2, "tri2", L.counts_text(L.tri_counts(t7txt, 2)), "E888", "control", src_txt),
        (U2, "diff", "%d of %d" % d, "E888", "control", src_txt),
        (U2, "target_hash", L.target_hash(t7txt), "E888", "control", src_txt),
        (U2, "kpoke", "par:11=0x00000001", "E888", "control", src_txt),
        (U3, "kpoke", ",".join("par:%d=0x%08x" % (dw + 27, v) for dw, v in p3), "plan", "heldout",
         "E829 p3 (pb-p3a-twin) shifted by 27: " + E829_CASES),
        (U3, "dwords_38_53", ",".join("%08x" % v for _, v in p3), "plan", "heldout", "the poked words"),
        (U3, "tri3", "4096 triangle, 0 background, 0 other", "H-READ2", "heldout",
         "plan 3.5: render 2's object in the bit-29-set layout draws; objects 1 and 3 stay displaced"),
        (U3, "diff", "0 of 4096", "H-READ2", "heldout", "plan 3.5: 0 wrong against render 3's colours"),
        (U3, "tri3_triangle", "0", "rival", "heldout", "plan 3.5 rival: render 2's object read otherwise or not at all"),
        (U4, "kpoke", "par:38=0xffffffff", "plan", "heldout", "plan 3.5"),
        (U4, "dword38", "ffffffff", "plan", "heldout", "the poked word"),
        (U4, "tri3_triangle", "0", "H-READ2", "heldout", "plan 3.5 (as E829 p4 and E888 t7)"),
    ]
    return out, [src_txt, src_par]


# ---- q139 ----------------------------------------------------------------------------------------------------------------------
Q139_KNOBS = "expectdiff needdump"
# (row name, set, dataset case); the size comes from the dataset's cases.tsv.  Picked by the builder (plan 3.6):
#   fit m2-B2-24: the CR_TE_MTILE2 B2 case AT B3 (the 640 x 480 rule's B3 is 24, 0x02010018), drawn exactly in E509 and
#     predicted wrong by E877's model; the held-out m2-B2-28: past B3 and still inside the target's 30 tile rows (B2 32 to 40
#     put the boundary past the target, a different case); bit 31: m1-flag0 at 640 x 480 (the rule's 0x82010018 with bit 31
#     cleared, 288 tiles wrong, the only 640 x 480 bit-31 case of the file).
Q139_CASES = [
    ("q139-c-256x256-ctl", "control", "q100-256x256-ctl-r1"),
    ("q139-c-640x480-ctl", "control", "q100-640x480-ctl-r1"),
    ("q139-c-256x256-m1-B1-5", "control", "q100-256x256-m1-B1-5"),
    ("q139-f-256x256-m1-B2-8", "fit", "q100-256x256-m1-B2-8"),
    ("q139-f-256x256-m1-B2-5", "fit", "q100-256x256-m1-B2-5"),
    ("q139-f-256x256-m2-B2-10", "fit", "q100-256x256-m2-B2-10"),
    ("q139-f-256x256-stride-8", "fit", "q100-256x256-stride-8"),
    ("q139-f-256x256-stride-16", "fit", "q100-256x256-stride-16"),
    ("q139-f-256x256-part1-8_8_8", "fit", "q100-256x256-part1-8_8_8"),
    ("q139-f-640x480-m1-B1-20", "fit", "q100-640x480-m1-B1-20"),
    ("q139-f-640x480-m1-B2-20", "fit", "q100-640x480-m1-B2-20"),
    ("q139-f-640x480-m2-B1-17", "fit", "q100-640x480-m2-B1-17"),
    ("q139-f-640x480-m2-B2-24", "fit", "q100-640x480-m2-B2-24"),
    ("q139-h-256x256-m1-B2-12", "heldout", "q100-256x256-m1-B2-12"),
    ("q139-h-256x256-m2-B2-12", "heldout", "q100-256x256-m2-B2-12"),
    ("q139-h-256x256-stride-4", "heldout", "q100-256x256-stride-4"),
    ("q139-h-256x256-stride-24", "heldout", "q100-256x256-stride-24"),
    ("q139-h-256x256-part2-10_10_10", "heldout", "q100-256x256-part2-10_10_10"),
    ("q139-h-640x480-m1-B1-28", "heldout", "q100-640x480-m1-B1-28"),
    ("q139-h-640x480-m1-B2-32", "heldout", "q100-640x480-m1-B2-32"),
    ("q139-h-640x480-m2-B1-20", "heldout", "q100-640x480-m2-B1-20"),
    ("q139-h-640x480-m2-B2-28", "heldout", "q100-640x480-m2-B2-28"),
    ("q139-h-640x480-m1-flag0", "heldout", "q100-640x480-m1-flag0"),
    ("q139-r-256x256-m1-B2-8", "replicate", "q100-256x256-m1-B2-8"),
]
Q139_TEMPLATE = ('tri --tri-full --pixels --width "$w" --height "$h" --max-width "$w" --max-height "$h" \\\n'
                 '\t\t $args --wait-ms 20000')


def dataset_rows():
    """{case: (dataset dir, W, H, args)} of both datasets' cases.tsv."""
    out = {}
    for d in (SAFE, RISKY):
        with open(d + "/cases.tsv") as f:
            next(f)
            for ln in f:
                c = ln.rstrip("\n").split("\t")
                out[c[0]] = (d, int(c[2]), int(c[3]), c[4] if len(c) > 4 else "")
    return out


def dataset_script(d):
    s = os.path.join(d, "scripts", os.path.basename(d) + ".sh")
    assert Q139_TEMPLATE in open(s).read(), "the dataset's command is not the template: " + s
    return s


def q139_command(w, h, args):
    """The dataset's command for (w, h, args), token for token, plus --keep-going and the dump (see the docstring)."""
    t = ["tri", "--tri-full", "--pixels", "--width", str(w), "--height", str(h), "--max-width", str(w), "--max-height",
         str(h)] + args.split() + ["--wait-ms", "20000"]
    return " ".join(t) + " --keep-going " + DUMP


def e877_misses():
    return set(re.findall(r"^  miss (\S+) \(", open(E877_SCORE).read(), re.M))


def q139_rows_and_predictions():
    ds = dataset_rows()
    misses = e877_misses()
    rows, preds, sources = [], [], set()
    for name, st, case in Q139_CASES:
        d, w, h, args = ds[case]
        sources |= {d + "/cases.tsv", dataset_script(d)}
        if st != "control" or case.endswith("m1-B1-5"):
            assert d == RISKY, case
        if st == "control":
            assert case not in misses, case
        else:
            assert case in misses, "%s is not a miss of E877's frozen model" % case
        dump = os.path.join(d, "dumps", case + ".txt.gz")
        sources.add(dump)
        text = L.read_text(dump)
        complete, bad = L.image_tiles(text, w, h)
        assert complete and re.search(r"^job: ok", text, re.M), "%s kept no whole image" % case
        risk = "safe" if not args else "risky"
        rows.append((name, st, risk, Q139_KNOBS, "t4", q139_command(w, h, args)))
        preds += [(name, "ds_case", case, "dataset", st, dump),
                  (name, "size", "%dx%d" % (w, h), "dataset", st, d + "/cases.tsv"),
                  (name, "kept_wrong", L.tiles_text(bad), "dataset", st, dump),
                  (name, "kept_count", str(len(bad)), "dataset", st, dump)]
        if st == "control" and not args:
            preds += [(name, "image", "exact", "control", st, dump),
                      (name, "headers", "every target tile has one header with a stream", "control", st,
                       "plan 3.6 (the baseline of its size)")]
        elif st == "control":
            preds += [(name, "image", "exact", "control", st, dump),
                      (name, "headers_in_place", "all", "H-MOVED", st, "plan 3.6 (the exactly drawing poked control)")]
        elif st in ("fit", "replicate"):
            preds += [(name, "hmoved", "wrong tiles = tiles whose header is not at the baseline's slot", "H-MOVED", st,
                       "plan 3.6"),
                      (name, "hmoved", "a wrong tile with its header in place", "H-INPLACE", st, "plan 3.6 rival")]
        else:
            preds += [(name, "heldout", "not read by score(); score_dump.py q139-heldout KEPT MODEL_SHA after the fold's "
                       "fitted model", "protocol", st, "plan 3.6")]
    return rows, preds, sorted(sources)


# ---- controls and what a row can produce (scorekit.refuse_unreadable) ----------------------------------------------------------
CONTROLS = {
    "q293": [{"name": U1, "reads": ["objects", "tri3"]},
             {"name": U2, "reads": ["dump_head", "tri2", "diff", "target_hash", "kpoke_applied"]}],
    "q139": [{"name": "q139-c-256x256-ctl", "reads": ["image_tiles", "headers", "streams"]},
             {"name": "q139-c-640x480-ctl", "reads": ["image_tiles", "headers", "streams"]},
             {"name": "q139-c-256x256-m1-B1-5", "reads": ["image_tiles", "headers"]}],
}


def controls(stage):
    return [dict(c) for c in CONTROLS[stage]]


def producible(row):
    """The reading keys a row's job can produce, from its args (row: a dict with 'args', or the args string)."""
    args = row["args"] if isinstance(row, dict) else row
    t = shlex.split(args.replace('"$W/dump"', "DUMP"))
    keys = {"diff", "target_hash"}
    n = int(t[t.index("-n") + 1]) if "-n" in t else 1
    geo = {int(t[i + 1]) for i, a in enumerate(t) if a == "--geometry"}
    keys |= {"tri%d" % k for k in range(1, n + 1) if k not in geo}
    if "--dump-render" in t:
        keys |= {"objects", "dump_head", "headers", "streams"}
    if "--kpoke-render" in t:
        keys.add("kpoke_applied")
    if "--pixels" in t:
        keys.add("image_tiles")
    return keys


def check_controls(stage, rows):
    by = {r[0]: {"args": r[5]} for r in rows}
    scorekit.refuse_unreadable({c["name"]: (tuple(c["reads"]), by[c["name"]]) for c in controls(stage)}, producible)


# ---- writing -------------------------------------------------------------------------------------------------------------------
def table_text(stage, rows, comments):
    out = ["#stage %s" % stage, "#limit 1"] + ["# " + c for c in comments]
    out += ["|".join(r) for r in rows]
    return "\n".join(out) + "\n"


def preds_text(preds):
    return HEADER + "".join("\t".join(p) + "\n" for p in preds)


Q293_COMMENTS = [
    "q293: render 2's own object, held out (plan closing7/a/exp-pixel-r7.md 3.5; E897 read it post hoc, E829, E888).",
    "-n 3 with renders 1 and 2 geometry only is new for this command (E888 ran -n 2): u1 runs FIRST; any class but ok",
    "stops the stage (no hypo knob: a fault is rc 4).  rgn:1: the module refuses TE_AA bit 30 on a context without --aa4",
    "unless render_rgn_arrays forces the count (E829, E888).  u2 is E888's t7 byte for byte (r6-render4x tables/t.txt).",
    "u3's 16 kpokes are E829's p3 words (2:par:11..26) at 3:par:38..53; 16 is t4's KPR_MAX (sgxfive-test.c), not over it.",
]
Q139_COMMENTS = [
    "q139: TA dumps at E877's missed cases (plan 3.6).  The datasets' own command token for token (ta/mtile-fields*/",
    "scripts) plus --keep-going (deviation: without it t4 keeps no dump of a wrong image) and --dump-render.",
    "Controls first (the baselines of each size, then the poked exact control), fit, held out, the replicate last.",
    "Held-out rows are read only after the fold's fitted model is hashed: score_dump.py q139-heldout KEPT MODEL_SHA.",
    "Disk: 640 x 480 --pixels prints 3.4 MB of text, the parameter dump is 4.6 MB raw (gzipped when kept).",
]


def write(kp=KP):
    r293 = q293_rows()
    p293, s293 = q293_predictions()
    r139, p139, s139 = q139_rows_and_predictions()
    check_controls("q293", r293)
    check_controls("q139", r139)
    assert len(r293) == 4 and len(r139) == 24
    files = {
        "tables/q293.txt": table_text("q293", r293, Q293_COMMENTS),
        "tables/q139.txt": table_text("q139", r139, Q139_COMMENTS),
        "predictions/q293.tsv": preds_text(p293),
        "predictions/q139.tsv": preds_text(p139),
    }
    sources = sorted(set(s293 + s139 + [E888_TABLE, os.path.join(E888_T, "cases.tsv"), E829_CASES, E877_SCORE]))
    files["gen/data/sources-dump.lst"] = "".join(s + "\n" for s in sources)
    for rel, text in files.items():
        p = os.path.join(kp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
    return {rel: hashlib.sha256(t.encode()).hexdigest()[:12] for rel, t in files.items()}


if __name__ == "__main__":
    for rel, h in write().items():
        print("%s %s" % (h, rel))
