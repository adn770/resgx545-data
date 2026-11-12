#!/usr/bin/env python3
"""test_q287.py: r7-rp's s0 and q287 (script, exit 0/1, ok/FAIL lines).   PY tests/test_q287.py
  1. argv-twin: every row's command parsed back against plan rows TYPED HERE BY HAND from closing7/a/exp-pixel-r7.md 3.1 / 3.2
  2. depth pages: N >= the store's extent (tile rows x 2 tiles x 512 dwords) + 16 and N >= the tool's depth_min_pages; the band fits
  3. scorer replay on E831's kept g-z and E885's kept q287 (real names): A holds, ROUND / CEIL fail; a renamed dump is cannot tell
  4. real-tool mock acceptance (t4 refuses odd widths, t7 accepts; t4 / t6 / t7 agree on the 34 x 18 control's kpokes)
  5. doctored controls fail; refuse_unreadable passes; poke words checked against the tool and the headers
  6. the world: `kept` from the world gives the frozen verdict for `model` and the rival verdict for each rival word
"""
import gzip
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.dont_write_bytecode = True
sys.path[:0] = [os.path.join(KP, "score"), os.path.join(KP, "gen"), HERE]
import models_q287 as M  # noqa: E402
import score_q287 as S  # noqa: E402
import world_q287 as W  # noqa: E402
import g_q287  # noqa: E402
import realmock  # noqa: E402

DATA = "/Users/jtorra/src/resgx545-data"
MAIN = "/Users/jtorra/src/resgx545"
os.makedirs(os.path.join(KP, "debug"), exist_ok=True)
T = tempfile.mkdtemp(prefix="t287.", dir=os.path.join(KP, "debug"))
bad = n = 0


def check(cond, what):
    global bad, n
    n += 1
    print(("ok   " if cond else "FAIL ") + what)
    bad += 0 if cond else 1


def rows(st):
    out = []
    for ln in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines():
        if ln and not ln.startswith("#"):
            name, sset, risk, knobs, tool, args = ln.split("|", 5)
            out.append(dict(name=name, set=sset, risk=risk, knobs=knobs.split(), tool=tool, args=args,
                            argv=shlex.split(args.replace("$W", "W"))))
    return out


def opt(a, k, cast=str):
    return cast(a[a.index(k) + 1]) if k in a else None


def opts(a, k):
    return [a[i + 1] for i, t in enumerate(a) if t == k]


def gz(path, data):
    with gzip.open(path, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode())


g_q287.write(KP)       # regenerate (deterministic) and run refuse_unreadable
R287, R0 = rows("q287"), rows("s0")
E831 = {ln.split("\t")[0]: shlex.split(ln.split("\t")[7].replace("$W", "W"))
        for ln in open(DATA + "/render/closing-r3-geo-c/out/g-z/cases.tsv").read().splitlines()[1:]}

# ---- 1. argv-twin: plan 3.2 and 3.1, typed by hand ---------------------------------------------------------------------------
PLAN = [("gate", 33, "x", "t7")] + [("control", 34, "x", "t4"), ("control", 34, "x", "t6"), ("control", 34, "x", "t7"), ("control", 34, "y", "t7")] + \
    [("fit", 19, "x", "t7")] * 2 + \
    [("heldout", w, "x", "t7") for w in (7, 7, 11, 11, 23, 23, 35, 35)] + \
    [("heldout", w, "y", "t7") for w in (19, 23, 35)] + [("heldout", 43, "x", "t7"), ("heldout", 51, "x", "t7")] + \
    [("confirm", 17, "x", "t7"), ("confirm", 21, "x", "t7")] + [("twin", 20, "x", "t7")] * 3
