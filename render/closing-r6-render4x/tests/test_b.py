#!/usr/bin/env python3
"""tests/test_b.py: set B (stage B on the r6-kernel module) offline: generator, layout against the fork's KUnit numbers, the plan's
table typed by hand, the argv twin, the scorer on argv-driven worlds of the r6-kernel, replays on kept files it must hold on and fail
on, and every command through the rgn4 tool's own mock.
Prints `ok ...` / `FAIL ...`; exit 1 on any FAIL."""
import os
import re
import shlex
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(KP, "gen"), os.path.join(KP, "score"), HERE]
import layout_b as B  # noqa: E402
import pbmodel as M  # noqa: E402
import rlib as L  # noqa: E402
import rules as R  # noqa: E402
import score_b as SB  # noqa: E402
import score_r as S  # noqa: E402
import twins as TW  # noqa: E402
import worlds as WD  # noqa: E402

PY = os.environ.get("PY", sys.executable)
os.makedirs(os.path.join(KP, "debug"), exist_ok=True)
TMP = tempfile.mkdtemp(prefix="test-b-", dir=os.path.join(KP, "debug"))
SB.preds()
S.preds()
bad = 0
STAGE_A = os.path.join(KP, "out", "20261112-144822")


def check(cond, msg):
    global bad
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        bad = 1


# ---- generator, counts, knobs ------------------------------------------------------------------------------------------------------
r = subprocess.run([PY, os.path.join(KP, "gen", "rgen_b.py"), "--check"], capture_output=True, text=True)
check(r.returncode == 0 and "DIFFERS" not in r.stdout, "rgen_b.py --check: every set B file is as on disk (%s)" % r.stdout.strip()[-60:])
stages = open(os.path.join(KP, "stages-B.txt")).read().split()
check(stages == ["s0b", "b", "k", "r"], "set B stages s0b, b, k, r")
counts = {st: len(WD.table(st)) for st in stages}
check(counts == {"s0b": 4, "b": 9, "k": 5, "r": 3}, "21 jobs: %s" % counts)
lim = {st: int([ln for ln in open(os.path.join(KP, "tables", st + ".txt")) if ln.startswith("#limit")][0].split()[1]) for st in stages}
check(lim == {"s0b": 1, "b": 2, "k": 4, "r": 1}, "limits s0b 1, b 2 (a second fault in b1-b8 stops), k 4 (3 predicted), r 1: %s" % lim)

# ---- the layout against the fork's KUnit (sgx_render_test.c at r6-kernel 3f0b3e74) -------------------------------------------------
four = {(1024, 768): 0x10000, (1280, 1024): 0x10000, (2048, 240): 0x10000, (768, 2048): 0x40000, (2048, 1536): 0x40000, (4096, 4096): 0x100000}
check(all(B.room(w, h, True) == v for (w, h), v in four.items()), "the 4x automatic room: the fork's KUnit table (1024 x 768 0x10000 ... 4096 x 4096 0x100000)")
check(B.layout(4096, 4096, True)["size"] == 0x2e3000 and B.room(1280, 1024, True, 0xb000) == 0xb000 and B.room(1280, 1024, False, 0xb000) == 0xb000
      and B.room(1280, 1024, True, 0xb001) == 0x10000, "4096 x 4096 at four arrays 0x2e3000 (SGX_RENDER_TD_MAX4_SIZE); a whole-page setting for either kind; 0xb001 ignored")
check(all(B.layout(w, h, False)["size"] == M.layout(w, h, 1)[3] for w, h in [(64, 64), (640, 480), (1024, 768), (1280, 1024), (4096, 4096)]),
      "a 1x context's layout is the rgn4 kernel's byte for byte")
check(B.layout(1280, 1024, True, 0x4000)["size"] == M.tadata_4x(1280, 1024) and B.layout(1280, 1024, True, 0x4000)["rgn"] == R.lay(1280, 1024)["rgn"],
      "the knob at 0x4000 reproduces the rgn4 layout of 1280 x 1024 (td.rgn 0x7000, size 0x34000)")
check(all(B.fault(*c[:4]) is False for c in R.RECORDED if c[0] < 4096) and B.fault(4096, 4096, 4096, 4096) is False,
      "H-TPM on the r6-kernel layout: none of the 26 recorded cells' targets faults with the automatic room")

