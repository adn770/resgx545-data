#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r19-own's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 6809cddd24ce, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

The kept TA data copies (t18b --kept-copy): NAME.kept.closed.1.bin (after the first context's
early close, before the second context's render) and NAME.kept.1.bin (after that render, before
any other close). The DPM pages are located by the fork's own layout (sgx_render.c at
456404fcffe5, sgx_render_layout() and sgx_render_tadata_layout_in(), 1x, automatic tail room):
control = the tail pointers rounded up to a page, OTPM and state the next two pages (64x64: 0x1000,
0x2000, 0x3000; 1024x768: 0x4000, 0x5000, 0x6000; 2048x1536: 0x10000, 0x11000, 0x12000;
4096x4096: state 0x42000 as E627 read it).

own2 (Q192): closed_state_nz and after_state_nz, the non-zero dwords of the state page in each
copy; a row is held for H-RSTORE when the closed copy holds the frozen count (18, or >0 held out)
and the after copy none, and is reported against H-EARLY and H-LATE too; every row also prints the
pages that differ between the two copies (dword counts per page) and the after copy's non-zero
words of the control, OTPM and state pages, whole (what the store writes).
own1 (Q191): the owner words (control word 0, OTPM word 0, state words 0 and 1) in each copy;
64x64 rows held for H-RENDER (none closed, all four after) against H-CLOSE; the 1024x768 rows'
state words against H-COUNT (U << 16 | head, tail with U 0x11 to 0x15), H-CONST, H-NONE.

REQUIRED: the files each stage's scorer reads; read_files(STAGE, DIR) reads exactly what score()
reads; producible(row) is the set of reading keys a row's job can produce."""
import os
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

PER_ROW = (".txt", ".kept.closed.1.bin", ".kept.1.bin")
REQUIRED = {"own2": PER_ROW + ("cases.tsv", "void.tsv", "readings.tsv"),
            "own1": PER_ROW + ("cases.tsv", "void.tsv", "readings.tsv")}
GATES = {}          # neither stage is gated (hook_check stops a stage whose copies fail)
PAGE = 4096
CLAIM = {"own2": "H-RSTORE: the partial owner's state page holds its lists after the close and "
                 "is zero after the second context's render (Q192)",
         "own1a": "H-RENDER: the 64x64 owner's words are stored by the second context's render, "
                  "not at the first context's close (Q191 a, c)",
         "own1b": "H-COUNT: the 1024x768 owner's state words count its pages (Q191 b)"}