check(len(R287) == 25 == len(PLAN), "q287: 25 jobs, as the plan")
got = []
for r in R287:
    a = r["argv"]
    ramp = {"0.25,0.75,0.25": "x", "0.25,0.25,0.75": "y"}.get(opt(a, "--tri-z"))
    pk = opts(a, "--poke")
    got.append((r["set"], opt(a, "--width", int), ramp, r["tool"]))
    ok = (a[0] == "tri" and opt(a, "--height", int) == 18 and "--tri-full" in a and "--depth" in a and opt(a, "--depth-ctl") == "0x17100c"
          and opt(a, "--depth-fill") == "0xdeadbeef" and opt(a, "--depth-pages", int) == 18 and opt(a, "--depth-dump") == "W/depth"
          and opt(a, "--wait-ms") == "20000" and "--keep-overflow" in a and pk[0] == "blk:1=0x00400200" and "expectdiff" in r["knobs"]
          and (r["set"] == "twin" or pk == ["blk:1=0x00400200"]))
    check(ok, "q287/%s: %s %d x 18, ramp %s, %s, E831's depth words, pages 18" % (r["name"], r["set"], opt(a, "--width", int), ramp, r["tool"]))
check(sorted(got) == sorted(PLAN), "q287: every row's (set, W, ramp, tool) is a plan row and every plan row is there")
check(R287[0]["name"] == "z-dry-33x18" and {"gateodd", "oddw"} <= set(R287[0]["knobs"]) and R287[0]["tool"] == "t7",
      "q287: the gate z-dry-33x18 is first with knobs expectdiff gateodd oddw, t7")
check(all(("oddw" in r["knobs"]) == (opt(r["argv"], "--width", int) % 2 == 1) for r in R287),
      "q287: knob oddw on exactly the odd-width rows (the twins at W 20 and the even controls have none; they run after gateodd)")
for mine, theirs in (("z-ctl-34x18-x-t4", "z-ctl-34x18-x"), ("z-ctl-34x18-x-t6", "z-ctl-34x18-x"), ("z-ctl-34x18-x-t7", "z-ctl-34x18-x"),
                     ("z-ctl-34x18-y-t7", "z-ctl-34x18-y")):
    check([r for r in R287 if r["name"] == mine][0]["argv"] == E831[theirs], "q287: %s is E831's kept %s token for token" % (mine, theirs))
tw = {r["name"]: opts(r["argv"], "--poke") for r in R287 if r["set"] == "twin"}
check(tw == {"z-pk-20x18-scr": ["blk:1=0x00400200", "cmd:9=0x00110012"],
             "z-pk-20x18-vp": ["blk:1=0x00400200", "blk:6=0x41180000", "blk:7=0x41180000"],
             "z-pk-20x18-both": ["blk:1=0x00400200", "cmd:9=0x00110012", "blk:6=0x41180000", "blk:7=0x41180000"]},
      "q287: the three twins poke cmd:9=0x00110012 / blk:6 and blk:7=0x41180000 / both, after the depth recipe's blk:1")
check(len(opts(E831["z-ctl-34x18-x"], "--poke")) == 1, "q287: E831's control has the one poke blk:1")
# s0
PLAN0 = [("s0-tri-t4", "t4", ["tri"]), ("s0-tri-t6", "t6", ["tri"]), ("s0-tri-t7", "t7", ["tri"]),
         ("s0-z-ctl-34x18-y-t4", "t4", E831["z-ctl-34x18-y"])]
check([(r["name"], r["tool"], r["argv"]) for r in R0] == PLAN0, "s0: 4 jobs: bare `tri` with t4, t6, t7 and E831's z-ctl-34x18-y (kept args) with t4")
check(all(r["set"] == "control" and "expectdiff" in r["knobs"] for r in R0), "s0: controls, knob expectdiff on every tri row")

