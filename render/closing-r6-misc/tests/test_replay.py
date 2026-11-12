#!/usr/bin/env python3
"""test_replay.py: every r6-misc scorer replayed BEFORE the freeze on kept records it must hold on and on ones it must fail on (round 6
rule).  The kept files are converted into this session's kept layout (cases.tsv, NAME.txt.gz, NAME.dmesg.gz, NAME.depth.1.bin.gz) in a
temporary directory under debug/, predictions are made for those rows with the frozen models, and the frozen scorers run on them.

  q289  E876's kept sweeps (pds/end-of-tile/values-doutu1-{x,y}/raw.txt, 1536 cases + 2 baselines, the 64 x 32 fill): M-OR and M-ADD
        must match every case (E876: 1536 of 1536), M-XOR must FAIL exactly 4 (E876: 4 of 1536), and since OR and ADD give the same
        image at 64 x 32 the scorer must NOT pick one ("cannot tell: no separating row decided").  A doctored case (one hash changed)
        must make the scorer refute both.
  q287  E831's kept g-z (render/closing-r3-geo-c/out/g-z, the 3 controls and 10 held-out full-screen cells, real depth dumps under
        their real names): the controls must pass (924, 924, 3444) and the frozen reader must give E831's verdicts: rule A and FLOOR
        10 of 10, ROUND and CEIL refuted 10 of 10, RSTRICT refuted in 6 of 10.  A dump renamed as round 4's slip did must be cannot
        tell (never a pass).
  q086  E511's 6 kept jobs (ta/mtile-msaa-risky) with E507's kept 128 x 64 R (ta/mtile-msaa) as the control: H-COV must hold 6 of 6
        (post hoc, as models.py says) and H-ANY must be refuted by the 3 HS faults (3D side, 0x90100 at 0x10000016, 0x10000012,
        0x10000013 in the kept kernel log).
  python3 tests/test_replay.py
"""
import gzip
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(KP, "score"), os.path.join(KP, "gen")]
import models as M  # noqa: E402
import score_m as S  # noqa: E402

DATA = "/Users/jtorra/src/resgx545-data"
os.makedirs(os.path.join(KP, "debug"), exist_ok=True)
T = tempfile.mkdtemp(prefix="replay.", dir=os.path.join(KP, "debug"))
bad = n = 0
HDR = "name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_req\tfault_word\tfree_kb\n"


def check(cond, what):
    global bad, n
    n += 1
    print(("ok   " if cond else "FAIL ") + what)
    bad += 0 if cond else 1


def gz(path, data):
    with gzip.open(path, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode())


# ---- q289 ------------------------------------------------------------------------------------------------------------------
def q289_kept(d, doctor=None):
    os.makedirs(d)
    P, cases = {}, [HDR]
    for ax in ("x", "y"):
        txt = open(DATA + "/pds/end-of-tile/values-doutu1-%s/raw.txt" % ax).read()
        for blk in txt.split("=== case ")[1:]:
            label = blk.split("\n", 1)[0].strip()
            m = re.match(r"pds:pixev:12\^=(0x[0-9a-f]+)$", label)
            v = int(m.group(1), 16) if m else 0
            name = "%s-%s" % (ax, label.replace(":", "_").replace("^=", "-"))
            body = blk.split("\n--- stderr")[0]
            rc = int(re.search(r"^--- rc (\d+)", blk, re.M).group(1))
            if doctor == name:
                body = re.sub(r"hash 0x[0-9a-f]+", "hash 0x0000000000000001", body)
            gz(os.path.join(d, name + ".txt.gz"), body)
            sset = "control" if label == "baseline" else "heldout"
            p = {"set": sset, "size": {"all": "64x32"}, "separates": {"OR-vs-ADD": "no"}, "hash": {}}
            for op in ("OR", "ADD", "XOR"):
                p["hash"]["M-" + op] = "0x%016x" % M.fill_predict(64, 32, ax, M.poke_field(ax, v) if v else 0, op)[0]
                assert p["hash"]["M-OR"] == p["hash"].get("M-ADD", p["hash"]["M-OR"])
            P[name] = p
            cls = "ok" if "job: ok" in body else "fail"
            cases.append("\t".join([name, "q289", sset, "safe", "expectdiff needhash", "t4", label, str(rc), cls, "-", "-", "0"]) + "\n")
    open(os.path.join(d, "cases.tsv"), "w").writelines(cases)
    return P