def layout(w, h):
    """(control, otpm, state, size) byte offsets of a 1x render context's TA data for targets up
    to w x h: the fork's sgx_render_layout() and sgx_render_tadata_layout_in() (room 0)."""
    tx, ty = -(-w // 32), -(-h // 16)
    n = 4 if w * h >= 640 * 480 else 2
    mx = -(-(-(-tx // n)) // 4) * 4
    my = -(-(-(-ty // n)) // 4) * 4
    span, side = max(n * mx, n * my), 1
    while side < span:
        side <<= 1
    tail = 4 * side * side
    rgn_size = 0xc0 * (mx // 4) * (my // 4) * n * n
    control = -(-tail // PAGE) * PAGE
    rgn = control + 3 * PAGE
    zls = rgn + -(-rgn_size // PAGE) * PAGE
    return control, control + PAGE, control + 2 * PAGE, zls + -(-rgn_size // PAGE) * PAGE


def producible(row):
    a = row["args"].split()
    if a[:1] == ["tri"] and "--ctx2" in a and "--kept-copy" in a and "--close-first-early" in a:
        return {"ovf", "kept", "size"}
    return {"ovf"} if a[:1] == ["tri"] else set()


def arg(args, name, default=None):
    a = args.split()
    return a[a.index(name) + 1] if name in a else default


def dwords(b, off, n):
    if b is None or len(b) < off + 4 * n:
        return None
    return list(struct.unpack_from(f"<{n}I", b, off))


def nz(ws):
    return None if ws is None else sum(1 for x in ws if x)


def kept(d, n, which):
    return K._read(os.path.join(d, f"{n}.kept.{which}1.bin"))


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        K.text(d, n + ".txt")
        kept(d, n, "closed.")
        kept(d, n, "")


def premise_row(r, case, d):
    """None when the row's job ran and both copies are the layout's size, else why not."""
    if not case or not K.completed(case):
        return "the job did not complete"
    w, h = int(arg(r["args"], "--width")), int(arg(r["args"], "--height"))
    size = layout(w, h)[3]
    for which in ("closed.", ""):
        b = kept(d, r["name"], which)
        if b is None or len(b) != size:
            return f"kept.{which}1.bin {'missing' if b is None else len(b)} (want {size} bytes)"
    return None


def want_count(v, got):
    if got is None:
        return None
    if v.startswith(">"):
        return got > int(v[1:])
    return got == int(v)


def words4(b, w, h):
    c, o, s, _ = layout(w, h)
    ws = [dwords(b, c, 1), dwords(b, o, 1), dwords(b, s, 2)]
    if None in ws:
        return None
    return ws[0] + ws[1] + ws[2]


def fmt(ws):
    return "none" if ws is not None and not any(ws) else \
        ",".join(f"0x{x:08x}" for x in ws) if ws is not None else "-"


def page_diff(a, b):
    out = []
    for p in range(min(len(a), len(b)) // PAGE):
        x, y = dwords(a, p * PAGE, 1024), dwords(b, p * PAGE, 1024)
        k = sum(1 for i in range(1024) if x[i] != y[i])
        if k:
            out.append(f"p{p}:{k}")
    return " ".join(out) or "none"


def nonzero_words(b, off):
    ws = dwords(b, off, 1024) or []
    return " ".join(f"{i}=0x{x:08x}" for i, x in enumerate(ws) if x) or "none"


def control_state(r, case, d, rd, preds):
    """A control: its premise readings against the frozen CTL values, then (own1) its words."""
    want = preds.get(r["name"], {})
    got = rd.get(r["name"], {})
    for q in r["reads"]:
        g = got.get(q)
        if g in (None, "", "-"):
            return None, f"{q} not read"
        if g != want.get(q, {}).get("CTL"):
            return False, f"{q} {g} (frozen {want.get(q, {}).get('CTL')})"
    why = premise_row(r, case, d)
    if why:
        return None, why
    if "closed_words" in want:
        w, h = int(arg(r["args"], "--width")), int(arg(r["args"], "--height"))
        cw = fmt(words4(kept(d, r["name"], "closed."), w, h))
        aw = fmt(words4(kept(d, r["name"], ""), w, h))
        if (cw, aw) != (want["closed_words"]["CTL"], want["after_words"]["CTL"]):
            return False, f"words closed {cw} after {aw} (frozen none, none)"
    return True, "premise read as frozen"


def group(stage, r):
    """The claim a row counts toward: own2's, or own1's (a, c: 64x64) and (b: 1024x768)."""
    if stage == "own2":
        return "own2"
    return "own1a" if arg(r["args"], "--width") == "64" else "own1b"


def verdicts(stage, d):
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    rd = K.readings(d)
    controls, rows, lines, counts = {}, [], [], {}
    for r in K.table(KP, stage):
        n = r["name"]
        case = cases.get(n)
        if r["set"] == "control":
            st, why = control_state(r, case, d, rd, preds)
            controls[n] = st
            lines.append(f"CONTROL {n}: {why}: "
                         f"{'PASS' if st else 'FAILED' if st is False else 'cannot tell'}")
            if stage == "own1":     # o1-4 is the flag-0x4 control only (no hypothesis row)
                continue
        why = premise_row(r, case, d)
        if why:
            rows.append((group(stage, r), None))
            lines.append(f"ROW {n}: cannot tell ({why})")
            continue
        w, h = int(arg(r["args"], "--width")), int(arg(r["args"], "--height"))
        a, b = kept(d, n, "closed."), kept(d, n, "")
        c, o, s, _ = layout(w, h)
        want = preds.get(n, {})
        if stage == "own2":
            got = {"closed_state_nz": nz(dwords(a, s, 1024)),
                   "after_state_nz": nz(dwords(b, s, 1024))}
            fits = [m for m in ("H-RSTORE", "H-EARLY", "H-LATE")
                    if all(want_count(want[q][m], got[q]) for q in got)]
            state = "H-RSTORE" in fits
            info = (f"state page 0x{s:x} non-zero dwords closed {got['closed_state_nz']} after "
                    f"{got['after_state_nz']}; fits {','.join(fits) or 'none'}; pages that "
                    f"differ {page_diff(a, b)}; after: control {nonzero_words(b, c)}; otpm "
                    f"{nonzero_words(b, o)}; state {nonzero_words(b, s)}")
        elif w == 64:
            cw, aw = fmt(words4(a, w, h)), fmt(words4(b, w, h))
            fits = [m for m in ("H-RENDER", "H-CLOSE")
                    if want["closed_words"][m] == cw and want["after_words"][m] == aw]
            state = "H-RENDER" in fits
            info = f"words closed {cw} after {aw}; fits {','.join(fits) or 'none'}"
        else:
            s01 = dwords(b, s, 2)
            v = fmt(s01) if any(s01) else "0x00000000,0x00000000"
            fits = [m for m in ("H-CONST", "H-NONE") if want["after_state01"][m] == v]
            lo, hi = (int(x, 16) for x in want["after_state01"]["H-COUNT"][6:].split("-"))
            if lo <= s01[0] >> 16 <= hi and s01[1]:
                fits.append("H-COUNT")
            state = "H-COUNT" in fits
            info = (f"state words after {v} (U {s01[0] >> 16:#x}); closed "
                    f"{fmt(dwords(a, s, 2))}; fits {','.join(fits) or 'none'}; after: control "
                    f"{nonzero_words(b, c)}; otpm {nonzero_words(b, o)}")
        for m in fits:
            counts[m] = counts.get(m, 0) + 1
        rows.append((group(stage, r), state))      # own2's control is E631's case too: a fit row as well
        lines.append(f"ROW {n} ({r['set']}): {info}: {'held' if state else 'FAILED'}")
    lines.append("FITS: " + (", ".join(f"{m} {k}" for m, k in sorted(counts.items())) or "none"))
    return controls, rows, lines


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        dep = GATES.get(argv[2])
        if dep is None:
            return 0
        print(f"gate {argv[2]}: no gate")
        return 1
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, rows, lines = verdicts(argv[1], argv[2])
        print("\n".join(lines))
        for g in sorted({k for k, _ in rows} or {argv[1]}):
            print(f"SUMMARY: {g}: " + SK.headline(CLAIM.get(g, g), controls,
                                                   [v for k, v in rows if k == g]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