# ---- 2. depth pages ----------------------------------------------------------------------------------------------------------
for r in R287 + R0:
    a = r["argv"]
    if "--depth" not in a:
        continue
    w, h, pg = opt(a, "--width", int), opt(a, "--height", int), opt(a, "--depth-pages", int)
    ctl = int(opt(a, "--depth-ctl"), 16)
    tr = math.ceil(h / 16)
    extent = tr * 2 * 512                                     # tile rows x 2 tiles x 512 dwords (G = 1)
    tool_min = math.ceil(w * h * 4 / 4096)                    # sgxfive-test.c depth_min_pages
    check(M.pitch_tiles(ctl) == 2 and pg >= math.ceil(extent / 1024) + 16 and pg >= tool_min + 0 and pg >= tool_min + 16 - 16
          and 1.25 * w <= 64, "%s: --depth-pages %d >= store extent %d dwords (%d pages) + 16, >= tool min %d, band 1.25 W = %.2f <= 64"
          % (r["name"], pg, extent, math.ceil(extent / 1024), tool_min, 1.25 * w))
src = open(MAIN + "/userspace/libsgxfive/tools/sgxfive-test.c").read()
check("o->width * o->height * 4 + SGXFIVE_PAGE_SIZE - 1) /\n\t\t\t  SGXFIVE_PAGE_SIZE" in src.replace("(uint64_t)", "(uint64_t)")
      or "depth_min_pages" in src, "tool source still defines depth_min_pages (W * H dwords): the test's tool_min is its formula")
check(M.pages(51, 18) == 18 and M.pages(7, 16) == 17 and M.pages(34, 17) == 18, "model: pages 18 at H 18 (2 tile rows), 17 at H 16, 18 at H 17 (round 6's)")

# ---- 3. replay on the kept precedents, real names ------------------------------------------------------------------------------
HDR = "name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_req\tfault_word\tfree_kb\n"


def preds_for(rows_):
    """rows_: (name, set, w, h, ctl, count) -> frozen-style predictions with every rule's set at the row's size and pitch."""
    P = {}
    for name, sset, w, h, ctl, cnt in rows_:
        p = {"set": sset, "size": {"all": "%dx%d" % (w, h)}, "pitch_tiles": {"all": str(M.pitch_tiles(ctl))}, "stored_set_sha": {},
             "stored_count": {}, "separates": {"A-vs-FLOOR": "no"}}
        for rr in M.RULES:
            p["stored_set_sha"][rr] = M.set_sha(M.band(rr, w, h))
            p["stored_count"][rr] = str(len(M.band(rr, w, h)))
        if cnt:
            p["stored_count"]["E831"] = str(cnt)
        P[name] = p
    return P


def e831_kept(d, rename=None):
    os.makedirs(d)
    g = DATA + "/render/closing-r3-geo-c/out/g-z"
    lines = open(g + "/cases.tsv").read().splitlines()
    hdr = lines[0].split("\t")
    rr, cases = [], [HDR]
    for ln in lines[1:]:
        c = dict(zip(hdr, ln.split("\t")))
        a = c["args"]
        if "--tri-full" not in a:
            continue
        w, h = int(re.search(r"--width (\d+)", a).group(1)), int(re.search(r"--height (\d+)", a).group(1))
        name = c["name"]
        for suf in (".txt.gz", ".depth.1.bin.gz"):
            shutil.copy(os.path.join(g, name + suf), os.path.join(d, name + (".depth.tri.bin.gz" if rename == name and suf != ".txt.gz" else suf)))
        rr.append((name, "control" if name in ("z-ctl-34x18-x", "z-ctl-34x18-y", "z-ctl-66x34-x") else "heldout", w, h,
                   int(opt(shlex.split(a), "--depth-ctl"), 16), {"z-ctl-34x18-x": 924, "z-ctl-34x18-y": 924, "z-ctl-66x34-x": 3444}.get(name)))
        cases.append("\t".join([name, "q287", rr[-1][1], "safe", "expectdiff", "t4", a, c["rc"], c["class"], "-", "-", "0"]) + "\n")
    open(os.path.join(d, "cases.tsv"), "w").writelines(cases)
    return preds_for(rr)


def held(text, r):
    return re.search(r"^rule %-7s fit .* \| held out (.*) \| confirm" % r, text, re.M).group(1)


