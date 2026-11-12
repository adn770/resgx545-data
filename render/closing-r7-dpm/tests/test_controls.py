#!/usr/bin/env python3
"""test_controls.py (plan section 6, R7-6): every gating control is readable by construction and can fail, proven on REAL kept files.
  1. R6-dpm's kept r-a0 jobs are s-a0's six rows (same commands, same P): assembled under our names and scored by score_r7.py against
     OUR frozen predictions, every s-a0 control is HELD and the premise has no STOP;
  2. planted copies of that directory FAIL: c4-b5 and c4-b6 swapped (class and pages left FAILED), g-qf's timeline in a 1500-vertex
     control (scene FAILED), a knob that did not land (FAILED), a control whose partial render was cut from its timeline (NO READING:
     the premise prints a STOP and the headline is never printed: r6-dpm's slip), a control block or a kept output missing (NO READING);
  3. R6-dpm's kept r-k k-b5 and k-b6 (oomring, no page counts) read R-5's bits as our s-k controls (held), and FAIL s-k's premise
     (ring_counts 0: oomring writes no 0x0724/0x072c words), so the premise can fail on real data;
  4. G8: R6-dpm's attempt a2 through this gate: the premise STOPS at a0-cal-2048f grow (no reading by construction); without that one
     control the gate opens and the tallies equal postrun/ungated.out's (r-m H-PHASE 10 held 5 FAILED, E-TL 10/5; r-n H-PHASE 18/0,
     H-STEPMODEL steps 18/0; r-b's count rows as kept);
  5. the generator's refusal: every control of every stage declares readings its job produces; R6's a0-cal-2048f grow is refused.
"""
import csv
import gzip
import os
import pathlib
import re
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True
os.environ["R7_SCORE_NOFREEZE"] = "1"
KP = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KP / "score"), str(KP / "run"), str(KP / "gen")]
import score_r7 as S  # noqa: E402
import r7plan as P  # noqa: E402
import scorekit as SK  # noqa: E402

R6 = pathlib.Path("/Users/jtorra/src/resgx545-data/render/closing-r6-dpm")
FAIL = []


def check(c, what):
    print(("ok   " if c else "FAIL ") + what)
    if not c:
        FAIL.append(what)


tmp = pathlib.Path(tempfile.mkdtemp(prefix="ctl7-", dir=str(KP / "debug")))
T = {r["name"]: r for st in ("s-a0", "s-k") for r in P.tables()[st]}


def assemble(dst, rows):
    """rows: (our name, source dir, source name): copy every kept file under our name; cases.tsv with our table's P, knobs, args."""
    dst.mkdir(parents=True)
    out = []
    for new, sd, sn in rows:
        src = {c["name"]: c for c in csv.DictReader(open(sd / "cases.tsv"), delimiter="\t")}[sn]
        for f in sd.iterdir():
            if f.name.startswith(sn + "."):
                shutil.copy(f, dst / (new + f.name[len(sn):]))
        t = T[new]
        cmd = t["cmd"].replace('"$W/', '"W/').replace('"$S/', '"S/')
        out.append(dict(src, name=new, P=t["P"], knobs=t["knobs"], args=cmd))
    with open(dst / "cases.tsv", "w") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(out)


def score(st, d):
    rows, rd = S._score(st, d, [d])
    return rows, S.stage_verdict(st, rows, rd, d if st != "s-a0" else None)


A0 = R6 / "out/a2/r-a0"
names = ["a0-cal-2048", "a0-cal-2048f", "a0-c4-b5", "a0-c4-b6", "a0-t-s3m6", "a0-qf-0xa2"]
base = tmp / "a0"
assemble(base, [(n, A0, n) for n in names])
rows, v = score("s-a0", base)
ctl = [x for x in rows if x["set"] == "control"]
check(len(ctl) >= 25 and all(x["state"] is True for x in ctl) and "premise holds" in v[0] and "rows decided" in v[0],
      f"R6-dpm's kept r-a0 jobs as s-a0: {sum(x['state'] is True for x in ctl)} of {len(ctl)} controls HELD; {v[0][:60]}")
