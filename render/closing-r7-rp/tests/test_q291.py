#!/usr/bin/env python3
"""test_q291.py: the q291g and q291 stages' build tests (debug/CONTRACT.md, area q291; plan
closing7/a/exp-pixel-r7.md 1.2, 2.3, 3.3).  A script, not pytest: ok / FAIL lines, exit 0 or 1.
  PY tests/test_q291.py [--no-mock] [--no-sim]

  0. the generator: deterministic, the programs' pins, E898's landed template against the draft
  1. argv-twin: every row parsed back against the plan's rows TYPED BY HAND below
  2. t6 (R6's d9b2969): the features the rows use exist in its pinned sgxfive-test.c (probe --tri
     --tri-v, pixpds:12, --slot, --vtx-coords; probe_scratch with no cap; the 0x5CAFnnnn patch),
     and every row runs in its --mock (tests/realmock.py) and completes; the mock's coverage of
     the target equals the model's (the cut triangles' 1/256 coordinates as the tool parses them);
     --emit-scene shows the four scratch immediates patched
  3. replay on kept precedents under their real names: the depth-twin reader on E831's g-z dumps
     (render/closing-r3-geo-c out/g-z) and E885's q287 dumps (render/closing-r6-misc
     out/20261112-152213/q287): rule A holds on every full-screen row, ROUND, CEIL and FLOOR fail
     where E831 and E885 refuted them; the pix_pa0 image reader on E437's kept raw.txt (pa0 run:
     1062 of 1062, held; the pa1 run must fail)
  4. every control on a doctored input fails; refuse_unreadable passes ours and refuses bad ones
  5. the world: kept() through the runner's naming gives the frozen verdict for `model` and the
     rival verdict for each rival word; the world speaks the real tool's lines
  6. the sim test (tests/test_sim_q291.py), run as a subprocess
"""
import gzip
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, HERE)
import score_q291 as S  # noqa: E402
import scorekit  # noqa: E402
import g_q291 as G  # noqa: E402
import world_q291 as WORLD  # noqa: E402

DATA = "/Users/jtorra/src/resgx545-data/render"
E831 = DATA + "/closing-r3-geo-c/out/g-z"
E885 = DATA + "/closing-r6-misc/out/20261112-152213/q287"
E437 = "/Users/jtorra/src/resgx545-data/dpm/partial-reload-pos"
DRAFT = "/Users/jtorra/src/scratch/resgx545/closing7/a/q291"
T6_SRC = os.path.join(KP, "debug/toold9b2969/userspace/libsgxfive")
ok = True


def check(name, cond, info=""):
    global ok
    print(("ok   " if cond else "FAIL ") + name + (f": {info}" if info else ""))
    ok &= bool(cond)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def table(stage):
    head, rows = [], []
    for ln in open(os.path.join(KP, "tables", stage + ".txt")).read().splitlines():
        (head if ln.startswith("#") else rows).append(ln)
    return head, [r.split("|", 5) for r in rows]