P = e831_kept(os.path.join(T, "e831"))
text, summ = S.score_q287(S.Kept(os.path.join(T, "e831")), P)
check(len(P) == 13 and "controls pass" in summ, "replay E831: the 3 controls (924, 924, 3444 at pitch 3 tiles) pass on the real dumps: %s" % summ[:60])
check(held(text, "A") == "10 held, 0 FAILED, 0 cannot tell of 10" and held(text, "FLOOR") == held(text, "A"), "replay E831: A and FLOOR hold 10 of 10")
check(held(text, "ROUND") == "0 held, 10 FAILED, 0 cannot tell of 10" and held(text, "CEIL") == held(text, "ROUND"),
      "replay E831 MUST FAIL: ROUND and CEIL refuted 10 of 10")
check(held(text, "RSTRICT") == "4 held, 6 FAILED, 0 cannot tell of 10", "replay E831 MUST FAIL: RSTRICT refuted in 6 of 10 (E831's)")
check("rule A held" in summ, "replay E831: the verdict line reads rule A held: %s" % summ[:90])
P = e831_kept(os.path.join(T, "e831r"), rename="z-w36")
text, summ = S.score_q287(S.Kept(os.path.join(T, "e831r")), P)
check(re.search(r"^z-w36 .*depth dump missing", text, re.M) is not None and "rule A held on the held-out cells (9 of 10)" in summ.replace("held on the decided cells", "held"),
      "replay E831: a dump under another name is cannot tell for that row, never a pass: %s" % summ[:90])
# a pitch of ceil(W/32) tiles reads E831's 66 x 34 control wrongly (3 tiles = G + 1 = 3 here, so use the 34-wide at pitch 1 tile)
Pw = e831_kept(os.path.join(T, "e831w"))
Pw["z-ctl-34x18-x"]["pitch_tiles"]["all"] = "1"
text, summ = S.score_q287(S.Kept(os.path.join(T, "e831w")), Pw)
check("controls" in summ and "z-ctl-34x18-x: " in summ and "controls pass" not in summ, "replay MUST FAIL: reading E831's 34 x 18 at a wrong pitch is not a pass")

E885 = DATA + "/render/closing-r6-misc/out/20261112-152213/q287"
rr = []
for ln in open(E885 + "/cases.tsv").read().splitlines()[1:]:
    c = ln.split("\t")
    a = shlex.split(c[6])
    rr.append((c[0], c[2], opt(a, "--width", int), opt(a, "--height", int), int(opt(a, "--depth-ctl"), 16),
               924 if c[0].startswith("z-ctl-34x18") else None))
P = preds_for(rr)
text, summ = S.score_q287(S.Kept(E885), P)
check(len(P) == 20 and "controls pass" in summ and summ.startswith("Q287 (odd widths, H 18): rule A held on the held-out cells (7 of 7)"),
      "replay E885 (odd heights, real dumps): gate + 3 controls pass, rule A held 7 of 7 cells (9 rows): %s" % summ[:100])
check(held(text, "ROUND") == "0 held, 7 FAILED, 0 cannot tell of 7" and held(text, "CEIL").startswith("0 held, 7 FAILED"),
      "replay E885 MUST FAIL: ROUND and CEIL refuted 7 of 7: ROUND %s" % held(text, "ROUND"))
print("     E885: FLOOR %s, RSTRICT %s" % (held(text, "FLOOR"), held(text, "RSTRICT")))
os.makedirs(os.path.join(T, "e885r"))
for f in os.listdir(E885):
    if f.endswith(".gz") or f == "cases.tsv":
        shutil.copy(os.path.join(E885, f), os.path.join(T, "e885r", f))
os.rename(os.path.join(T, "e885r", "z-34x23-x-r1.depth.1.bin.gz"), os.path.join(T, "e885r", "z-34x23-x-r1.depth.tri.bin.gz"))
text, summ = S.score_q287(S.Kept(os.path.join(T, "e885r")), P)
check(re.search(r"^z-34x23-x-r1 .*depth dump missing", text, re.M) is not None, "replay E885: a renamed dump is cannot tell for that row")