check(not [x for x in ctl if x["state"] == S.NO_READING], "every s-a0 control has its reading on the kept jobs (none is NO READING)")


def planted(tag, fn):
    d = tmp / tag
    shutil.copytree(base, d)
    fn(d)
    return score("s-a0", d)


def swap(d):
    for f in list(d.iterdir()):
        if f.name.startswith("a0-c4-b5."):
            f.rename(d / ("X" + f.name[len("a0-c4-b5"):]))
    for f in list(d.iterdir()):
        if f.name.startswith("a0-c4-b6."):
            f.rename(d / ("a0-c4-b5" + f.name[len("a0-c4-b6"):]))
    for f in list(d.iterdir()):
        if f.name.startswith("X."):
            f.rename(d / ("a0-c4-b6" + f.name[1:]))


rows, v = planted("swap", swap)
st = {(x["case"], x["quantity"]): x["state"] for x in rows}
check(st[("a0-c4-b5", "cls")] is False and st[("a0-c4-b5", "gps_left")] is False and "controls FAILED" in v[0],
      f"planted: c4-b5 and c4-b6 swapped: class and pages left FAILED ({v[0][:50]})")
rows, v = planted("scene", lambda d: shutil.copy(d / "a0-qf-0xa2.txt.gz", d / "a0-c4-b6.txt.gz"))
check(any(x["case"] == "a0-c4-b6" and x["state"] is False and "scene" in x["why"] for x in rows) and "FAILED" in v[0],
      "planted: g-qf's timeline in a 1500-vertex control: scene FAILED")


def knob(d):
    c = (d / "cases.tsv").read_text().replace("\ta0-c4-b5\t", "\ta0-c4-b5\t")
    rows_ = list(csv.DictReader(open(d / "cases.tsv"), delimiter="\t"))
    for r in rows_:
        if r["name"] == "a0-t-s3m6":
            r["P"] = "0xba"
    with open(d / "cases.tsv", "w") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(rows_)
    return c


rows, v = planted("knob", knob)
check(any(x["case"] == "a0-t-s3m6" and x["state"] is False and "knob did not land" in x["why"] for x in rows), "planted: a knob that did not land: FAILED")


def cut_render(d):
    """the partial render's samples of a0-c4-b6 removed from its timeline: no pages left can be read (the job is otherwise whole)"""
    t = gzip.open(d / "a0-c4-b6.txt.gz").read().decode().splitlines()
    hdr = next(i for i, ln in enumerate(t) if ln.startswith("timeline: regs"))
    regs = [int(x, 16) for x in t[hdr].split()[2:t[hdr].split().index("samples")]]
    i658 = regs.index(0x658)
    keep = [ln for ln in t if not (ln.startswith("tl ") and int(ln.split()[2 + i658], 16) & 1)]
    with gzip.open(d / "a0-c4-b6.txt.gz", "wt") as f:
        f.write("\n".join(keep) + "\n")


rows, v = planted("noread", lambda d: (d / "a0-c4-b6.after.buf09.bin.gz").unlink())
check(any(x["case"] == "a0-c4-b6" and x["quantity"] == "cls" and x["state"] == S.NO_READING for x in rows)
      and v == ["STOP: premise: control a0-c4-b6 has no reading of cls"],
      f"planted: a class control whose control block was not kept: NO READING and a premise STOP, no headline ({v[0][:70]})")
rows, v = planted("cut", cut_render)
check(v[0].startswith("STOP: premise: control a0-c4-b6 has no reading of") and any(x["case"] == "a0-c4-b6" and x["state"] is False for x in rows),
      "planted: a control's partial render cut from its timeline: its scene check FAILS and the premise STOPS")
rows, v = planted("nofile", lambda d: (d / "a0-t-s3m6.after.buf09.bin.gz").unlink() or (d / "a0-t-s3m6.txt.gz").unlink())
check(any(x["case"] == "a0-t-s3m6" and x["state"] == S.NO_READING for x in rows) and v[0].startswith("STOP"),
      f"planted: a control's kept output missing: NO READING, STOP ({v[0][:70]})")