# ---- the plan's table (section 4), typed ---------------------------------------------------------------------------------------------
PLAN = {"b9-1024x768": ("complete", 0x7000, 0x13000, 0)}
for n_, w, h in [("b1-1280x1024", 1280, 1024), ("b2-1184x768", 1184, 768), ("b3-1024x800", 1024, 800), ("b4-2048x240", 2048, 240),
                 ("b5-768x2048", 768, 2048), ("b6-2048x1536", 2048, 1536), ("b7-1280x768", 1280, 768), ("b8-1024x1024", 1024, 1024)]:
    PLAN[n_] = ("complete", R.entries_end(w, h), None, 0)
PLAN.update({"k1-1280x1024-room4000": ("fault", 0xd800, 0x7000, 0x4000), "k2-1280x1024-roomb000": ("complete", 0xd800, 0xe000, 0xb000),
             "k3-1280x1024-rooma000-held": ("fault", 0xd800, 0xd000, 0xa000), "k4-1024x768-room3000": ("fault", 0x7000, 0x6000, 0x3000),
             "k5-1024x768-room4000": ("complete", 0x7000, 0x7000, 0x4000), "r1-4096x960": ("complete", 0x2ff00, 0x43000, 0),
             "r2-2048x2032": ("complete", 0x1fff0, 0x43000, 0), "r3-4096x1152": ("overflow", None, 0x43000, 0)})
for st in ("b", "k", "r"):
    P = L.load_predictions(st + ".tsv", KP)
    for row in WD.table(st):
        n = row["name"]
        oc, end, rg, room = PLAN[n]
        got_room = int(next((k[5:] for k in row["knobs"].split() if k.startswith("room:")), "0"), 16)
        ok = L.pred(P, n, "outcome") == oc and got_room == room and (end is None or int(L.pred(P, n, "entries_end"), 16) == end) \
            and (rg is None or int(L.pred(P, n, "td_rgn"), 16) == rg)
        check(ok, "%s: %s, room %s, entries end and td.rgn as the plan's table" % (n, oc, hex(room) if room else "automatic"))
        hy = next((k for k in row["knobs"].split() if k.startswith("hypo:")), None)
        want = {"b": None if n.startswith("b9") else "hypo:b:2", "k": "hypo:k:4", "r": None}[st]
        check(hy == want and "strict" in row["knobs"].split(), "%s: hypothesis knob %s, strict health" % (n, hy))
PK = L.load_predictions("kh.tsv", KP)
lo = [int(x, 16) for x in L.pred(PK, "k3-1280x1024-rooma000-held", "lost").split(",")]
check((len(lo), lo[0], lo[-1], L.pred(PK, "k3-1280x1024-rooma000-held", "header0_lost")) == (171, 0xd000, 0xd7f8, "yes"),
      "k3's frozen set: the plan's 171 headers 0xd000 to 0xd7f8, header 0 among them")
nf = sum(1 for st in ("b", "k", "r") for row in WD.table(st) if L.pred(L.load_predictions(st + ".tsv", KP), row["name"], "outcome") == "fault")
check(nf == 3, "3 predicted faults (k1, k4, k3)")
check(all("--dump-render" not in r_["args"] for r_ in WD.table("r") if r_["name"] in ("r1-4096x960", "r3-4096x1152")),
      "r1 and r3 run without dumps (no dump above 2048 x 2048)")

# ---- the argv twin --------------------------------------------------------------------------------------------------------------------
def twin(args, knobs):
    a = WD.parse(TW.tokens(args))
    k = knobs.split()
    return (a["full"], a["aa4"], a["te"], a["w"], a["h"], a["mw"], a["mh"], int(next((x[5:] for x in k if x.startswith("room:")), "0"), 16), "held" in k)


TWIN = {n: (True, True, 0xE0000000, w, h, w, h, room, n.endswith("held")) for n, (w, h, room) in {
    "b9-1024x768": (1024, 768, 0), "b1-1280x1024": (1280, 1024, 0), "b2-1184x768": (1184, 768, 0), "b3-1024x800": (1024, 800, 0),
    "b4-2048x240": (2048, 240, 0), "b5-768x2048": (768, 2048, 0), "b6-2048x1536": (2048, 1536, 0), "b7-1280x768": (1280, 768, 0),
    "b8-1024x1024": (1024, 1024, 0), "k1-1280x1024-room4000": (1280, 1024, 0x4000), "k5-1024x768-room4000": (1024, 768, 0x4000),
    "k2-1280x1024-roomb000": (1280, 1024, 0xb000), "k4-1024x768-room3000": (1024, 768, 0x3000), "k3-1280x1024-rooma000-held": (1280, 1024, 0xa000),
    "r2-2048x2032": (2048, 2032, 0), "r1-4096x960": (4096, 960, 0), "r3-4096x1152": (4096, 1152, 0)}.items()}