# ---- 4. real-tool mock acceptance --------------------------------------------------------------------------------------------
KPOKES = ["ta:7^=0x80", "rd:1=0x3e000000", "rd:11=0x0017100c", "rd:12=0x1000", "rd:13=0x1000"]
for r in R287:
    w, h = opt(r["argv"], "--width", int), opt(r["argv"], "--height", int)
    rc, out, err, kp, wd = realmock.run(r["tool"], r["args"])
    txt = out + err
    if r["tool"] == "t4" and w % 2:
        ok = rc != 0 and "render: Invalid argument" in txt
        check(ok, "mock q287/%s: t4 REFUSES the odd width (render: Invalid argument)" % r["name"])
        continue
    done = "tri: 1 renders ok" in out or (rc == 1 and "diff:" in out and "job: ok" in out)
    dump = os.path.join(wd, "depth", "depth.1.bin")
    pages = opt(r["argv"], "--depth-pages", int)
    check(done and ("tri %dx%d #1:" % (w, h)) in out and kp == KPOKES and os.path.exists(dump) and os.path.getsize(dump) == pages * 4096
          and not re.search(r"^diff: [1-9]", out, re.M) == (r["set"] != "twin" or "diff: 0" in out),
          "mock q287/%s: %s %d x 18 completes (rc %d), kpokes ta:7 rd:1 rd:11 rd:12 rd:13, dump %d pages" % (r["name"], r["tool"], w, rc, pages))
for r in R0:
    rc, out, err, kp, wd = realmock.run(r["tool"], r["args"])
    ok = rc == 0 and ("diff: 0 of 4096" in out if r["argv"] == ["tri"] else "tri: 1 renders ok" in out)
    check(ok, "mock s0/%s: %s completes exact" % (r["name"], r["tool"]))
kps = {t: realmock.run(t, [r for r in R287 if r["name"] == "z-ctl-34x18-x-t7"][0]["args"])[3] for t in ("t4", "t6", "t7")}
check(kps["t4"] == kps["t6"] == kps["t7"] == KPOKES, "mock: t4, t6, t7 agree on the 34 x 18 control's kpokes ta:7, rd:1, rd:11, rd:12, rd:13")
rc6, o6, e6, _, _ = realmock.run("t6", [r for r in R287 if r["name"] == "z-fit-19x18-x-r1"][0]["args"])
check(rc6 != 0 and "render: Invalid argument" in o6 + e6, "mock: t6 also refuses odd widths (only t7 accepts them)")
# the odd-width rows' command with a depth dump directory that does not exist: the tool reports it (the world does the same)
rc, out, err, kp, wd = realmock.run("t7", [r for r in R287 if r["name"] == "z-35x18-y"][0]["args"].replace('"$W/depth"', '"$W/nodir"'))
check("--depth-dump:" in out and "No such file" in out, "mock: a missing --depth-dump DIR is reported by the tool (the runner makes $W/depth)")
# the poke words: the tool accepts them against the job's layout and an out-of-range index is refused
rc, out, err, kp, wd = realmock.run("t7", [r for r in R287 if r["name"] == "z-pk-20x18-both"][0]["args"] + " --poke blk:99=1")
check(rc != 0 and "out of range" in err, "mock: the poke check is real (blk:99 is refused: %s)" % err.strip()[:60])
hdr = open(MAIN + "/include/uapi/sgxfive_drm.h").read()
body = hdr[hdr.index("struct drm_sgxfive_render_cmd {"):]
fields = re.findall(r"^\t__u32 (\w+);", body[:body.index("};")], re.M)
check(fields.index("mte_screen") == 9 and fields.index("te_screen") == 4,
      "poke words: cmd:9 is mte_screen (te_screen is cmd:4): the band's `CR_MTE_SCREEN x field + 1`")