P = q289_kept(os.path.join(T, "q289"))
text, summ = S.score_q289(S.Kept(os.path.join(T, "q289")), P)
held = {m: re.search(r"^%s on the held-out rows: (.*)$" % m, text, re.M).group(1) for m in ("M-OR", "M-ADD", "M-XOR")}
check(len(P) == 1536, "q289 replay: 1536 kept cases read (511 x + 1023 y pokes, 2 baselines)")
check(held["M-OR"] == "1534 held, 0 FAILED, 0 cannot tell of 1534" and held["M-ADD"] == held["M-OR"],
      "q289 replay: M-OR and M-ADD hold on every kept poke case (%s), the baselines are the controls (E876: 1536 of 1536)" % held["M-OR"])
check(held["M-XOR"] == "1530 held, 4 FAILED, 0 cannot tell of 1534", "q289 replay MUST FAIL: M-XOR fails 4 (E876: 4 of 1536): %s" % held["M-XOR"])
check(summ == "Q289: cannot tell: no separating row decided", "q289 replay: on the 64 x 32 fill the scorer does not pick OR or ADD: %s" % summ)
P2 = q289_kept(os.path.join(T, "q289d"), doctor="x-pds_pixev_12-0x10")
P2["x-pds_pixev_12-0x10"]["separates"]["OR-vs-ADD"] = "yes"          # let the doctored row decide
t2, s2 = S.score_q289(S.Kept(os.path.join(T, "q289d")), P2)
check("M-OR refuted" in s2 and "M-ADD refuted" in s2 and "off both models: 1" in s2, "q289 replay MUST FAIL: one doctored hash refutes both models: %s" % s2)


# ---- q287 ------------------------------------------------------------------------------------------------------------------
G = DATA + "/render/closing-r3-geo-c/out/g-z"
E831_CTL = {"z-ctl-34x18-x": 924, "z-ctl-34x18-y": 924, "z-ctl-66x34-x": 3444}


def q287_kept(d, rename=None):
    os.makedirs(d)
    P, cases = {}, [HDR]
    lines = open(os.path.join(G, "cases.tsv")).read().splitlines()
    hdr = lines[0].split("\t")
    for ln in lines[1:]:
        c = dict(zip(hdr, ln.split("\t")))
        a = c["args"]
        if "--tri-full" not in a:
            continue                                          # the two --tri-v single triangles: not this session's shape
        w, h = int(re.search(r"--width (\d+)", a).group(1)), int(re.search(r"--height (\d+)", a).group(1))
        name = c["name"]
        for suf in (".txt.gz", ".dmesg.gz", ".depth.1.bin.gz"):
            src = os.path.join(G, name + suf)
            dst = os.path.join(d, name + (".depth.tri.bin.gz" if (suf == ".depth.1.bin.gz" and rename == name) else suf))
            if os.path.exists(src):
                shutil.copy(src, dst)
        if not os.path.exists(os.path.join(d, name + ".err.gz")):
            gz(os.path.join(d, name + ".err.gz"), "")
        sset = "control" if name in E831_CTL else "heldout"
        p = {"set": sset, "size": {"all": "%dx%d" % (w, h)}, "stored_set_sha": {}, "stored_count": {},
             "separates": {"A-vs-FLOOR": "no"}}
        for r in M.G.RULES:
            p["stored_set_sha"][r] = M.set_sha(M.band(r, w, h))
        if sset == "control":
            p["stored_count"]["E831"] = str(E831_CTL[name])
        P[name] = p
        cases.append("\t".join([name, "q287", sset, "safe", "expectdiff", "t4", a, c["rc"], c["class"], "-", "-", "0"]) + "\n")
    open(os.path.join(d, "cases.tsv"), "w").writelines(cases)
    return P