TWIN.update({"s0b-1x-1024x768": (False, False, 0x20000000, 1024, 768, 1024, 768, 0, False),
             "s0b-1xf-1024x768": (True, False, 0x20000000, 1024, 768, 1024, 768, 0, False),
             "s0b-4x-288x144": (True, True, 0xE0000000, 288, 144, 288, 144, 0, False),
             "s0b-4x-1024x768": (True, True, 0xE0000000, 1024, 768, 1024, 768, 0, False)})
seen = set()
for st in stages:
    for row in WD.table(st):
        seen.add(row["name"])
        g = twin(row["args"], row["knobs"])
        check(g == TWIN.get(row["name"]), "argv twin %s: %s" % (row["name"], g))
check(seen == set(TWIN), "every plan row of set B is a table row and back (%d)" % len(TWIN))
k2 = [r_ for r_ in WD.table("k") if r_["name"].startswith("k2")][0]
check(twin(k2["args"], k2["knobs"].replace("room:0xb000", "room:0xa000")) != TWIN[k2["name"]], "must fail: k2 with k3's room")
check(twin(k2["args"], k2["knobs"].replace("room:0xb000 ", "")) != TWIN[k2["name"]], "must fail: k2 without its room knob (automatic)")
P0 = L.load_predictions("s0b.tsv", KP)
tb = TW.table()
pr = TW.check([(r_["name"], r_["args"], r_["knobs"], L.pred(P0, r_["name"], "pb_used"), "control", False) for r_ in WD.table("s0b")], tb)
check(not pr, "scene twins: every s0b control's page need is its kept twins' (1x full: r5 o10's 49)%s" % ("" if not pr else ": %s" % pr))


# ---- the scorer on r6-kernel worlds ---------------------------------------------------------------------------------------------------
def session(world, kernel="b", stages_=("s0b", "b", "k", "r")):
    d = tempfile.mkdtemp(prefix=world + "-", dir=TMP)
    for st in stages_:
        WD.kept(os.path.join(d, st), st, world, kernel=kernel)
    return d


d = session("model")
v = SB.verdict([d])
for w_ in ("NODATA", "cannot tell", "not supported", "FAILED", "not run"):
    check(w_ not in v, "model world (r6-kernel): no %r in set B's verdict" % w_)
for k in ("H-ROOM (b): H-ROOM: with the r6-kernel's automatic 4x room", "(8 of 8 rows decided)", "H-TPM knob (k):", "(3 of 3 rows decided)",
          "k3: set equal (171)", "header 0 lost (frozen yes)", "largest (r):"):
    check(k in v, "model world verdict has: %s" % k)
d = session("model", kernel="rgn4", stages_=("s0b",))
code, msg = SB.gate("b", [d])
check(code == 1 and "s0b-4x-1024x768: FAILED" in msg and "s0b-4x-288x144" not in msg.split("FAILED")[0][-40:],
      "s0b on the rgn4 kernel: the 4x TA-data size (0x1e000, not 0x2a000) fails a control and closes every gate: %s" % msg.splitlines()[0][:110])
d = session("b-old")
v = SB.verdict([d])
check("controls FAILED: s0b" in v, "world b-old (a module without the change): s0b fails, nothing claimed")
d2 = session("b-old", stages_=("b", "k"))
os.symlink(os.path.join(session("model", stages_=("s0b",)), "s0b"), os.path.join(d2, "s0b"))
v = SB.verdict([d2])
check(v.count("is not supported") == 2, "world b-old with a passing s0b: H-ROOM and the knob claim are both not supported")
d = session("b-bound", stages_=("s0b", "k"))
v = SB.verdict([d])
check("H-TPM knob (k):" in v and ("is not supported" in v or "controls FAILED: k5" in v), "world b-bound (the room must be 4 times the 1x room): k2 faults, the exact-limit claim fails")
d = session("b-kset", stages_=("s0b", "k"))
v = SB.verdict([d])
check("k3: both 168, lost only 0, predicted only 3" in v and "is not supported" in v, "world b-kset: three offsets fewer than frozen: FAILED with the counts")
d = session("b-b1fault", stages_=("s0b", "b"))
v = SB.verdict([d])
check("is not supported: 7 held, 1 FAILED" in v, "world b-b1fault: b1 faulting refutes H-ROOM (7 held, 1 FAILED)")
d = session("b-wrong", stages_=("s0b", "r"))
v = SB.verdict([d])
check("largest (r):" in v and "is not supported" in v and "completed with 1024 of 3932160 pixels wrong" in SB.r_stage(os.path.join(d, "r"))[0][1], "world b-wrong: r1 with 1024 wrong pixels fails r")