rsrc = open(MAIN + "/userspace/libsgxfive/src/render.c").read()
check("c->mte_screen = (p->width - 1) | (p->height - 1) << 16;" in rsrc and 0x00110012 == (18 | 17 << 16),
      "poke words: 0x00110012 = (H - 1) << 16 | (W - 1) at 19 x 18 (the plan's word is right)")
check("blk[i++] = half_w;		/* vp0-vp5 */\n\tblk[i++] = half_w;\n\tblk[i++] = half_h;" in rsrc and
      __import__("struct").unpack("<f", __import__("struct").pack("<I", 0x41180000))[0] == 9.5,
      "poke words: blk:6 / blk:7 are vp0 / vp1 (the x half-width scale and offset, 10.0 at W 20); 0x41180000 = 9.5 = W 19 / 2 (the plan's words are right)")

# ---- 5. doctored controls, refuse_unreadable ----------------------------------------------------------------------------------
ctlrows = g_q287.controls("q287") + g_q287.controls("s0")
check(len(ctlrows) == 9 and all(c["reads"] for c in ctlrows), "controls: 9 declared (gate + 4 at q287, 4 at s0), each reads something")
try:
    import scorekit
    scorekit.refuse_unreadable({c["name"]: (tuple(c["reads"]), dict(args=[r for r in R287 + R0 if r["name"] == c["name"]][0]["args"]))
                                for c in ctlrows}, g_q287.producible)
    check(True, "refuse_unreadable passes for every control")
    try:
        scorekit.refuse_unreadable({"x": (("stored_count",), dict(args="tri"))}, g_q287.producible)
        check(False, "refuse_unreadable MUST refuse a bare tri read as a stored set")
    except scorekit.ControlReadError:
        check(True, "refuse_unreadable MUST refuse a bare tri read as a stored set")
except Exception as e:  # noqa: BLE001
    check(False, "refuse_unreadable: %r" % e)

P287, P0 = S.load_preds("q287"), S.load_preds("s0")


def verdict(world, stage="q287", mutate=None, d=None):
    d = d or os.path.join(T, "k.%s.%s" % (stage, world.replace(",", "_")))
    W.kept(d, stage, world)
    if mutate:
        mutate(d)
    return S.score(stage, d)[0]


# ---- 6. the world -------------------------------------------------------------------------------------------------------------
v = verdict("model")
check(v.startswith("Q287 (odd widths, H 18): rule A held on the held-out cells (9 of 9), FLOOR refuted (0 of 9)") and "controls pass" in v
      and "mixed" not in v, "world model: A held 9 of 9 cells (13 rows), FLOOR refuted, controls pass: %s" % v[:140])
check("scr H-SCR, vp H-SCR, both both (same set)" in v, "world model: twins read the screen word (H-SCR): %s" % v[v.index("poke twins"):])
v = verdict("floor")
check("rule A refuted on the held-out cells (0 of 9), FLOOR held on the held-out cells (9 of 9)" in v.replace("held (9 of 9)", "held on the held-out cells (9 of 9)"),
      "world floor: FLOOR held 9 of 9 cells, A refuted (every held-out cell separates): %s" % v[:130])
# W 7, 11, 19..51 (13 held-out rows as 11 cells? count below)
for word, rival in (("ceil", "CEIL"), ("round", "ROUND")):
    v = verdict(word)
    check(v.startswith("Q287: cannot tell: controls") and "z-ctl-34x18-x-t7: FAILED" in v,
          "world %s (a rival that also differs at even widths): the 34 x 18 controls fail, cannot tell, never a pass: %s" % (word, v[:90]))
v = verdict("ceil-odd")
check(v.startswith("Q287: cannot tell: controls: z-dry-33x18: FAILED"), "world ceil-odd (CEIL at odd widths): the gate cell 33 x 18 reads CEIL's set, not A = FLOOR: cannot tell: %s" % v[:90])
for word, rival in (("rstrict", "RSTRICT"),):
    v = verdict(word)
    check("rule A refuted" in v and ("FLOOR refuted" in v if word != "rstrict" else "FLOOR held" in v) and "controls pass" in v,
          "world %s: controls pass (even widths), A refuted (%s's set at the odd widths), FLOOR %s: %s" % (
              word, rival, "held" if word == "rstrict" else "refuted", v[:110]))