# what the gate does with a NO READING control: it shuts (never a pass), and s-m's headlines are gated, not silently printed
g = SK.gate({"s-a0 a0-c4-b6 gps_left": S.NO_READING})
check(not g.ok and "NODATA" in g.problems[0], "scorekit's gate shuts on a NO READING control (NODATA)")

# 3. R6-dpm's r-k controls as s-k's
K = R6 / "out/a2/r-k"
kd = tmp / "k"
assemble(kd, [("k-b6", K, "k-b6"), ("k-b5", K, "k-b5")])
rows, rd = S._score("s-k", kd, [kd])
st = {(x["case"], x["quantity"], x["model"]): x["state"] for x in rows}
check(st[("k-b5", "dec_sa8_380", "CTL")] is True and st[("k-b6", "dec_sa8_380", "CTL")] is True and st[("k-b5", "cls", "CTL")] is True
      and st[("k-b6", "cls", "CTL")] is True, "R6-dpm's kept k-b5 / k-b6 (oomring): R-5's bits and classes HELD as s-k's controls")
check(st[("k-b6", "ring_counts", "PREMISE")] in (False, S.NO_READING), f"... and s-k's premise FAILS on them: oomring writes no page counts ({st[('k-b6', 'ring_counts', 'PREMISE')]})")
v = S.stage_verdict("s-k", rows, rd, None)
check(any("controls FAILED" in x or "STOP" in x for x in v), f"s-k's headlines are not printed over a failed premise: {v[0][:70]}")

# 4. G8: R6-dpm's attempt through this gate
stops, res = S.replay_r6(R6 / "out/a2")
check(stops == ["STOP: premise: control a0-cal-2048f has no reading of grow"], f"G8: the gate STOPS at r6-dpm's slip: {stops}")
stops2, res = S.replay_r6(R6 / "out/a2", drop={("a0-cal-2048f", "grow")})
check(stops2 == [], "G8: without a0-cal-2048f grow every r-a0 control has its reading (the gate opens)")
un = (R6 / "postrun/ungated.out").read_text()
cur = None
want = {}
for ln in un.splitlines():
    if ln.startswith("== "):
        cur = ln[3:].strip()
        continue
    m = re.match(r"^\s{2}(\S+)\s+(\S+)\s+(\S+)\s+all: (\d+) held, (\d+) FAILED, (\d+) cannot tell of (\d+)", ln)
    if m and cur:
        k = (cur, m.group(1), m.group(2))
        a = want.get(k, (0, 0, 0))
        want[k] = (a[0] + int(m.group(4)), a[1] + int(m.group(5)), a[2] + int(m.group(6)))
for key in [("r-m", "H-PHASE", "gps_left"), ("r-m", "E-TL", "gps_left"), ("r-n", "H-PHASE", "gps_left"), ("r-n", "H-STEPMODEL", "steps"),
            ("r-n", "R-5", "cls"), ("r-m", "H-GREQ", "grow")]:
    st_, m_, q_ = key
    if q_ == "steps":
        t = [v_ for (m2, q2), v_ in res[st_].items() if m2 == m_ and re.fullmatch(r"S\d+", q2)]
        got = (sum(x.held for x in t), sum(x.failed for x in t))
    else:
        x = res[st_].get((m_, q_))
        got = (x.held, x.failed) if x else None
    check(got == want[key][:2], f"G8 ungated {st_} {m_} {q_}: {got} = postrun/ungated.out {want[key][:2]}")

# 5. the generator's refusal on every stage
T_all = P.tables()
probs = SK.control_read_problems(P.control_decls(T_all), P.producible)
check(probs == [], f"every control of every stage declares readings its job produces ({len(P.control_decls(T_all))} controls)")
bad = {"a0-cal-2048f": (("grow",), next(r for r in T_all["s-a0"] if r["name"] == "a0-cal-2048f"))}
check(SK.control_read_problems(bad, P.producible) == ["control a0-cal-2048f reads grow, which its row cannot produce"],
      "R6's a0-cal-2048f grow control is refused by the generator")
shutil.rmtree(tmp)
print(f"{'PASS' if not FAIL else 'FAIL'}: {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
