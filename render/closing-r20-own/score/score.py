#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r20-own's scorer (closing20/plan/rank-round20.md section 4: ow and owt for Q191,
E1091; owp for Q192, E1092). Every verdict rule comes from kit/scorekit.py, the kept files are read
through kit/kitscore.py (byte copies of resgx545 c0f8c41fbbf9, pinned in FROZEN.commits).

  score.py STAGE KEPT_DIR [ROOTS...]   ROW and CONTROL lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

The kept TA data copies (t18b --kept-copy): NAME.kept.closed.1.bin (right after the first
context's early close) and NAME.kept.1.bin (after the second context's render). Pages by the
fork's layout (r19-own1b's layout(): 1024x768 control 4, OTPM 5, state 6). Pages are compared by
dword (every non-zero dword of the page and its index; never a hash of a buffer). An empty copy
right after the close makes its row cannot tell (E1085), never a pass or a failure.

ow: H-SECOND (pages 4 to 6 after = E1087's) against H-OWNER (the non-zero lists 0 to 15 of page 6
= the moved owner's cover). owt: the order of 0x062c's owner state base with a task write against
the second context's task writes (H-TA, H-END) [infer]. owp: H-REGIME by the owner's regime read
from NAME.ta3d.101.bin dword 38 (raised iff non-zero): raised zero, not raised E627 lists (P 0x30
unmoved: E1084's dwords exactly); owp-30m also H-SECOND against H-OWNER (group owpw).

REQUIRED: the files each stage's scorer reads; read_files(STAGE, DIR) reads exactly what score()
reads; producible(row) is the set of reading keys a row's job can produce."""
import os
import struct
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

PER_ROW = (".txt", ".kept.closed.1.bin", ".kept.1.bin", ".words.101.txt", ".ta3d.101.bin")
REQUIRED = {s: PER_ROW + ("cases.tsv", "void.tsv", "readings.tsv") for s in ("ow", "owt", "owp")}
GATES = {}          # no stage gates another (ow-c voids ow's own headline when it fails)
PAGE = 4096
SIZE = 0x11000      # 1024x768, the fork's layout (E1087: 69632 bytes)
STATE, PAGES = 6, (4, 5, 6)
CLAIM = {"ow": "H-SECOND: the kept owner's lists after the second render are the second "
               "context's scene, not the owner's (Q191)",
         "owt": "H-TA: the owner's state base is stored with a task write before the second "
                "context's last task write (Q191, which kick) [infer]",
         "owp": "H-REGIME: the owner's state page after the second render is zero iff its kick "
                "is raised, E627 lists otherwise, a repeat at 0x30 (Q192)",
         "owpw": "H-SECOND: a moved owner at 0x30 keeps the second context's lists (Q192)"}


def tool_args(args):
    """the wrapped tool's argv (after regtimeline's `--` and the tool's path)"""
    a = args.split()
    return a[a.index("--") + 2:] if "--" in a else a


def producible(row):
    a = tool_args(row["args"])
    if a[:1] == ["tri"] and "--ctx2" in a and "--kept-copy" in a and "--close-first-early" in a:
        return {"ovf", "kept", "size"}
    return {"ovf"} if a[:1] == ["tri"] else set()


def arg(args, name, default=None):
    a = tool_args(args)
    return a[a.index(name) + 1] if name in a else default


def kept(d, n, which):
    return K._read(os.path.join(d, f"{n}.kept.{which}1.bin"))


def page_words(b, p):
    if b is None or len(b) < (p + 1) * PAGE:
        return None
    return struct.unpack_from("<1024I", b, p * PAGE)


def pages(b, which):
    """the predictions' form: 'pN:i=0x...,...;pM:...' (non-zero dwords with their index)"""
    out = []
    for p in which:
        ws = page_words(b, p)
        if ws is None:
            return None
        out.append(f"p{p}:" + ",".join(f"{i}=0x{x:08x}" for i, x in enumerate(ws) if x))
    return ";".join(out)


def lists(ws):
    """the macrotile lists 0 to 15 (pairs) that are non-zero, and entry 16"""
    return [m for m in range(16) if ws[2 * m] or ws[2 * m + 1]]


def e627(ws):
    """every non-zero pair (count << 16 | head, tail) is a list: count >= 1, count 1 => head ==
    tail; and at least one"""
    got = 0
    for m in range(17):
        a, t = ws[2 * m], ws[2 * m + 1]
        if not a and not t:
            continue
        if a >> 16 < 1 or (a >> 16 == 1 and (a & 0xffff) != t):
            return False
        got += 1
    return got > 0 and not any(ws[34:])


def raised(d, n):
    b = K._read(os.path.join(d, f"{n}.ta3d.101.bin"))
    if b is None or len(b) < 39 * 4:
        return None
    return struct.unpack_from("<I", b, 38 * 4)[0] != 0


def owner_base(d, n):
    for ln in (K.text(d, n + ".words.101.txt") or "").splitlines():
        if ln.startswith("rtds:11="):
            return int(ln.split("=")[1], 16)
    return None


def timeline(text):
    """regtimeline's samples: (regs, [(t, {reg: value})])"""
    regs, out = None, []
    for ln in (text or "").splitlines():
        s = ln.split()
        if ln.startswith("timeline: regs "):
            regs = [int(x, 16) for x in s[2:s.index("samples")]]
        elif regs and s[:1] == ["tl"] and len(s) == 2 + len(regs):
            out.append((int(s[1]), dict(zip(regs, (int(x, 16) for x in s[2:])))))
    return regs, out


def kick(text, base):
    """'ta', 'end' or why it cannot tell: 0x062c's owner state base O (words.101 rtds:11) with a
    task write (0x0694 or 0x0698 changing in that sample) after the first sample with another
    non-zero state base (the second context's [infer]), against the task writes under that
    other base after it"""
    regs, tl = timeline(text)
    if not tl or not regs or not {0x62c, 0x694, 0x698} <= set(regs):
        return "cannot tell (no timeline of 0x062c, 0x0694, 0x0698)"
    if base is None:
        return "cannot tell (no owner state base in words.101)"
    first = next((i for i, (_, v) in enumerate(tl) if v[0x62c] not in (0, base)), None)
    if first is None:
        return "cannot tell (no other state base seen)"
    tw = [i for i in range(1, len(tl))
          if (tl[i][1][0x694], tl[i][1][0x698]) != (tl[i - 1][1][0x694], tl[i - 1][1][0x698])]
    own = next((i for i in tw if i > first and tl[i][1][0x62c] == base), None)
    if own is None:
        return "cannot tell (no task write under the owner's state base after the other's)"
    later = [i for i in tw if i > own and tl[i][1][0x62c] not in (0, base)]
    return "ta" if later else "end"


def premise_row(r, case, d):
    """None when the job ran and both copies are 69632 bytes, else why not (cannot tell)"""
    if not case or not K.completed(case):
        return "the job did not complete"
    for which in ("closed.", ""):
        b = kept(d, r["name"], which)
        if b is None or len(b) != SIZE:
            n = "missing" if b is None else f"{len(b)} bytes"
            return f"kept.{which}1.bin {n} (want {SIZE}; an empty copy after the close: E1085)"
    return None


def control_state(r, case, d, rd, want):
    got = rd.get(r["name"], {})
    if got.get("kept") not in (None, "", "-", "2"):
        return None, f"kept {got['kept']} of 2 copies (an empty copy: cannot tell, E1085)"
    for q in r["reads"]:
        g = got.get(q)
        if g in (None, "", "-"):
            return None, f"{q} not read"
        if g != want.get(q, {}).get("CTL"):
            return False, f"{q} {g} (frozen {want.get(q, {}).get('CTL')})"
    why = premise_row(r, case, d)
    if why:
        return None, why
    for q, which, pg in (("closed_pages", "closed.", PAGES), ("after_pages", "", PAGES),
                         ("after_state", "", (STATE,))):
        if q in want and pages(kept(d, r["name"], which), pg) != want[q]["CTL"]:
            return False, f"{q} not as frozen (dword for dword)"
    return True, "premise read as frozen, its pages as frozen"


def score_ow(r, d, want):
    b = kept(d, r["name"], "")
    ws = page_words(b, STATE)
    ls = lists(ws)
    fits = []
    if pages(b, PAGES) == want["after_pages"]["H-SECOND"]:
        fits.append("H-SECOND")
    if ",".join(map(str, ls)) == want["lists"]["H-OWNER"]:
        fits.append("H-OWNER")
    tot = sum(ws[2 * m] >> 16 for m in ls)
    return "H-SECOND" in fits, fits, (f"lists {','.join(map(str, ls)) or 'none'} (counts sum "
                                      f"{tot}), entry 16 0x{ws[32]:08x}")


def score_owp(r, d, want):
    """(state for owp, fits, info, state for owpw or 'none')"""
    b = kept(d, r["name"], "")
    ws = page_words(b, STATE)
    rz = raised(d, r["name"])
    s6 = pages(b, (STATE,))
    fits, w2 = [], "none"
    if rz is None:
        return None, fits, "regime not read (ta3d.101.bin)", w2
    pv = want["plain_state"]["H-REGIME"]
    if rz:
        ok = s6 == want["raised_state"]["H-REGIME"]
    elif pv == "lists":
        ok = e627(ws)
    else:
        ok = s6 == pv
    if ok:
        fits.append("H-REGIME")
    if "whose" in want:
        sec = s6 == want["whose"]["H-SECOND"]
        cov = {int(x) for x in want["whose"]["H-OWNER"].split(":")[1].split(",")}
        own = not sec and bool(lists(ws)) and set(lists(ws)) <= cov
        fits += ["H-SECOND"] * sec + ["H-OWNER"] * own
        w2 = sec
    cl = page_words(kept(d, r["name"], "closed."), STATE)
    info = (f"{'raised' if rz else 'not raised'}; after: {s6}; lists "
            f"{','.join(map(str, lists(ws))) or 'none'}; closed copy lists "
            f"{','.join(map(str, lists(cl))) or 'none'}")
    return ok, fits, info, w2


def verdicts(stage, d):
    preds = K.predictions(KP, stage)
    cases = K.rows(d, "cases.tsv")
    rd = K.readings(d)
    controls, rows, lines, counts = {}, [], [], {}
    for r in K.table(KP, stage):
        n = r["name"]
        case = cases.get(n)
        want = preds.get(n, {})
        if r["set"] == "control":
            st, why = control_state(r, case, d, rd, want)
            controls[n] = st
            lines.append(f"CONTROL {n}: {why}: "
                         f"{'PASS' if st else 'FAILED' if st is False else 'cannot tell'}")
            if stage == "ow":       # ow-c is a control only; owt-a and owp-30-a are fit rows too
                continue
        why = premise_row(r, case, d)
        if why:
            rows.append((stage, None))
            lines.append(f"ROW {n}: cannot tell ({why})")
            continue
        k = kick(K.text(d, n + ".txt"), owner_base(d, n))
        if stage == "ow":
            state, fits, info = score_ow(r, d, want)
            info += f"; kick reading {k}"
        elif stage == "owt":
            state = {"ta": True, "end": False}.get(k)
            fits = {"ta": ["H-TA"], "end": ["H-END"]}.get(k, [])
            ref = K.predictions(KP, "ow")["ow-c"]["after_pages"]["CTL"]
            info = f"kick {k}; pages 4 to 6 E1087's: {pages(kept(d, n, ''), PAGES) == ref}"
        else:
            state, fits, info, w2 = score_owp(r, d, want)
            info += f"; kick reading {k}"
            if w2 != "none":
                rows.append(("owpw", w2))
        for m in fits:
            counts[m] = counts.get(m, 0) + 1
        rows.append((stage, state))
        lines.append(f"ROW {n} ({r['set']}): {info}; fits {','.join(fits) or 'none'}: "
                     f"{'held' if state else 'FAILED' if state is False else 'cannot tell'}")
    lines.append("FITS: " + (", ".join(f"{m} {k}" for m, k in sorted(counts.items())) or "none"))
    return controls, rows, lines


def read_files(stage, d):
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.readings(d)
    for n in cases:
        K.text(d, n + ".txt")
        K.text(d, n + ".words.101.txt")
        K._read(os.path.join(d, f"{n}.ta3d.101.bin"))
        kept(d, n, "closed.")
        kept(d, n, "")


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        if GATES.get(argv[2]) is None:
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