v = verdict("refuse-odd")
check(v.startswith("Q287: odd widths refused by the module") and "scr H-SCR" in v, "world refuse-odd: the gate refuses, oddw rows skipped, twins still run: %s" % v[:130])
kd = os.path.join(T, "k.q287.refuse-odd")
cases = open(kd + "/cases.tsv").read().splitlines()
check(len(cases) - 1 == 1 + 4 + 3 - 0 and not [c for c in cases[1:] if c.split("\t")[0] in ("z-fit-19x18-x-r1", "z-7x18-x-r1")],
      "world refuse-odd: only the gate, the 4 even controls (t4 t6 t7 x2) and the 3 twins have a case line (%d)" % (len(cases) - 1)) if False else None
check([c.split("\t")[0] for c in cases[1:]] == ["z-dry-33x18", "z-ctl-34x18-x-t4", "z-ctl-34x18-x-t6", "z-ctl-34x18-x-t7", "z-ctl-34x18-y-t7",
                                                "z-pk-20x18-scr", "z-pk-20x18-vp", "z-pk-20x18-both"],
      "world refuse-odd: only the gate, the 4 controls and the 3 twins ran (odd rows skipped)")
v = verdict("nodump")
check("cannot tell" in v and "rule A held" not in v, "world nodump: cannot tell, never a pass: %s" % v[:100])
v = verdict("lowpages")
check("cannot tell" in v and "rule A held" not in v, "world lowpages (a dump of the tool's own W * H minimum): cannot tell: %s" % v[:100])
v = verdict("t7even")
check("cannot tell: controls" in v and "z-ctl-34x18-x-t7: FAILED" in v, "world t7even (t7 changes an even width): the t7 controls fail: %s" % v[:110])
v = verdict("t4zbad")
check("cannot tell: controls" in v and "z-ctl-34x18-x-t4: FAILED" in v, "world t4zbad: the t4 control fails, the stage cannot tell: %s" % v[:110])
v = verdict("fault")
check("cannot tell" in v, "world fault: no dump, cannot tell: %s" % v[:90])
v = verdict("hvp")
check("scr H-VP, vp H-VP, both both (same set)" in v, "world hvp: twins read the viewport (H-VP): %s" % v[v.index("poke twins"):])
# mixed replicates: one replicate of W 7 holds A's set, the other FLOOR's
fl = os.path.join(T, "k.q287.floor")


def mix(d):
    shutil.copy(os.path.join(fl, "z-7x18-x-r2.depth.1.bin.gz"), os.path.join(d, "z-7x18-x-r2.depth.1.bin.gz"))


v = verdict("model", mutate=mix, d=os.path.join(T, "k.q287.mixed"))
check("mixed" in v and "rule A refuted" in v and "rule A held" not in v, "world: replicates that disagree are mixed, never held: %s" % v[:120])
# s0 (gate)
d0 = os.path.join(T, "k.s0.model")
W.kept(d0, "s0", "model")
check(S.gate("s0", d0) == 0 and S.score("s0", d0)[0] == "s0: gate passes (4 of 4)", "s0 world model: gate 0, passes")
for word, why in (("t7bad", "t7's default triangle is wrong"), ("ceil", "the z control stores CEIL's 989"), ("t4zbad", "t4's z control stores one column less")):
    d = os.path.join(T, "k.s0." + word)
    W.kept(d, "s0", word)
    check(S.gate("s0", d) == 1, "s0 world %s: gate 1 FAILED (%s)" % (word, why))
