#!/usr/bin/env python3
"""twins.py: the scene twin of a row (closing5/render4x/exp-render4x-r5.md 2.1, dry run 1).  A row's frozen page need comes from a KEPT
row that ran the same scene: the same verb and options once the options that only change what is printed or kept are stripped
(--dump-render P, --dump-each, --words P, --regs R, --pixels, --wait-ms N, --keep-going, --keep-overflow, -n 1, a maximum equal to the
target) and the context's region-header array count is folded into the key (--aa4 or the knob rgn:4 = four, rgn:N = N, else one).
The PB size (pb:0xNN) is not in the key: a twin counts only if it completed without an overflow, and its need is the count of non-zero
pages among the first 0x422 of its render_param dump (every kept dump is 0x464 pages, whatever P was).  Twins that disagree, a row
with no twin, or a frozen need that differs from its twins' fail the build (rgen.py) and the test (tests/test_twin.py).
Standard library only.
"""
import csv
import glob
import gzip
import os
import re
import shlex

DATA = os.environ.get("RESGX545_DATA", "/Users/jtorra/src/resgx545-data")
STRIP_VAL = ("--dump-render", "--words", "--regs", "--wait-ms")
STRIP_FLAG = ("--dump-each", "--pixels", "--keep-going", "--keep-overflow", "--aa4")
PB_PAGES = 0x422


def tokens(args):
    return shlex.split(args.replace('"$W/dump"', "DUMP").replace('"$W/words"', "WORDS"), posix=True)


def arrays(args, knobs):
    k = (knobs or "").split()
    if "--aa4" in tokens(args):
        return 4
    for x in k:
        m = re.match(r"rgn:(\d)$", x)
        if m:
            return int(m.group(1))
    return 1


def key(args, knobs=""):
    """(verb, normalized options, arrays): the scene a row draws, whatever it prints or keeps."""
    t = tokens(args)
    verb, rest = t[0], t[1:]
    opts, i = [], 0
    while i < len(rest):
        a = rest[i]
        if a in STRIP_VAL:
            i += 2
            continue
        if a in STRIP_FLAG:
            i += 1
            continue
        if a.startswith("-") and i + 1 < len(rest) and not rest[i + 1].startswith("--"):
            opts.append((a, rest[i + 1]))
            i += 2
        else:
            opts.append((a, None))
            i += 1
    d = dict((o, v) for o, v in opts if v is not None)
    drop = set()
    if d.get("--max-width") == d.get("--width") and d.get("--max-height") == d.get("--height"):
        drop |= {"--max-width", "--max-height"}
    if d.get("-n") == "1":
        drop.add("-n")
    opts = sorted((o, v or "") for o, v in opts if o not in drop)
    return (verb, tuple(opts), arrays(args, knobs))


def key_text(k):
    return "%s %s arrays=%d" % (k[0], " ".join(o + ("=" + v if v else "") for o, v in k[1]), k[2])


def scene_pages(dump):
    return sum(1 for i in range(min(len(dump) // 4096, PB_PAGES)) if dump[i * 4096:(i + 1) * 4096].strip(b"\0"))


def kept_rows(root=DATA + "/render"):
    """Every kept `tri` or `probe` row with a parameter dump in the published closing sessions: (source, name, knobs, args, class, path
    of the dump, path of the output).  The dump of a `tri` is NAME.tri.param.bin.gz, of a probe NAME.PROG.param.bin.gz."""
    out = []
    for ct in sorted(glob.glob(root + "/closing-*/out/*/*/cases.tsv") + glob.glob(root + "/closing-*/out/*/cases.tsv")):
        d = os.path.dirname(ct)
        for row in csv.DictReader(open(ct), delimiter="\t"):
            a = row.get("args") or ""
            if not a.startswith("tri"):
                continue
            p = os.path.join(d, row["name"] + ".tri.param.bin.gz")
            if not os.path.exists(p):
                continue
            out.append((os.path.relpath(ct, root), row["name"], row.get("knobs") or "", a, row.get("class"), p,
                        os.path.join(d, row["name"] + ".txt.gz")))
    return out


def overflowed(outpath):
    if not os.path.exists(outpath):
        return True
    t = gzip.open(outpath).read().decode("utf-8", "replace")
    return bool(re.search(r"scene overflowed|overflowed the parameter buffer|overflowed, |\d+ overflowed$", t, re.M))


def table(root=DATA + "/render"):
    """{key: [(source, name, pages)]} over the kept rows that completed without an overflow."""
    tb = {}
    for src, name, knobs, a, cls, p, o in kept_rows(root):
        if cls != "ok" or overflowed(o):
            continue
        k = key(a, knobs)
        tb.setdefault(k, []).append((src, name, scene_pages(gzip.open(p).read())))
    return tb


def need_of(args, knobs, tb):
    """(pages, twins) for a row; pages None if it has no twin, 'DISAGREE' if its twins differ."""
    tw = tb.get(key(args, knobs), [])
    if not tw:
        return None, []
    vals = {t[2] for t in tw}
    return (vals.pop() if len(vals) == 1 else "DISAGREE"), tw


def check(rows, tb):
    """rows: [(name, args, knobs, frozen_need, set, model_ok)].  Problems: a row with a frozen need whose twins give another count, or
    whose twins disagree, or a CONTROL with no twin or with a need marked [model] (model_ok False for a control).  Explore rows may carry
    a [model] need (model_ok True)."""
    bad = []
    for name, args, knobs, need, sset, model_ok in rows:
        if need is None:
            continue
        got, tw = need_of(args, knobs, tb)
        if got is None:
            if not model_ok:
                bad.append("%s: no kept twin for its scene (%s): a %s row cannot carry a model need" % (name, key_text(key(args, knobs)), sset))
            continue
        if got == "DISAGREE":
            bad.append("%s: its twins disagree: %s" % (name, ", ".join("%s %s %d" % t for t in tw)))
            continue
        if int(need) != got:
            bad.append("%s: frozen need %s, its %d kept twins say %d (%s)" % (name, need, len(tw), got, ", ".join("%s/%s" % (t[0], t[1]) for t in tw[:3])))
    return bad