# ---- the plan's rows, typed by hand from exp-pixel-r7.md 3.3 --------------------------------------
# (name, set, program set P/V/pa0/Z, W, H, geometry: full | (x0,y0,x1,y1,x2,y2) in PIXELS)
CX = (32, 0, 128, 0, 32, 48)
CY = (0, 16, 96, 16, 0, 64)
PLAN = {
    "q291g": [("q291-ps-gate-32x16", "gate", "P", 32, 16, "full")],
    "q291": [
        ("q291-pa0-ctl-20x12", "control", "pa0", 20, 12, "full"),
        ("q291-ps-ctl-cutx-64x16", "control", "P", 64, 16, CX),
        ("q291-ps-ctl-cuty-32x32", "control", "P", 32, 32, CY),
        ("q291-pv-ctl-32x16", "control", "V", 32, 16, "full"),
        ("q291-ps-fit-20x12-r1", "fit", "P", 20, 12, "full"),
        ("q291-ps-fit-20x12-r2", "fit", "P", 20, 12, "full"),
        ("q291-ps-18x12", "heldout", "P", 18, 12, "full"),
        ("q291-ps-24x8", "heldout", "P", 24, 8, "full"),
        ("q291-ps-12x12", "heldout", "P", 12, 12, "full"),
        ("q291-ps-20x8", "heldout", "P", 20, 8, "full"),
        ("q291-ps-26x10", "heldout", "P", 26, 10, "full"),
        ("q291-ps-10x6", "heldout", "P", 10, 6, "full"),
        ("q291-ps-cutx-34x16", "heldout", "P", 34, 16, CX),
        ("q291-ps-cutx-36x16", "heldout", "P", 36, 16, CX),
        ("q291-ps-cutx-44x16", "heldout", "P", 44, 16, CX),
        ("q291-ps-cutx-50x16", "heldout", "P", 50, 16, CX),
        ("q291-ps-cuty-32x18", "heldout", "P", 32, 18, CY),
        ("q291-ps-cuty-32x24", "heldout", "P", 32, 24, CY),
        ("q291-pv-20x12", "heldout", "V", 20, 12, "full"),
        ("q291-pv-18x12", "heldout", "V", 18, 12, "full"),
        ("q291-pv-24x8", "heldout", "V", 24, 8, "full"),
        ("q291-pz-20x12", "twin", "Z", 20, 12, "full"),
        ("q291-pz-18x12", "twin", "Z", 18, 12, "full"),
        ("q291-pz-24x8", "twin", "Z", 24, 8, "full"),
        ("q291-pz-12x12", "twin", "Z", 12, 12, "full"),
        ("q291-pz-10x6", "twin", "Z", 10, 6, "full"),
    ],
}
# the plan's counts: 20 x 12 band 25 x 15 = 375 (target 240, tile 512); 34 x 16 cut: columns 32-41
PLAN_COUNTS = {"q291-ps-fit-20x12-r1": (375, 240, 512), "q291-ps-cutx-34x16": (160, 32, 512)}


