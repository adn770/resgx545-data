#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""score.py: r19-k0's frozen scorer (stages k0, E1077, and f0, E1078). Every verdict rule comes from
kit/scorekit.py, the kept files are read through kit/kitscore.py (byte copies of resgx545
6809cddd24ce, pinned in FROZEN.commits) and one job through score/read.py.

  score.py STAGE KEPT_DIR [ROOTS...]   CONTROL, ROW, READING lines, MODEL tallies, SUMMARY lines
  score.py gate STAGE ROOTS...         exit 0 when every control of GATES[STAGE] passed (f0 on k0)
  score.py premise STAGE KEPT_DIR      STOP lines and exit 1 when a control has no reading

A row is scored when its job completed (kitscore.completed). Its CTL values are its control's
(PASS only when every one holds); a model's rows are scored only when every control of the stage
passed (scorekit.gate), else cannot tell. Values: 0x.. or decimal, `a|b` (either), `>=N`, a
sha256 (a 16-digit prefix for the hooks' dsha), pb words `0xTA,0xZLS,0xGLOBAL,0xPDS`, and
`same: ROW` (every geometry dump both jobs wrote is byte-identical, and ovf1, knob agree).

k0 and kg models: H-SAME (the kept twin's value, kg: t10's; H-DIFF is its failure), H-E625 (kg:
TA3DCtl dwords 35, 37, 38 at snapshot 1 of the geometry kick). k0's file readings (dsha, param,
tadata) are the hooks' 16-digit prefixes in readings.tsv: the controls' only. f0 models: H-UPD, H-IGN, H-LATE (thr2, ovf2, nparts),
H-STORE against H-NOSTORE (pb2), H-STICK (f0-back). f0-geo (H-GEO0 against H-LIST, 0 jobs): the
geometry kick of f0-up-1/2 (a list of 0x100 pages, TA threshold 0x110) against k0-geo-t18b-1's (P
0x28, 0x38): knob, ovf1, the partial renders before the final (0x0658 stretches up to snapshot 1
are not separable, so the kick's d35, d37, d38) equal; read from kg of the same attempt (a ROOT, or
KEPT_DIR's sibling kg/).

REQUIRED: the files each stage's scorer requires of every row (the others are read when there,
cannot tell when not); read_files(STAGE, DIR) reads exactly what score() reads; producible(row)
is the set of reading keys a row's job can produce (run/hooks.sh's words)."""
import collections
import os
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "gen"))
import kitscore as K  # noqa: E402
import scorekit as SK  # noqa: E402
import read as R  # noqa: E402
import plan as PL  # noqa: E402

STAGES = PL.STAGES
BASE = (".txt", "cases.tsv", "void.tsv", "readings.tsv")
# every row of a stage writes its stage's files: k0's are read by the hooks (readings.tsv)
REQUIRED = {"k0": BASE,
            "kg": BASE + (".words.1.txt", ".ta3d.1.bin", ".tri.param.bin", ".tri.tadata.bin"),
            "f0": BASE + (".words.2.txt", ".ta3d.1.bin")}
GATES = {"kg": ("k0",), "f0": ("k0", "kg")}
HOOKED = ("dsha", "param", "tadata")      # a control's file readings, from readings.tsv
MODELS = {"k0": ("H-SAME",), "kg": ("H-SAME", "H-E625"),
          "f0": ("H-UPD", "H-IGN", "H-LATE", "H-STORE", "H-NOSTORE", "H-STICK")}
GEO_KEYS = ("knob", "ovf1", "d35", "d37", "d38")


def producible(row):
    """The hooks' words a row's job can give (score/read.py words)."""
    a = row["args"]
    keys = set()
    if row["tool"] == "rt":
        keys |= {"nparts", "knob"}
    if a.split(" -- ")[-1].split()[1:2] == ["probe"] and "--dump-render" in a:
        keys |= {"param", "tadata"}
    if " tri " in f" {a} " or a.startswith("tri "):
        keys |= {"drawn", "ovf1"}
        if "--depth-store" in a:
            keys |= {"dst", "dsha"}
        if "--geometry" in a:
            n = int(a.split(" -n ")[1].split()[0])
            keys |= {f"ovf{k}" for k in range(1, n + 1)} | {f"thr{k}" for k in range(1, n + 1)}
    return keys


def allowed(stage):
    return {f for f in REQUIRED[stage] if f.startswith(".")}


def readings(stage, d):
    cases = K.rows(d, "cases.tsv")
    hooked = K.readings(d)
    out = {}
    for r in K.table(KP, stage):
        c = cases.get(r["name"])
        if c is None or not K.completed(c):
            out[r["name"]] = None
            continue
        rd = R.reading(d, r["name"], allowed(stage))
        for k in HOOKED:
            if hooked.get(r["name"], {}).get(k):
                rd[k] = hooked[r["name"]][k]
        out[r["name"]] = rd
    return out


def _num(s):
    return int(s, 0)


def holds(q, got, want, rds=None, rd=None):
    """Whether `got` (the reading of q) is the frozen `want`; None when unread."""
    if q == "same":
        other = (rds or {}).get(want)
        if rd is None or other is None:
            return None
        common = set(rd["dumps"]) & set(other["dumps"])
        if not common:
            return None
        return all(rd["dumps"][f] == other["dumps"][f] for f in common) and \
            rd.get("ovf1") == other.get("ovf1") and rd.get("knob") == other.get("knob")
    if got is None:
        return None
    if isinstance(got, str):
        if q in HOOKED:         # the hooks keep 16 digits, a frozen value may give all 64
            return want.startswith(got) if len(got) < len(want) else got.startswith(want)
        return got == want
    if want.startswith(">="):
        return got >= _num(want[2:])
    return got in {_num(x) for x in want.split("|")}


def show(v):
    if isinstance(v, int):
        return f"0x{v:x}" if v > 9 else str(v)
    if isinstance(v, str) and len(v) == 64:
        return v[:16] + "..."
    return str(v)


def verdicts(stage, d):
    rows = K.table(KP, stage)
    preds = K.predictions(KP, stage)
    rds = readings(stage, d)
    controls, lines = {}, []
    for r in rows:
        if r["set"] != "control":
            continue
        n, rd = r["name"], rds[r["name"]]
        want = {q: by["CTL"] for q, by in preds[n].items() if "CTL" in by}
        sts = {q: holds(q, None if rd is None else rd.get(q), v, rds, rd) for q, v in want.items()}
        st = None if rd is None or any(s is None for s in sts.values()) else all(sts.values())
        controls[n] = st
        lines.append(f"CONTROL {n}: " + ", ".join(
            f"{q} {show(None if rd is None else rd.get(q))} (frozen {v})" for q, v in want.items())
            + ": " + ("PASS" if st else "FAILED" if st is False else "cannot tell"))
    g = SK.gate(controls)
    tallies = collections.defaultdict(list)
    for r in rows:
        n, rd = r["name"], rds[r["name"]]
        for q, by in preds[n].items():
            for mdl, want in by.items():
                if mdl == "CTL":
                    continue
                st = holds(q, None if rd is None else rd.get(q), want, rds, rd)
                st = st if g.ok else None
                tallies[mdl].append(st)
                lines.append(f"ROW {n} [{mdl}, {r['set']}]: "
                             f"{'held' if st else 'FAILED' if st is False else 'cannot tell'}: "
                             f"{q} {show(None if rd is None else rd.get(q))} (frozen {want})")
    for r in rows:
        rd = rds[r["name"]]
        if rd is None:
            lines.append(f"READING {r['name']}: none")
            continue
        keys = [k for k in ("nparts", "knob", "ovf1", "ovf2", "ovf3", "thr1", "thr2", "thr3",
                            "pb0", "pb1", "pb2", "pb3", "d35", "d37", "d38", "drawn", "dst",
                            "jobfail") if rd.get(k) is not None]
        tl = ",".join(f"0x{x:x}" for x in rd.get("tl624", []))
        lines.append(f"READING {r['name']}: " + " ".join(f"{k} {show(rd[k])}" for k in keys)
                     + (f" tl624 {tl}" if tl else ""))
    return controls, lines, dict(tallies), rds


def kg_dir(d, roots):
    for root in roots:
        if os.path.isdir(os.path.join(root, "kg")):
            return os.path.join(root, "kg")
    sib = os.path.join(os.path.dirname(os.path.abspath(d)), "kg")
    return sib if os.path.isdir(sib) else None


def geo0(d, roots, rds):
    """f0-geo: (state, lines). H-GEO0 holds when both f0-up rows equal k0-geo-t18b-1 at GEO_KEYS."""
    kg = kg_dir(d, roots)
    if kg is None:
        return None, ["ROW f0-geo [H-GEO0, control]: cannot tell: no kg of this attempt"]
    c = K.rows(kg, "cases.tsv").get("k0-geo-t18b-1")
    ref = R.reading(kg, "k0-geo-t18b-1", allowed("kg")) if c is not None and K.completed(c) else None
    sts, lines = [], []
    for n in ("f0-up-1", "f0-up-2"):
        rd = rds.get(n)
        if rd is None or ref is None:
            sts.append(None)
            continue
        diff = [k for k in GEO_KEYS if rd.get(k) != ref.get(k)]
        sts.append(not diff)
        lines.append(f"ROW f0-geo {n} [H-GEO0, control]: {'held' if not diff else 'FAILED'}: "
                     + ", ".join(f"{k} {show(rd.get(k))}/{show(ref.get(k))}" for k in GEO_KEYS))
    st = None if any(s is None for s in sts) else all(sts)
    return st, lines or ["ROW f0-geo [H-GEO0, control]: cannot tell"]


def main(argv):
    if len(argv) >= 3 and argv[1] == "gate":
        for dep in GATES.get(argv[2], ()):
            d = next((os.path.join(r, dep) for r in argv[3:] if os.path.isdir(os.path.join(r, dep))),
                     None)
            if d is None:
                print(f"gate {argv[2]}: {dep} has not run")
                return 1
            g = SK.gate(verdicts(dep, d)[0])
            print(f"gate {argv[2]} on {dep}: {'open' if g.ok else '; '.join(g.problems)}")
            if not g.ok:
                return 1
        return 0
    if len(argv) == 4 and argv[1] == "premise":
        stops = K.premise(KP, argv[2], argv[3])
        print("\n".join(stops) if stops else f"premise {argv[2]}: every control read")
        return 1 if stops else 0
    if len(argv) >= 3 and argv[1] in REQUIRED:
        st, d = argv[1], argv[2]
        controls, lines, tallies, rds = verdicts(st, d)
        print("\n".join(lines))
        for mdl in MODELS[st]:
            if mdl in tallies:
                print(f"MODEL {mdl}: {SK.tally(tallies[mdl])}")
        claim = {"k0": "knob 0 runs B60AB0B4's jobs (the kept twins' readings)",
                 "kg": "the geometry kick at P 0x28 overflows, 0x0624 0x6, on t10 and t18b",
                 "f0": "the final job's 0x0624 reads N - 0x22 (the TA command's thresholds)"}[st]
        print(f"SUMMARY: {st}: " + SK.headline(claim, controls, [True] if controls else []))
        for mdl in MODELS[st]:
            if mdl in tallies:
                print(f"SUMMARY: {st}: {mdl}: " + SK.headline(f"{mdl} holds", controls, tallies[mdl]))
        if st == "f0":
            gs, gl = geo0(d, argv[3:], rds)
            print("\n".join(gl))
            print("SUMMARY: f0: H-GEO0: " + SK.headline("the longer list leaves the geometry kick as it "
                                                        "was", controls, [gs]))
        return 0
    print(__doc__)
    return 2


def read_files(stage, d):
    """Exactly the files score() reads in the kept directory."""
    cases = K.rows(d, "cases.tsv")
    K.rows(d, "void.tsv")
    K.text(d, "readings.tsv")
    for n in cases:
        for f in R.files_of(n, allowed(stage)):
            R.raw(d, f)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