# ---- replays on kept files ----------------------------------------------------------------------------------------------------------
if os.path.exists(os.path.join(STAGE_A, "s0", "cases.tsv")):
    c = L.read_cases(STAGE_A + "/s0")
    res = {}
    for n_a, n_b in (("s0-1x-1024x768", "s0b-1x-1024x768"), ("s0-4x-288x144", "s0b-4x-288x144"), ("s0-4x-1024x768", "s0b-4x-1024x768")):
        res[n_b] = S.ctl(S.job(STAGE_A + "/s0", c, n_a), SB.PRED["s0b"], n_b)
    check(res["s0b-1x-1024x768"][0] == "PASS" and res["s0b-4x-288x144"][0] == "PASS", "replay: stage A's kept 1x and 288 x 144 controls pass as s0b (their layouts do not change)")
    check(res["s0b-4x-1024x768"][0] == "FAILED" and "tadata_size 122880, frozen 172032" in res["s0b-4x-1024x768"][1],
          "must fail: stage A's 4x 1024 x 768 (rgn4 TA data 0x1e000) as s0b: %s" % res["s0b-4x-1024x768"][1][:70])
    ca = L.read_cases(STAGE_A + "/a")
    h1 = S.job(STAGE_A + "/a", ca, "h1-1024x800-held")
    got = B.lost_offsets(h1["heldtadata"], 1024, 800, 0x7000)
    check(got is not None and set(got) == set(R.lost(1024, 800)), "replay: set B's lost reader on stage A's h1 dump (base 0x7000) gives its 43 (as set A's did)")
    got2 = B.lost_offsets(h1["heldtadata"], 1024, 800, 0xd000)
    check(set(got2 or []) != set(R.lost(1024, 800)), "must fail: the same dump read from another base (0xd000) is not the set")
else:
    check(False, "stage A's kept attempt %s is missing" % STAGE_A)
c = L.read_cases(L.R5X_A + "/o")
v1 = S.ctl(S.job(L.R5X_A + "/o", c, "o10-1xf-1024x768-p53"), SB.PRED["s0b"], "s0b-1xf-1024x768")
check(v1[0] == "PASS", "replay: r5's o10 (the 1x full twin) passes as s0b-1xf: %s" % v1[1][:60])
dj = S.job(L.R5X_A + "/d", L.read_cases(L.R5X_A + "/d"), "d1-1280x1024-held")
got = B.lost_offsets(dj["heldtadata"], 1280, 1024, 0x7000)
want = [int(x, 16) for x in L.pred(PK, "k3-1280x1024-rooma000-held", "lost").split(",")]
check(len(got) == 1023 and set(want) < set(got) and S.lost_cmp(got, want)[1] is False,
      "must fail: E869's dump (lost from 0x7000, 1023) against k3's frozen 171 (from 0xd000): %s" % S.lost_cmp(got, want)[0])

# ---- every command through the rgn4 tool's own mock ------------------------------------------------------------------------------------
TOOL = os.environ.get("R6X_MOCK_TOOL", os.path.join(KP, "debug/tool4623753/userspace/libsgxfive/build/sgxfive-test"))
if not os.path.exists(TOOL):
    subprocess.run([os.path.join(HERE, "build_mock_tool.sh")], check=True, capture_output=True)
for st in stages:
    for row in WD.table(st):
        a = shlex.split(re.sub(r'--dump-render \S+', "", row["args"].replace("$W", TMP)))
        pr = subprocess.run([TOOL, "--mock"] + a, capture_output=True, text=True, timeout=900)
        txt = pr.stdout + pr.stderr
        m = re.search(r"--max-width (\d+) --max-height (\d+)", " ".join(a))
        okp = pr.returncode != 2 and "usage" not in txt.lower() and "bad option" not in txt and "job: ok" in txt \
            and (not m or ("targets up to %sx%s" % m.groups()) in txt)
        check(okp, "mock: %s/%s parses and runs in the rgn4 tool's mock" % (st, row["name"]))
print("work dir (kept for inspection): %s" % TMP)
sys.exit(bad)