def parse_back(args):
    """An independent parse of a row's argv (not the scorer's)."""
    a = shlex.split(args)
    d = {"cmd": a[0], "W": int(a[a.index("--width") + 1]), "H": int(a[a.index("--height") + 1])}
    if "--tri-v" in a:
        v = [int(x) for x in a[a.index("--tri-v") + 1].split(",")]
        assert all(x % 256 == 0 for x in v)
        d["geom"] = tuple(x // 256 for x in v)
    else:
        d["geom"] = "full" if "--tri-full" in a else None
    if a[0] == "probe":
        d["slots"] = sorted(a[i + 1] for i, t in enumerate(a) if t == "--slot")
        d["pds"] = a[-1]
        d["fixed"] = a[1:8] == ["--tri", "pixpds:12", "--temps", "32", "--pixels", "--width",
                                str(d["W"])]
        d["coords"] = a[a.index("--vtx-coords") + 1] if "--vtx-coords" in a else None
    else:
        d["depth"] = [a[a.index(k) + 1] for k in ("--tri-z", "--depth-ctl", "--depth-fill",
                                                  "--depth-dump", "--depth-pages", "--poke")]
        d["fixed"] = a[1:4] == ["--keep-overflow", "--wait-ms", "20000"] and "--depth" in a
    return d


def want_prog(kind):
    pos, vtx = "$S/q291_pos.bin", "$S/q291_vtx.bin"
    return {"P": (["pixel=$S/pix_posstore.bin"], pos, None),
            "pa0": (["pixel=$S/pix_pa0.bin"], pos, None),
            "V": (["pixel=$S/pix_posstore.bin", "vtxuse=$S/vtx_attr_zx.bin"], vtx, "2")}[kind]


# ---- 0 -------------------------------------------------------------------------------------------
def test_generator():
    outs = [os.path.join(KP, p) for p in ("tables/q291g.txt", "tables/q291.txt",
                                          "predictions/q291g.tsv", "predictions/q291.tsv",
                                          "templates/pix_posstore.s", "templates/pix_posstore.lst",
                                          "gen/data/sources-q291.lst")] + \
        [os.path.join(KP, "bins", n) for n in G.NEED]
    G.write()
    a = [sha(p) for p in outs]
    G.write()
    check("the generator is deterministic (two runs, identical bytes)", a == [sha(p) for p in outs])
    pins = dict(reversed(ln.split()) for ln in open(G.PINS) if ln.strip() and not ln.startswith("#"))
    check("every program in bins/ is its pinned sha256", all(
        sha(os.path.join(KP, "bins", n)) == pins[n] for n in G.NEED), str(sorted(pins)))
    check("pix_posstore.bin is E898's (8a136e52..., the plan's SHA256.txt)",
          sha(os.path.join(KP, "bins/pix_posstore.bin")) ==
          "8a136e52d7966dc41b5f20da97f16347e5484bc8b6e1e37618def59cea2fdf9f")
    land = open(os.path.join(KP, "templates/pix_posstore.s")).read().splitlines()
    draft = open(DRAFT + "/pix_posstore.s").read().splitlines()
    diff = [i + 1 for i, (x, y) in enumerate(zip(land, draft)) if x != y]
    check("the landed template is the draft but for its header comment (line 3, E898)",
          len(land) == len(draft) and diff == [3] and land[2].startswith(";"), str(diff))
    check("the listing equals the draft's pix_posstore.lst byte for byte",
          sha(os.path.join(KP, "templates/pix_posstore.lst")) == sha(DRAFT + "/pix_posstore.lst"))
    check("the landed template copied byte for byte",
          sha(os.path.join(KP, "templates/pix_posstore.s")) == sha(G.T_POSSTORE))
    srcs = open(os.path.join(KP, "gen/data/sources-q291.lst")).read().split()
    check("sources-q291.lst: absolute paths that exist, outside KP", srcs and all(
        os.path.isabs(p) and os.path.exists(p) and not p.startswith(KP) for p in srcs))
    for st in ("q291g", "q291"):
        cs = {c["name"]: (tuple(c["reads"]), c["row"]) for c in G.controls(st)}
        try:
            scorekit.refuse_unreadable(cs, G.producible)
            check(f"refuse_unreadable passes {st}'s controls ({len(cs)})", len(cs) >= 1)
        except scorekit.ControlReadError as e:
            check(f"refuse_unreadable passes {st}'s controls", False, str(e))


# ---- 1 -------------------------------------------------------------------------------------------
def test_twin():
    for st, plan in PLAN.items():
        head, rows = table(st)
        check(f"{st}: #stage, #limit 1, {len(plan)} rows", f"#stage {st}" in head and
              "#limit 1" in head and len(rows) == len(plan), str(len(rows)))
        needs = {h.split("$S/")[1] for h in head if h.startswith("#need ")}
        used = {m for *_, a in rows for m in re.findall(r"\$S/([A-Za-z0-9_.-]+)", a)}
        check(f"{st}: every $S file is a #need and every #need is used", needs == used,
              f"{sorted(needs)} {sorted(used)}")
        for (name, sset, risk, knobs, tool, args), (pn, ps, kind, w, h, geom) in zip(rows, plan):
            d = parse_back(args)
            good = name == pn and sset == ps and tool == "t6" and risk == "safe" and \
                d["W"] == w and d["H"] == h and d["geom"] == geom and d["fixed"]
            if kind == "Z":
                good &= d["cmd"] == "tri" and "expectdiff" in knobs.split() and d["depth"] == [
                    "0.25,0.75,0.25", "0x17100c", "0xdeadbeef", "$W/depth", "17",
                    "blk:1=0x00400200"]
            else:
                slots, pds, coords = want_prog(kind)
                good &= d["cmd"] == "probe" and d["slots"] == sorted(slots) and d["pds"] == pds \
                    and d["coords"] == coords
                good &= ("strict" in knobs.split()) == (sset == "gate")
            check(f"{st} {name}: the plan's row ({kind} {w}x{h} {geom})", good, args)
    for n, (b, t, ti) in PLAN_COUNTS.items():
        r = S.parse_row(dict((x[0], x[5]) for x in table("q291")[1])[n])
        ms = S.model_sets(r)
        check(f"{n}: the plan's counts H-BAND {b}, H-TARGET {t}, H-TILE {ti}",
              (len(ms["H-BAND"]), len(ms["H-TARGET"]), len(ms["H-TILE"])) == (b, t, ti))
    pr = S.predictions("q291")
    held = [n for n, *_ in PLAN["q291"] if n.startswith("q291-ps-") and "-fit-" not in n
            and "-ctl-" not in n]
    check("the 12 held-out P rows separate H-BAND from H-TARGET and H-TILE",
          len(held) == 12 and all(pr[n][("separates", "H-BAND-vs-rivals")] == "yes"
                                  and len({pr[n][("valid_sha", m)] for m in S.MODELS}) == 3
                                  for n in held))
    for st in ("q291g", "q291"):
        pr = S.predictions(st)
        same = True
        for name, sset, _, _, _, args in table(st)[1]:
            r = S.parse_row(args)
            if r["cmd"] == "probe" and r["kind"] == "store":
                ms = S.model_sets(r)
                same &= all(pr[name][("valid_sha", m)] == S.set_sha(ms[m]) for m in S.MODELS)
            elif r["cmd"] == "tri":
                same &= pr[name][("stored_set_sha", "A")] == S.set_sha(S.band_set("A", r["W"],
                                                                                  r["H"]))
        check(f"{st}: the frozen predictions are the model's", same)


# ---- 2 -------------------------------------------------------------------------------------------
def test_tool():
    c = open(os.path.join(T6_SRC, "tools/sgxfive-test.c")).read()
    tp = open(os.path.join(T6_SRC, "src/tri_probe.c")).read()
    pin = open(os.path.join(KP, "TOOL6SRC.sha256")).read().split()[0]
    check("t6's sgxfive-test.c is the pinned d9b2969 source (TOOL6SRC.sha256)",
          sha(os.path.join(T6_SRC, "tools/sgxfive-test.c")) == pin)
    m = re.search(r"static void probe_tri_one\(.*?\n}\n", c, re.S)
    body = m.group(0) if m else ""
    check("t6: probe --tri parses --tri-v, --slot, --vtx-coords and a pixpds:N slot",
          '"--tri-v"' in c and "parse_tri_v(argv[++i], popts.tri.v256)" in c and
          '"--slot"' in c and '"--vtx-coords"' in c and "pixpds" in c)
    check("t6: the triangle probe prints every changed scratch dword (no cap: max_shown = the "
          "buffer's dword count)", body.count("SCRATCH_PAGES * SGXFIVE_PAGE_SIZE / 4)") >= 2 and
          "probe_report(f->name, g->fb, pt->width, pt->height, po->pixels, sp,\n\t\t\t     "
          "SCRATCH_PAGES * SGXFIVE_PAGE_SIZE / 4);" in body)
    check("t6: slot programs' 0x5CAFnnnn limm immediates patched to the scratch (tri_probe.c)",
          "SGXFIVE_TRI_PROBE_SCRATCH_IMM" in tp and "imm_patch(imm, ib)" in tp)
    import realmock
    for st in ("q291g", "q291"):
        for name, sset, _, _, tool, args in table(st)[1]:
            rc, out, err, kp, w = realmock.run(tool, args)
            r = S.parse_row(args)
            if r["cmd"] == "tri":
                good = rc == 0 and "tri: 1 renders ok" in out and \
                    os.path.exists(os.path.join(w, "depth", "depth.1.bin"))
                check(f"mock {name}: completes, writes $W/depth/depth.1.bin", good, err[-200:])
            else:
                p = S.parse_probe(out)
                nm = os.path.basename(shlex.split(args)[-1])[:-4]
                fg = (f"probe {nm}: tri {r['W']}x{r['H']}" in out and
                      ("pixel pixpds replaced" in out) and
                      (f"vertices256 {' '.join(map(str, r['v256']))}" in out if r["v256"] else
                       f"triangle (0,0) ({3 * r['W']},0) (0,{3 * r['H']})" in out))
                cov = sum(1 for y in p["rows"] for wd in p["rows"][y] if wd != S.BG_COLOUR)
                want = len(S.model_sets(r)["H-TARGET"])
                check(f"mock {name}: completes, as parsed; mock coverage {cov} = model {want}",
                      rc == 0 and p["ok"] and fg and len(p["rows"]) == r["H"] and cov == want,
                      err[-200:])
            shutil.rmtree(w, ignore_errors=True)
    # --emit-scene: the posstore words as built, the four 0x5CAF immediates patched
    args = table("q291g")[1][0][5]
    tmp = tempfile.mkdtemp(prefix="w.", dir=os.path.join(KP, "debug", "realmock"))
    rc, out, err, kp, w = realmock.run("t6", args.replace("probe --tri", "probe --emit-scene "
                                                         + tmp + "/scene.json --tri"))
    import json
    import struct
    sc = json.load(open(tmp + "/scene.json"))
    base = int(re.search(r"scratch at (0x[0-9a-f]+)", out).group(1), 16)
    pw = struct.unpack("<17Q", open(os.path.join(KP, "bins/pix_posstore.bin"), "rb").read())
    found = None
    for mm in sc["memory"]:
        dw = [int(x, 16) if isinstance(x, str) else x for x in mm["dwords"]]
        q = [dw[i] | dw[i + 1] << 32 for i in range(0, len(dw) - 1, 2)]
        for i in range(len(q) - 17):
            if q[i:i + 6] == list(pw[:6]):
                found = (mm["role"], q[i:i + 17])
    good = found is not None and found[0] == "usep"
    if good:
        q = found[1]
        good = all(q[k] == pw[k] for k in range(17) if k not in (6, 8, 10, 12)) and all(
            q[k] != pw[k] and q[k] & 0xFFFF == (base + 4 * j) & 0xFFFF
            for j, k in enumerate((6, 8, 10, 12)))
    check("--emit-scene: pix_posstore in the pixel code page, its four scratch immediates "
          "patched to the scratch + 0, 4, 8, 12, the rest unchanged", good)
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(w, ignore_errors=True)


# ---- 3 -------------------------------------------------------------------------------------------
def _gz_words(path):
    import struct
    b = gzip.open(path).read()
    return list(struct.unpack("<%dI" % (len(b) // 4), b))


def test_replay():
    for label, d in (("E831 g-z", E831), ("E885 q287", E885)):
        cs = S.cases(d)
        n_a, refuted = 0, {"ROUND": 0, "CEIL": 0, "FLOOR": 0}
        decided = {"ROUND": 0, "CEIL": 0, "FLOOR": 0}
        for name, row in cs.items():
            r = S.parse_row(row["args"])
            if not r["full"]:
                continue
            words = S.read_words(d, name + ".depth.1.bin")
            dr = S.depth_reading(words, r["W"], r["H"])
            n_a += dr["A"]
            for k in refuted:
                if S.band_set(k, r["W"], r["H"]) != S.band_set("A", r["W"], r["H"]):
                    decided[k] += 1
                    refuted[k] += k not in dr["rules"]
        full = sum(1 for n, row in cs.items() if S.parse_row(row["args"])["full"])
        check(f"replay {label}: the twin reader finds rule A's set in {n_a} of {full} full-screen "
              "dumps (all)", n_a == full and full >= 13, str(full))
        check(f"replay {label}: ROUND, CEIL, FLOOR fail wherever they differ from A "
              f"({decided})", all(refuted[k] == decided[k] for k in refuted) and
              sum(decided.values()) > 0, str(refuted))
    # E831's 924 under its real name
    w = S.read_words(E831, "z-ctl-34x18-y.depth.1.bin")
    check("replay E831 z-ctl-34x18-y: 924 stored, dead 0", (S.depth_reading(w, 34, 18)["stored"],
                                                            S.depth_reading(w, 34, 18)["dead"])
          == (924, 0))
    # a twin row's own scorer on a real dump given the wrong size must fail
    pr = {("stored_set_sha", "A"): S.set_sha(S.band_set("A", 34, 18))}
    tmpd = tempfile.mkdtemp(dir=os.path.join(KP, "debug"))
    shutil.copyfile(E831 + "/z-w20.depth.1.bin.gz", tmpd + "/z-w20.depth.1.bin.gz")
    held, txt, _ = S.row_result("z-w20", {"args": "tri --width 20 --height 18 --tri-full --depth "
                                          "--depth-dump d --depth-pages 17"}, tmpd,
                                {("stored_set_sha", "A"): S.set_sha(S.band_set("A", 20, 18))})
    check("replay E831 z-w20 under its real name through row_result: rule A held (550)",
          held is True and "stored 550" in txt, txt)
    held, txt, _ = S.row_result("z-w20", {"args": "tri --width 34 --height 18 --tri-full --depth "
                                          "--depth-dump d --depth-pages 18"}, tmpd, pr)
    check("replay E831 z-w20 scored as a 34 x 18 row: fails", held is False, txt)
    shutil.rmtree(tmpd)
    # pix_pa0's image reader on E437's kept raw.txt (64 x 64 default triangle)
    r = S.parse_row("probe --tri pixpds:12 --pixels --width 64 --height 64 --slot "
                    "pixel=pix_pa0.bin q291_pos.bin")
    for k, want in (("pa0", True), ("pa1", False)):
        raw = open(f"{E437}/dpm-partial-reload-pos-{k}/raw.txt").read()
        runs = re.split(r"^probe-case .*\n", raw, flags=re.M)[1:]
        res = [S.image_reading(r, t) for t in runs]
        cov = sum(1 for y in range(64) for x in range(64) if S.covered(S.vertices256(r), x, y))
        state = [g is not None and g["wrong"] == 0 for g in res]
        check(f"replay E437 {k} raw.txt (3 runs): the image reader says "
              f"{'held' if want else 'FAILED'}; the model covers 1062",
              len(res) == 3 and all(s == want for s in state) and cov == 1062,
              str([g and g["wrong"] for g in res]))


# ---- 4 and 5 -------------------------------------------------------------------------------------
def _kept(tokens):
    d = tempfile.mkdtemp(prefix="kept.", dir=os.path.join(KP, "debug"))
    for st in ("q291g", "q291"):
        WORLD.kept(os.path.join(d, st), st, set(tokens))
    return d


def _rewrite(path, fn):
    t = gzip.open(path).read().decode()
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as f:
        f.write(fn(t).encode())


def _controls(kd, st):
    pr = S.predictions(st)
    cs = S.cases(kd)
    out = {}
    for n, row in cs.items():
        if row["set"] in ("gate", "control"):
            held, _, g = S.row_result(n, row, kd, pr[n])
            out[n] = S.control_state(S.parse_row(row["args"]), held, g)
    return out


def test_controls():
    d = _kept(["model"])
    base = {**_controls(d + "/q291g", "q291g"), **_controls(d + "/q291", "q291")}
    check("model world: every control passes", all(v is True for v in base.values()), str(base))

    def lane_flip(t):    # one lane tag wrong
        return re.sub(r"(scratch \+0x00c 0x7e57000)(\d)", lambda m: m.group(1) + "3", t, count=1)

    def drop_last(t):    # one slot's dword 1 not stored
        return re.sub(r"^probe \S+: scratch \+0x1ff4 .*\n", "", t, flags=re.M)

    def value_off(t):    # one value one ulp off
        return re.sub(r"(scratch \+0x004 0x)([0-9a-f]{8})",
                      lambda m: m.group(1) + "%08x" % (int(m.group(2), 16) + 1), t, count=1)

    def pixel_off(t):    # one image pixel wrong
        return re.sub(r"(row 0: )([0-9a-f]{8})", lambda m: m.group(1) + "%08x" %
                      (int(m.group(2), 16) + 1), t, count=1)

    def vfar(t):         # clip x of one slot 40 units off
        return re.sub(r"(scratch \+0x008 0x)([0-9a-f]{8})",
                      lambda m: m.group(1) + "%08x" % (int(m.group(2), 16) + 400), t, count=1)
    cases = [("q291g", "q291-ps-gate-32x16", lane_flip, "a lane tag"),
             ("q291g", "q291-ps-gate-32x16", drop_last, "a missing slot"),
             ("q291g", "q291-ps-gate-32x16", value_off, "a value"),
             ("q291", "q291-pa0-ctl-20x12", pixel_off, "an image pixel"),
             ("q291", "q291-ps-ctl-cutx-64x16", value_off, "a value"),
             ("q291", "q291-ps-ctl-cutx-64x16", drop_last, "a missing slot"),
             ("q291", "q291-ps-ctl-cuty-32x32", value_off, "a value"),
             ("q291", "q291-ps-ctl-cuty-32x32", lane_flip, "a lane tag"),
             ("q291", "q291-pv-ctl-32x16", vfar, "a clip x 400 ulp off"),
             ("q291", "q291-pv-ctl-32x16", drop_last, "a missing slot")]
    for st, name, fn, what in cases:
        kd = os.path.join(d, st)
        p = os.path.join(kd, name + ".txt.gz")
        orig = open(p, "rb").read()
        _rewrite(p, fn)
        changed = open(p, "rb").read() != orig
        state = _controls(kd, st)[name]
        g = S.gate("q291g", kd) if st == "q291g" else None
        summ, _ = S.score(st, kd)
        check(f"doctored control {name} ({what}): FAILED" +
              (", gate 1" if g is not None else ", stage summary says controls FAILED"),
              changed and state is False and (g == 1 if g is not None else
                                              "controls FAILED" in summ), summ[:120])
        with open(p, "wb") as f:
            f.write(orig)
    # a control with no reading: its output not kept -> cannot tell, premise STOP
    kd = os.path.join(d, "q291")
    p = os.path.join(kd, "q291-ps-ctl-cutx-64x16.txt.gz")
    orig = open(p, "rb").read()
    os.remove(p)
    summ, det = S.score("q291", kd)
    check("a control's output not kept: cannot tell, a premise STOP, never a pass",
          summ.startswith("Q291 cannot tell") and any(x.startswith("STOP: premise") for x in det),
          summ[:100])
    open(p, "wb").write(orig)
    p = os.path.join(d, "q291g", "q291-ps-gate-32x16.txt.gz")
    os.rename(p, p + ".x")
    check("the gate row's output not kept: gate 2 (cannot tell)", S.gate("q291g", d + "/q291g") == 2)
    os.rename(p + ".x", p)
    # refuse_unreadable refuses a control that cannot read what it names, or reads nothing
    bad = {"x": (("image",), "probe --tri pixpds:12 --width 20 --height 12 --tri-full --slot "
                 "pixel=$S/pix_posstore.bin $S/q291_pos.bin"),
           "y": ((), table("q291g")[1][0][5]),
           "z": (("valid_set",), table("q291")[1][-1][5])}
    for k, v in bad.items():
        try:
            scorekit.refuse_unreadable({k: v}, G.producible)
            check(f"refuse_unreadable refuses bad control {k}", False)
        except scorekit.ControlReadError as e:
            check(f"refuse_unreadable refuses bad control {k}", True, str(e)[:90])
    shutil.rmtree(d)


def test_world():
    want = {
        "model": ("Q291 H-BAND held", 0, "values H-LIN held", "values E661 held"),
        "htarget": ("Q291 H-TARGET held (the other way)", 0, None, None),
        "htile": ("Q291 H-TILE held (the other way)", 0, None, None),
        "clamp-value": ("Q291 H-BAND held", 0, "values H-LIN refuted", "slots clamped"),
        "gate-miss": (None, 1, None, None),
        "vfar": ("Q291 controls FAILED", 0, "values E661 refuted", None),
        "ceil": ("Q291 H-BAND held", 0, "depth twins rule A 3 held, 2 FAILED", None),
        "fault": ("Q291 cannot tell", 2, None, None),
    }
    for tok, (head, gate, w1, w2) in want.items():
        d = _kept([tok])
        g = S.gate("q291g", d + "/q291g")
        v = S.verdict(d)
        good = g == gate and len(v) == 2 and all(x.startswith("SUMMARY: ") for x in v)
        good &= head is None or v[1].startswith("SUMMARY: " + head)
        good &= all(x is None or x in v[1] for x in (w1, w2))
        check(f"world {tok}: gate {gate}" + (f", '{head}'" if head else ""), good, v[1][:160])
        if tok == "model":
            for st in ("q291g", "q291"):
                r = subprocess.run([sys.executable, os.path.join(KP, "score/sessioncheck.py"),
                                    "kept", os.path.join(KP, "score/score_q291.py"), st,
                                    os.path.join(d, st), "--call", "score"],
                                   capture_output=True, text=True)
                check(f"sessioncheck kept {st} --call score: REQUIRED kept, nothing else read",
                      r.returncode == 0, r.stdout.strip()[-150:])
            r = subprocess.run([sys.executable, os.path.join(KP, "score/score_q291.py"), "q291",
                                d + "/q291"], capture_output=True, text=True)
            lines = r.stdout.splitlines()
            check("CLI: detail then exactly one SUMMARY line, exit 0", r.returncode == 0 and
                  sum(x.startswith("SUMMARY: ") for x in lines) == 1 and
                  lines[-1].startswith("SUMMARY: "))
            r = subprocess.run([sys.executable, os.path.join(KP, "score/score_q291.py"), "gate",
                                "q291g", d + "/q291g"])
            check("CLI gate q291g: exit 0 on the model world", r.returncode == 0)
        shutil.rmtree(d)
    d = _kept(["nodump"])
    miss = scorekit.missing_files(S.REQUIRED["q291"], d + "/q291", list(S.cases(d + "/q291")))
    check("world nodump: the twins' dumps are missing and REQUIRED names them (runner rc 23)",
          sorted(miss) == sorted(n + ".depth.1.bin" for n in S.TWINS), str(miss))
    shutil.rmtree(d)
    # handles: our rows yes, q287-shaped depth rows and the health pair no
    q287 = ("tri --keep-overflow --wait-ms 20000 --width 19 --height 18 --tri-full --tri-z "
            "0.25,0.75,0.25 --depth --depth-ctl 0x17100c --depth-fill 0xdeadbeef --depth-dump "
            "D --depth-pages 18 --poke blk:1=0x00400200")
    ours = all(WORLD.handles(t, shlex.split(a)) for st in ("q291g", "q291")
               for *_, t, a in table(st)[1])
    check("world handles every q291 row and not q287's depth rows, tri or fill",
          ours and not WORLD.handles("t7", shlex.split(q287)) and not WORLD.handles("t6", ["tri"])
          and not WORLD.handles("t6", ["fill"]))
    # missing --depth-dump directory: the real tool's line (t6 prints it and exits 0)
    a = shlex.split(table("q291")[1][-1][5].replace("$W", "/nonexistent-q291"))
    res = WORLD.answer("t6", a, {"model"})
    check("world: a missing --depth-dump DIR gets t6's `depth #1: --depth-dump: No such file or "
          "directory`", "depth #1: --depth-dump: No such file or directory" in res["out"])
    # the world speaks the tool's lines: line kinds in order equal the real mock's (values aside)
    import realmock

    def kinds(text):
        return [re.sub(r"0x[0-9a-f]+|[0-9a-f]{8}|\d+", "N", ln.split(":", 1)[-1])[:30]
                for ln in text.splitlines() if not re.search(r"scratch \+|: row \d", ln)]
    for name, *_, args in [table("q291g")[1][0], table("q291")[1][2], table("q291")[1][3]]:
        rc, out, err, kp, w = realmock.run("t6", args)
        res = WORLD.answer("t6", shlex.split(args.replace("$W", w).replace(
            "$S", os.path.join(KP, "bins"))), {"model"})
        km, kw = kinds(out), kinds(res["out"])
        check(f"world {name}: the real mock's line kinds (o0 aside)",
              [k for k in km if not k.startswith(" oN ")] == [k for k in kw if not k.startswith(" oN ")], f"{km} {kw}")
        shutil.rmtree(w, ignore_errors=True)


def main():
    args = sys.argv[1:]
    test_generator()
    test_twin()
    if "--no-mock" not in args:
        test_tool()
    test_replay()
    test_controls()
    test_world()
    if "--no-sim" not in args:
        r = subprocess.run([sys.executable, os.path.join(HERE, "test_sim_q291.py")],
                           capture_output=True, text=True)
        print(r.stdout, end="")
        check("tests/test_sim_q291.py exits 0", r.returncode == 0, r.stderr[-200:])
    print("test_q291:", "all ok" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