P = q287_kept(os.path.join(T, "q287"))
text, summ = S.score_q287(S.Kept(os.path.join(T, "q287")), P)
held = {r: re.search(r"^rule %-7s fit .* \| held out (.*) \| confirm" % r, text, re.M).group(1) for r in M.G.RULES}
check(len(P) == 13 and "controls pass" in summ, "q287 replay: E831's 3 controls (924, 924, 3444) pass with the frozen reader on the real dumps")
check(held["A"] == "10 held, 0 FAILED, 0 cannot tell of 10" and held["FLOOR"] == held["A"], "q287 replay: rule A and FLOOR hold 10 of 10 (E831): %s" % held["A"])
check(held["ROUND"] == "0 held, 10 FAILED, 0 cannot tell of 10" and held["CEIL"] == held["ROUND"], "q287 replay MUST FAIL: ROUND and CEIL refuted 10 of 10 (E831)")
check(held["RSTRICT"] == "4 held, 6 FAILED, 0 cannot tell of 10", "q287 replay MUST FAIL: RSTRICT refuted in 6 of 10 (E831): %s" % held["RSTRICT"])
P = q287_kept(os.path.join(T, "q287r"), rename="z-w36")
text, summ = S.score_q287(S.Kept(os.path.join(T, "q287r")), P)
check(re.search(r"^z-w36 .*depth dump missing", text, re.M) is not None and "rule A held on the held-out cells (9 of 9)" in summ,
      "q287 replay: a dump under another name (round 4's t slip) is cannot tell for that row, never a pass (A 9 of 9)")


# ---- q086 ------------------------------------------------------------------------------------------------------------------
def q086_kept(d):
    os.makedirs(d)
    P, cases = {}, [HDR]
    words = re.findall(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)", open(DATA + "/ta/mtile-msaa-risky/kernel.log").read())
    rows = [("q086-128x64-R", "control", 128, 64, {}, DATA + "/ta/mtile-msaa/dumps/q086-128x64-R.txt.gz")]
    for ln in open(DATA + "/ta/mtile-msaa-risky/cases.tsv").read().splitlines()[1:]:
        name, sset, w, h, args = ln.split("\t")
        kp = {int(i): int(v, 16) for i, v in re.findall(r"1:ta:(\d+)=(0x[0-9a-f]+)", args)}
        rows.append((name, "heldout", int(w), int(h), kp, DATA + "/ta/mtile-msaa-risky/dumps/%s.txt.gz" % name))
    wi = iter(words)
    for name, sset, w, h, kp, src in rows:
        shutil.copy(src, os.path.join(d, name + ".txt.gz"))
        with gzip.open(src, "rt") as f:
            txt = f.read()
        cls, fi, fw = ("fault",) + (lambda v: (str(int(v[0], 16) & 0xFFFF), v[1]))(next(wi)) if "faulted" in txt else ("ok", "-", "-")
        P[name] = {"set": sset, "size": {"all": "%dx%d" % (w, h)}, "cover": {"H-COV": "-"},
                   "class": {"H-COV": "ok" if M.hcov_completes(w, h, kp) else "fault", "H-ANY": "ok"}}
        cases.append("\t".join([name, "q086", sset, "risky", "expectdiff strict", "t4", "-", "0", cls, fi, fw, "0"]) + "\n")
    open(os.path.join(d, "cases.tsv"), "w").writelines(cases)
    return P, words


P, words = q086_kept(os.path.join(T, "q086"))
text, summ = S.score_q086(S.Kept(os.path.join(T, "q086")), P)
check([w[1] for w in words] == ["0x10000016", "0x10000012", "0x10000013"], "q086 replay: the kept kernel log's three 3D-side fault words, in job order")
check(summ.startswith("Q086: H-COV held (6 of 6 held-out rows), H-ANY refuted (3 of 6)"), "q086 replay: H-COV 6 of 6 (post hoc), H-ANY MUST FAIL (3 of 6): %s" % summ)

print("%d of %d replay checks" % (n - bad, n))
sys.exit(1 if bad else 0)