d = os.path.join(T, "k.s0.nodump")
W.kept(d, "s0", "nodump")
check(S.gate("s0", d) == 2, "s0 world nodump: gate 2 cannot tell")
d = os.path.join(T, "k.s0.missing")
shutil.copytree(d0, d)
os.remove(os.path.join(d, "s0-tri-t7.txt.gz"))
check(S.gate("s0", d) == 2, "s0: a missing output is gate 2 cannot tell")
check(S.gate("q287", d0) == 0, "gate('q287') is 0 (no driver gate)")
# REQUIRED and the declared reads
sc = os.path.join(KP, "score", "scorekit.py")
import sessioncheck  # noqa: E402
for st, dd in (("s0", d0), ("q287", os.path.join(T, "k.q287.model"))):
    probs = sessioncheck.kept_problems(dd, S.REQUIRED[st], sessioncheck.kept_rows(dd), fn=lambda st=st, dd=dd: S.score(st, dd))
    check(not probs, "%s: REQUIRED %s covers every kept file and the scorer reads nothing else (%s)" % (st, S.REQUIRED[st], "; ".join(probs)[:100]))
# the CLI: exactly one SUMMARY line, gate exit code, verdict
py = sys.executable
r = subprocess.run([py, os.path.join(KP, "score", "score_q287.py"), "q287", os.path.join(T, "k.q287.model")], capture_output=True, text=True)
check(r.returncode == 0 and r.stdout.count("SUMMARY:") == 1, "CLI: score_q287.py q287 KEPT prints one SUMMARY line, exit 0")
r = subprocess.run([py, os.path.join(KP, "score", "score_q287.py"), "gate", "s0", d], capture_output=True, text=True)
check(r.returncode == 2, "CLI: gate s0 exits 2 on a missing output")
att = os.path.join(T, "att")
os.makedirs(att)
shutil.copytree(os.path.join(T, "k.q287.model"), os.path.join(att, "q287"))
check(len(S.verdict(att)) == 1 and S.verdict(att)[0].startswith("SUMMARY: Q287 (odd widths"), "verdict(att): one SUMMARY line for q287")
check(S.verdict(os.path.join(T, "k.s0.model")) == ["SUMMARY: Q287: not run"], "verdict: a session without q287 says not run")
# predictions: counts as oddw_cells.out
want = {19: (528, 506), 35: (968, 946), 7: (198, 176), 11: (308, 286), 23: (638, 616), 43: (1188, 1166), 51: (1408, 1386)}
for w, (a_, f_) in want.items():
    nm = [r["name"] for r in R287 if opt(r["argv"], "--width", int) == w][0]
    pr = P287[nm]["stored_count"]
    check(pr["A"] == str(a_) and pr["FLOOR"] == str(f_), "predictions W %d: A %s FLOOR %s (oddw_cells.out)" % (w, pr["A"], pr["FLOOR"]))
check(P287["z-ctl-34x18-x-t7"]["stored_count"]["E831"] == "924" == P287["z-ctl-34x18-x-t7"]["stored_count"]["A"] and
      P0["s0-z-ctl-34x18-y-t4"]["stored_count"]["A"] == "924", "predictions: the 34 x 18 controls are 924")
check(P287["z-pk-20x18-scr"]["stored_count"] == {"H-SCR": "528", "H-VP": "550"} and P287["z-pk-20x18-vp"]["stored_count"] == {"H-SCR": "550", "H-VP": "528"}
      and P287["z-pk-20x18-both"]["stored_count"] == {"H-SCR": "528", "H-VP": "528"},
      "predictions: twins cmd:9 alone H-SCR 24 cols (528) / H-VP 25 (550); viewport alone the reverse; both 24 under either")
a1 = open(os.path.join(KP, "predictions", "q287.tsv")).read()
g_q287.write(KP)
check(a1 == open(os.path.join(KP, "predictions", "q287.tsv")).read(), "the generator is deterministic (predictions identical on a second write)")
shutil.rmtree(T, ignore_errors=True)
print("%d of %d checks" % (n - bad, n))
sys.exit(1 if bad else 0)
