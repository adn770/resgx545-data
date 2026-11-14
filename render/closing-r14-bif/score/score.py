#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r14-bif's scorer. Every verdict rule comes from kit/scorekit.py, the kept files are
read through kit/kitscore.py (byte copies of resgx545 c58f9f9c87aa, pinned in FROZEN.commits);
the kept records it compares with are read at the frozen data commit (gen/pins.py).

  score.py refill KEPT_DIR [ROOTS...]  ROW, CONTROL and READING lines, then SUMMARY lines (exit 0)
  score.py gate STAGE ROOTS...         exit 0 (no stage gates another)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

refill: render N's store (NAME.depth-store.N.bin) is classed by gen/rf.store_class: F (the index
render 1 loaded), V (the refill), clear (1.0), mixed or other. A held-out row holds a model when
its store 2 is the model's class; its premise is store 1 F (else cannot tell), and the tool's
buffers at gen/rf's addresses (else cannot tell). Controls: rf-c-plain both renders exact
(`tri: 2 renders ok`) and each store 4096 changed (E965's tri-c-depth); rf-c-depth both stores
byte for byte E1029's zb-c-id dump; rf-c-unread store 1 byte for byte E1029's zb-c-off dump and
store 2 V. READING lines: each row's store classes, `depth #2` changed (against V on a refill
row: 0 means the host's write held) and the kernel's PTE line.

REQUIRED: the files the scorer reads; read_files(STAGE, DIR) reads exactly what verdicts() reads;
producible(row) is the set of reading keys a row's job can produce."""
import os
import re
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402

REQUIRED = {"refill": (".txt", ".dmesg", ".depth-store.1.bin", ".depth-store.2.bin", "cases.tsv",
                       "void.tsv", "readings.tsv")}
GATES = {}


def producible(row):
    a = row["args"].split()
    keys = {"job", "renders"} if a[:1] == ["tri"] else set()
    if "--depth" in a:
        keys |= {"dep1", "dep2"}
    if "--depth-store" in a:
        keys |= {"dst1", "dst2"} if "-n" in a and a[a.index("-n") + 1] == "2" else {"dst1"}
    return keys


def changed(text, what, n):
    m = re.search(r"^%s #%d: \d+ dwords, (\d+) changed" % (what, n), text or "", re.M)
    return int(m.group(1)) if m else None


def renders(text):
    m = re.findall(r"^tri: (?:(\d+) renders ok|(\d+) of (\d+) renders ok)$", text or "", re.M)
    if not m:
        return None
    a, b, c = m[-1]
    return f"{a}ok" if a else f"{b}of{c}"


def jobs_ok(text):
    j = re.findall(r"^job: (.*)$", text or "", re.M)
    return bool(j) and all(x == "ok" for x in j)


def addresses_ok(text):
    import rf as R
    t = text or ""
    return (f"depth: {R.DEPTH:#010x} {R.PAGES} pages," in t and f"base {R.BASE:#010x}," in t
            and f"depth store: {R.STORE:#010x} {R.PAGES} pages" in t)


def pte_line(dmesg):
    import rf as R
    m = re.search(r"vm_map %#010x \+0x[0-9a-f]+: PTE flags (0x[0-9a-f]+)" % R.DEPTH, dmesg or "")
    return m.group(1) if m else None


def kept(key):
    import pins
    import rf as R
    return pins.blob(R.KEPT[key])


def _st(s):
    return "PASS" if s else "FAILED" if s is False else "cannot tell"


class Run:
    def __init__(self, stage, d):
        self.d = d
        self.cases = K.rows(d, "cases.tsv")
        K.rows(d, "void.tsv")
        K.rows(d, "readings.tsv")
        self.table = K.table(KP, stage)

    def done(self, n):
        return n in self.cases and K.completed(self.cases[n])

    def text(self, n, suffix=".txt"):
        return K.text(self.d, n + suffix) if self.done(n) else None

    def dump(self, n, r):
        return K._read(os.path.join(self.d, f"{n}.depth-store.{r}.bin")) if self.done(n) else None


def refill(r):
    import rf as R
    controls, per_model, lines = {}, {}, []
    for row in r.table:
        n = row["name"]
        txt, dm = r.text(n), r.text(n, ".dmesg")
        b1, b2 = r.dump(n, 1), r.dump(n, 2)
        c1, c2 = R.store_class(R.dwords(b1)), R.store_class(R.dwords(b2))
        pte = pte_line(dm)
        lines.append(f"READING {n}: jobs ok {jobs_ok(txt) if txt is not None else None}; renders "
                     f"{renders(txt)}; store 1 {c1}, store 2 {c2}; depth #2 changed "
                     f"{changed(txt, 'depth', 2)}; PTE line {pte}")
        if n == "rf-c-plain":
            d1, d2 = changed(txt, "depth store", 1), changed(txt, "depth store", 2)
            got = renders(txt)
            s = None if txt is None or got is None or d1 is None or d2 is None else (
                jobs_ok(txt) and got == "2ok" and d1 == d2 == R.PLAIN_CHANGED)
            lines.append(f"CONTROL {n}: renders {got} (frozen 2ok); store changed {d1}, {d2} "
                         f"(frozen {R.PLAIN_CHANGED}): {_st(s)}")
            controls[n] = s
            continue
        if row["set"] == "control":
            ref, want2 = R.CONTROL[n]
            same = None if b1 is None or not addresses_ok(txt) else b1 == kept(ref)
            s = None if same is None or c2 is None else (same and c2 == want2 and jobs_ok(txt))
            lines.append(f"CONTROL {n}: store 1 byte for byte E1029's zb-c-{ref}: {same}; store 2 "
                         f"{c2} (frozen {want2}): {_st(s)}")
            controls[n] = s
            continue
        premise = (txt is not None and jobs_ok(txt) and addresses_ok(txt) and c1 == "F"
                   and ("dbg:vm_pte_flags=0x8" not in row["knobs"] or pte is not None))
        res = {}
        for m, want in R.MODELS[n].items():
            res[m] = None if not premise or c2 is None else c2 == want
            per_model.setdefault(m, []).append(res[m])
        held = [m for m, s in res.items() if s]
        lines.append(f"ROW {n}: store 2 {c2}; " + "; ".join(
            f"{m} {R.MODELS[n][m]}" for m in res) + ": " + (
            f"held {', '.join(held)}" if held else
            "cannot tell" + ("" if premise else " (premise: jobs ok, addresses, store 1 F, "
                             "the PTE line)") if any(s is None for s in res.values()) else
            "no frozen model"))
    return controls, per_model, lines


STAGE_FN = {"refill": refill}


def verdicts(stage, d, roots=None):
    return STAGE_FN[stage](Run(stage, d))


def read_files(stage, d):
    verdicts(stage, d)


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        controls, per_model, lines = verdicts(argv[1], argv[2], argv[3:])
        print("\n".join(lines))
        for m, states in sorted(per_model.items()):
            h = SK.headline(m, controls, states)
            print("SUMMARY: " + argv[1] + ": " + (h if h.startswith(m) else f"{m}: {h}"))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
