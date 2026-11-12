#!/usr/bin/env python3
"""test_dump.py: the `dump` area's checks (stages q293, q139), pytest-free: prints ok/FAIL lines, exits 0 or 1.
Run with the session's PY after `PY gen/g_dump.py`.  Sections (debug/CONTRACT.md):
  1 argv twin       every row parsed back against rows TYPED BY HAND from plan 3.5 / 3.6 (not from the generator)
  2 real-tool mock  every row through tests/realmock.py (t4 = 4623753's --mock): q293 rows refused by the mock's TE_AA check
                    (no render_rgn_arrays in the mock: rgn:1 covers it) and complete at TE_AA 0x20000000 with their kpokes
                    before the right render and the dump files' real names; q139 rows complete with their kpoke and dumps
  3 replay          the readers on the kept precedent files under their REAL names: E888's t7 (u2 PASS) and t8 (u2 FAILS),
                    E897's 13 two-object dumps (u1's object reader: 0 and 27, +12, zero before; render 2's images), the
                    datasets' kept maps of every q139 case, the r6-render4x and s1b dumps as region-header reader checks
  4 controls        every control's reading on a doctored input fails; refuse_unreadable passes and catches a doctored
                    control; the scorer reads only REQUIRED files (sessioncheck) and score() never reads a held-out row
  5 world           kept(dir) from tests/world_dump.py through the runner's naming: model -> the frozen verdicts, each
                    rival word -> its rival verdict; the held-out CLI (model hash, refusals); determinism of the generator
"""
import gzip
import hashlib
import json
import os
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(KP, "score"), os.path.join(KP, "gen")]
import g_dump as G  # noqa: E402
import lib_dump as L  # noqa: E402
import realmock  # noqa: E402
import score_dump as S  # noqa: E402
import scorekit  # noqa: E402
import sessioncheck  # noqa: E402
import world_dump as W  # noqa: E402

DATA = "/Users/jtorra/src/resgx545-data"
T7DIR = DATA + "/render/closing-r6-render4x/out/20261112-144822/t"
SCR = os.path.join(KP, "debug", "dump")
os.makedirs(SCR, exist_ok=True)
FAILS = []


def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    if not ok:
        FAILS.append(what)


def table(stage):
    return W.table_rows(stage)


# ---- 1. argv twin: typed by hand from the plan ------------------------------------------------------------------------------------
BASE3 = ("tri --tri-full --keep-going --wait-ms 20000 --width 64 --height 64 --max-width 64 --max-height 64 -n 3 --geometry 1 "
         "--geometry 2 --poke cmd:1=0x40000000 --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26")
TWIN = ["0x00040101", "0x00000000", "0x00000000", "0x00000000", "0x00000000", "0x00100000", "0x00001000", "0x00003f00",
        "0x10500010", "0x3f000000", "0x00105000", "0x00001000", "0x50003f00", "0x10500010", "0x3f000000", "0x00000000"]
HAND_Q293 = {
    "u1": ("control", BASE3 + ' --dump-render "$W/dump"'),
    "u2": ("control", "tri --tri-full --keep-going --wait-ms 20000 --width 64 --height 64 --max-width 64 --max-height 64 -n 2 "
           "--geometry 1 --poke cmd:1=0x40000000 --poke cmd:10=0xeaa26e26 --poke cmd:13=0x80000002 --poke cmd:16=0xeaa26e26 "
           '--kpoke-render 2:par:11=0x00000001 --dump-render "$W/dump"'),
    "u3": ("heldout", BASE3 + "".join(" --kpoke-render 3:par:%d=%s" % (38 + i, v) for i, v in enumerate(TWIN))
           + ' --dump-render "$W/dump"'),
    "u4": ("heldout", BASE3 + ' --kpoke-render 3:par:38=0xffffffff --dump-render "$W/dump"'),
}
# (set, W, H, poke) typed from plan 3.6 and the risky dataset's table (scripts/mtile-fields-risky.sh)
HAND_Q139 = [
    ("control", 256, 256, None), ("control", 640, 480, None), ("control", 256, 256, "ta:143=0x01404004"),
    ("fit", 256, 256, "ta:143=0x01008004"), ("fit", 256, 256, "ta:143=0x01005004"), ("fit", 256, 256, "ta:144=0x0200a008"),
    ("fit", 256, 256, "ta:146=0x8"), ("fit", 256, 256, "ta:146=0x10"), ("fit", 256, 256, "ta:143=0x02008008"),
    ("fit", 640, 480, "ta:143=0x85010018"), ("fit", 640, 480, "ta:143=0x82014018"), ("fit", 640, 480, "ta:144=0x04410018"),
    ("fit", 640, 480, "ta:144=0x02018018"),
    ("heldout", 256, 256, "ta:143=0x0100c004"), ("heldout", 256, 256, "ta:144=0x0200c008"), ("heldout", 256, 256, "ta:146=0x4"),
    ("heldout", 256, 256, "ta:146=0x18"), ("heldout", 256, 256, "ta:144=0x0280a00a"),
    ("heldout", 640, 480, "ta:143=0x87010018"), ("heldout", 640, 480, "ta:143=0x82020018"),
    ("heldout", 640, 480, "ta:144=0x05010018"), ("heldout", 640, 480, "ta:144=0x0201c018"),
    ("heldout", 640, 480, "ta:143=0x02010018"),
    ("replicate", 256, 256, "ta:143=0x01008004"),
]
ALLOWED_SETS = {"gate", "control", "fit", "heldout", "confirm", "replicate", "twin", "bridge"}
ALLOWED_KNOBS = re.compile(r"^(expectdiff|strict|hypo:\w+:\d+|gateodd|oddw|rgn:1|expectfault|needdump)$")


def parse(args):
    t = shlex.split(args)
    o = {"verb": t[0], "pokes": [], "kpokes": [], "geometry": [], "flags": set()}
    i = 1
    while i < len(t):
        a = t[i]
        if a in ("--poke", "--kpoke-render", "--geometry", "--width", "--height", "--max-width", "--max-height", "-n",
                 "--wait-ms", "--dump-render"):
            v = t[i + 1]
            if a == "--poke":
                o["pokes"].append(v)
            elif a == "--kpoke-render":
                o["kpokes"].append(v)
            elif a == "--geometry":
                o["geometry"].append(int(v))
            else:
                o[a] = v
            i += 2
        else:
            o["flags"].add(a)
            i += 1
    return o


def sec1():
    print("== 1. argv twin")
    for stage, n in (("q293", 4), ("q139", 24)):
        rows = table(stage)
        check(len(rows) == n, "%s: %d rows (plan: %d)" % (stage, len(rows), n))
        text = open(os.path.join(KP, "tables", stage + ".txt")).read()
        check(text.startswith("#stage %s\n#limit 1\n" % stage), "%s: header #stage, #limit 1 (plan: fault limit 1)" % stage)
        check("$S/" not in text, "%s: no staged program, so no #need" % stage)
        for name, st, risk, knobs, tool, args in rows:
            ok = (re.fullmatch(r"[A-Za-z0-9._-]+", name) and st in ALLOWED_SETS and risk in ("safe", "risky")
                  and all(ALLOWED_KNOBS.match(k) for k in knobs.split()) and tool == "t4"
                  and "expectdiff" in knobs.split() and "needdump" in knobs.split() and args.endswith('--dump-render "$W/dump"'))
            check(bool(ok), "%s %s: name, set, risk, knobs (expectdiff needdump), tool t4, dump last" % (stage, name))
        names = [r[0] for r in rows]
        check(len(set(names)) == len(names), "%s: names unique" % stage)
    rows = table("q293")
    check([r[0][5:7] for r in rows] == ["u1", "u2", "u3", "u4"], "q293: u1 first, then u2, u3, u4")
    for r, key in zip(rows, ("u1", "u2", "u3", "u4")):
        st, args = HAND_Q293[key]
        got, want = parse(r[5]), parse(args)
        check(r[1] == st and got == want and r[5] == args, "q293 %s: set %s and argv equal the hand-typed plan row" % (key, st))
        check("rgn:1" in r[3].split(), "q293 %s: rgn:1 (TE_AA 0x40000000 on a context without --aa4)" % key)
    u3 = parse(rows[2][5])
    check(len(u3["kpokes"]) == 16 and u3["kpokes"][0] == "3:par:38=0x00040101" and u3["kpokes"][-1] == "3:par:53=0x00000000",
          "q293 u3: 16 kpokes, 3:par:38..53 (E829's p3 shifted by 27)")
    rows = table("q139")
    for r, (st, w, h, poke) in zip(rows, HAND_Q139):
        o = parse(r[5])
        want = ["tri", "--tri-full", "--pixels", "--width", str(w), "--height", str(h), "--max-width", str(w),
                "--max-height", str(h)] + (["--kpoke-render", "1:" + poke] if poke else []) + [
            "--wait-ms", "20000", "--keep-going", "--dump-render", '"$W/dump"']
        check(r[1] == st and shlex.split(r[5]) == [x.strip('"') if x == '"$W/dump"' else x for x in want]
              and o["kpokes"] == (["1:" + poke] if poke else []),
              "q139 %s: %s %dx%d %s = the dataset's command + --keep-going --dump-render" % (r[0], st, w, h, poke or "unpoked"))
    sets = [r[1] for r in rows]
    check(sets.count("control") == 3 and sets.count("fit") == 10 and sets.count("heldout") == 10 and
          sets.count("replicate") == 1, "q139: 3 controls, 10 fit, 10 held out, 1 replicate (plan 3.6: 24)")
    # the dataset's template, token for token (read here from the dataset scripts, not the generator)
    for d in ("mtile-fields", "mtile-fields-risky"):
        s = open("%s/ta/%s/scripts/%s.sh" % (DATA, d, d)).read()
        check('"$T" tri --tri-full --pixels --width "$w" --height "$h" --max-width "$w" --max-height "$h" \\\n\t\t $args '
              '--wait-ms 20000' in s, "dataset %s: the command the rows copy" % d)


# ---- 2. real-tool mock ---------------------------------------------------------------------------------------------------------
def mock(args, dumpdir=True):
    base = os.path.join(KP, "debug", "realmock")
    os.makedirs(base, exist_ok=True)
    w = tempfile.mkdtemp(prefix="wd.", dir=base)
    os.makedirs(os.path.join(w, "dbgfs"))
    with open(os.path.join(w, "dbgfs", "render_param"), "wb") as f:
        f.write(b"\1" * 8192)
    with open(os.path.join(w, "dbgfs", "render_tadata"), "wb") as f:
        f.write(b"\2" * 4096)
    rc, out, err, kp, w = realmock.run("t4", args, workdir=w)
    files = sorted(os.listdir(os.path.join(w, "dump")))
    shutil.rmtree(w)
    return rc, out, err, kp, files


def sec2():
    print("== 2. real-tool mock (t4 = 4623753 --mock)")
    src = subprocess.run(["git", "-C", realmock.MAIN, "show", "4623753:userspace/libsgxfive/tools/sgxfive-test.c"],
                         capture_output=True, text=True).stdout
    check("#define KPR_MAX\t16" in src, "t4 source: KPR_MAX 16 (a row may carry 16 --kpoke-render; u3 carries 16)")
    check("if (!ret && o->dump_dir) {" in src and "if (o->keep_going) {" in src,
          "t4 source: the dump is written only when ret is 0, which --keep-going keeps after a wrong image")
    check('ret = dump_render(o->dump_dir, "tri", false);' in src, "t4 source: -n N writes one dump, DIR/tri.{param,tadata}.bin")
    for name, st, risk, knobs, tool, args in table("q293"):
        rc, out, err, kp, files = mock(args)
        check(rc == 1 and "job: rejected (Invalid argument)" in out and "rgn:1" in knobs,
              "q293 %s: the mock refuses TE_AA 0x40000000 without --aa4 (no render_rgn_arrays in the mock): rgn:1" % name)
        a2 = args.replace("cmd:1=0x40000000", "cmd:1=0x20000000")
        rc, out, err, kp, files = mock(a2)
        o = parse(args)
        n = int(o["-n"])
        want_k = [k.split(":", 1)[1] for k in o["kpokes"]]
        last = n
        ok = (rc == 0 and L.geometry_lines(out) == list(range(1, n)) and L.tool_kpokes(out, last) == want_k and kp == want_k
              and files == ["tri.param.bin", "tri.tadata.bin"] and L.tri_counts(out, last) is not None)
        check(ok, "q293 %s at TE_AA 0x20000000: parses, renders 1..%d geometry only, %d kpokes before render %d, dump %s"
              % (name, n - 1, len(want_k), last, files))
    u3 = table("q293")[2][5]
    rc, out, err, kp, files = mock(u3.replace("cmd:1=0x40000000", "cmd:1=0x20000000").replace(
        "--dump-render", "--kpoke-render 3:par:54=0x00000000 --dump-render"))
    check(rc == 2 and "bad --kpoke-render 3:par:54" in err, "t4 refuses a 17th --kpoke-render (KPR_MAX): u3's 16 is the limit")
    rc, out, err, kp, files = mock(table("q293")[0][5].replace("cmd:1=0x40000000", "cmd:1=0x20000000").replace(
        '"$W/dump"', '"$W/nodir"'))
    wd = tempfile.mkdtemp(prefix="wd.", dir=SCR)
    r = W.answer("t4", shlex.split(table("q293")[0][5].replace("$W", wd).replace('/dump"', '/nodir"')), {"model"})
    shutil.rmtree(wd)
    check(rc == 1 and "sgxfive-test: --dump-render: No such file or directory" in err and r["rc"] == 1 and
          r["err"].strip() == "sgxfive-test: --dump-render: No such file or directory",
          "a missing dump directory: the real tool's error and rc 1, and the world's the same")
    sizes = {}
    for name, st, risk, knobs, tool, args in table("q139"):
        rc, out, err, kp, files = mock(args)
        o = parse(args)
        want_k = [k.split(":", 1)[1] for k in o["kpokes"]]
        ok = (rc == 0 and L.diff_count(out) == (0, int(o["--width"]) * int(o["--height"])) and kp == want_k
              and L.tool_kpokes(out, 1) == want_k and files == ["tri.param.bin", "tri.tadata.bin"]
              and L.image_tiles(out, int(o["--width"]), int(o["--height"])) == (True, set()))
        sizes[o["--width"]] = len(out)
        check(ok, "q139 %s: completes in the mock, kpoke %s before render 1, --pixels whole, dump %s" % (name, want_k, files))
    print("     --pixels text: 256x256 %d bytes, 640x480 %d bytes (the mock's; the laptop's is the same format)" % (
        sizes["256"], sizes["640"]))


# ---- 3. replay on the kept precedent files (real names) ------------------------------------------------------------------------
E897 = ["closing-r3k-pixel/out/20261110-193547/k-pb0/pb-d0-te40", "closing-r3k-pixel/out/20261110-193547/k-pb0/pb-p1-te40",
        "closing-r3k-regress/out/20261110-222647/rg-pb/pb-n40-a", "closing-r3k-regress/out/20261110-222647/rg-pb/pb-n40-b",
        "closing-r3k-regress/out/20261110-222647/rg-pb/pb-n40-c", "closing-r4-q285/out/20261111-081210/a-pb/pb-p2-own11",
        "closing-r4-q285/out/20261111-081210/a-pb/pb-p3a-twin", "closing-r4-q285/out/20261111-081210/a-pb/pb-p3b-twin",
        "closing-r4-q285/out/20261111-081210/a-pb/pb-p4a-ffff", "closing-r4-q285/out/20261111-081210/a-pb/pb-p4b-ffff",
        "closing-r4-q285/out/20261111-081210/a-pb0/pb-d0-te40", "closing-r4-q285/out/20261111-081210/a-pb0/pb-p1-te40",
        "closing-r6-render4x/out/20261112-144822/t/t7-tri-te40-poke11"]
TWINS = ("pb-p3a-twin", "pb-p3b-twin")


def files_of(p):
    return (L.read_bytes(p + ".tri.param.bin.gz"), L.read_text(p + ".txt.gz"), L.read_text(p + ".dmesg.gz"))


def sec3():
    print("== 3. replay on kept precedent files")
    P = S.preds("q293")
    par, txt, km = files_of(T7DIR + "/t7-tri-te40-poke11")
    st, t = S.u2_reading(par, txt, km, P)
    check(st == "PASS", "u2 on E888's kept t7 (t7-tri-te40-poke11): PASS (%s)" % t)
    par8, txt8, km8 = files_of(T7DIR + "/t8-ctl-te40-1array")
    st, t = S.u2_reading(par8, txt8, km8, P)
    check(st == "FAILED", "u2 on E888's kept t8 (one render, no poke): FAILED (%s)" % t[:90])
    st, t = S.u1_reading(par8, txt8)
    check(st in ("FAILED", "NODATA"), "u1 on t8 (one object, no render 3): not a pass (%s: %s)" % (st, t[:70]))
    n_empty = 0
    for rel in E897:
        p = DATA + "/render/" + rel
        par, txt, km = files_of(p)
        objs = L.objects(L.dwords(par, 4096))
        twin = os.path.basename(rel) in TWINS
        ok = ([o[0] for o in objs] == [0, 27] and objs[1][1:] == (12, 0)
              and objs[0][1] == (11 if twin else 12))
        c2 = L.tri_counts(txt, 2)
        n_empty += c2 is not None and c2[0] == 0
        check(ok and c2 == ((4096, 0, 0) if twin else (0, 4096, 0)),
              "E897 %s: objects %s, render 2 %s" % (os.path.basename(rel), [(o[0], o[1]) for o in objs], L.counts_text(c2)))
        st, t = S.u1_reading(par, txt)
        check(st != "PASS", "  u1's reading on it (two renders, no object at 54, no render 3): %s" % st)
    check(n_empty == 11, "E897: 11 of 13 jobs draw 0 triangle pixels in render 2 (the 2 twins draw 4096)")
    # q139's readers: the datasets' kept maps of every case, under their real names
    Q = S.preds("q139")
    for n, (st, w, h, case) in sorted(S.q139_table(Q).items()):
        d = G.dataset_rows()[case][0]
        txt = L.read_text("%s/dumps/%s.txt.gz" % (d, case))
        complete, bad = L.image_tiles(txt, w, h)
        check(complete and L.tiles_text(bad) == L.pred(Q, n, "kept_wrong"),
              "q139 %s: %s's kept map reads back as frozen (%d tiles)" % (n, case, len(bad)))
    miss = G.e877_misses()
    check(all(c in miss for n, (st, w, h, c) in S.q139_table(Q).items() if st != "control") and
          not any(c in miss for n, (st, w, h, c) in S.q139_table(Q).items() if st == "control"),
          "q139: every named case but the controls is a miss of E877's frozen model (q139_score.out)")
    # region-header reader checks (E877: no dump of these datasets was kept)
    p = DATA + "/render/closing-s1b/out/p-b2/d-t256"
    td, pa = L.read_bytes(p + ".tri.tadata.bin.gz"), L.read_bytes(p + ".tri.param.bin.gz")
    ok, t, lay = L.baseline_layout(td, pa, 256, 256)
    check(ok, "reader on s1b d-t256 (a kept 256 x 256 1x dump, every tile drawn): %s" % t)
    check(L.moved_tiles(td, lay, 256, 256) == (set(), set()), "  its own headers are all in place against itself")
    for nm in ("t8-ctl-te40-1array", "t7-tri-te40-poke11"):
        td8, pa8 = L.read_bytes(T7DIR + "/%s.tri.tadata.bin.gz" % nm), L.read_bytes(T7DIR + "/%s.tri.param.bin.gz" % nm)
        hs = L.headers(td8, L.header_base(td8))
        ok, t, _ = L.baseline_layout(td8, pa8, 64, 64)
        check(len(hs) == 128 and sum(1 for h in hs if h[4]) == 16 and not ok,
              "reader on r6-render4x %s.tri.tadata.bin: 128 headers, 16 with a stream (TE_AA 0x40: rows doubled), and as a "
              "1x baseline it is refused (%s)" % (nm, t[:60]))
    return td, pa


# ---- 4. controls on doctored inputs ----------------------------------------------------------------------------------------------
def gzw(path, data):
    with open(path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as f:
            f.write(data if isinstance(data, bytes) else data.encode())


def sec4(td256, pa256):
    print("== 4. controls on doctored inputs; refuse_unreadable; files read")
    P = S.preds("q293")
    par, txt, km = files_of(T7DIR + "/t7-tri-te40-poke11")
    b = bytearray(par)
    struct.pack_into("<I", b, 4 * 40, 0x12345678)
    check(S.u2_reading(bytes(b), txt, km, P)[0] == "FAILED", "u2 with one head dword doctored: FAILED")
    check(S.u2_reading(par, txt.replace("0x8ea26cdfee74a325", "0x8ea26cdfee74a326"), km, P)[0] == "FAILED",
          "u2 with the target hash doctored: FAILED")
    check(S.u2_reading(par, txt, "", P)[0] != "PASS", "u2 with no 'applied' line: not a pass")
    k = tempfile.mkdtemp(prefix="k293.", dir=SCR)
    W.kept(k, "q293", ("model",))
    par1 = L.read_bytes(os.path.join(k, "q293-u1-ctl-n3.tri.param.bin.gz"))
    txt1 = L.read_text(os.path.join(k, "q293-u1-ctl-n3.txt.gz"))
    check(S.u1_reading(par1, txt1)[0] == "PASS", "u1 on the world's model dump: PASS")
    b = bytearray(par1)
    struct.pack_into("<2I", b, 4 * 65, 0x00040101, 0)          # object 3's format word moved to +11
    check(S.u1_reading(bytes(b), txt1)[0] == "FAILED", "u1 with object 3's format word at +11: FAILED")
    check(S.u1_reading(par1, txt1.replace("#3: 0 triangle, 4096 background", "#3: 4096 triangle, 0 background"))[0] ==
          "FAILED", "u1 with render 3 drawing: FAILED")
    check(S.u1_reading(par1, re.sub(r"(?m)^tri 64x64 #3: .*$", "", txt1))[0] == "NODATA",
          "u1 with no render 3 line: NODATA (cannot tell, never a pass)")
    shutil.rmtree(k)
    # q139 baselines and the poked control
    ok, t, lay = L.baseline_layout(td256, pa256, 256, 256)
    b = bytearray(td256)
    b[lay["base"] + 12 * 5: lay["base"] + 12 * 6] = b"\0" * 12
    check(not L.baseline_layout(bytes(b), pa256, 256, 256)[0], "baseline with one header zeroed: FAILED")
    b = bytearray(td256)
    w0 = struct.unpack_from("<I", b, lay["base"] + 12 * 7)[0]
    struct.pack_into("<I", b, lay["base"] + 12 * 7, w0 ^ (2 << 16))
    check(not L.baseline_layout(bytes(b), pa256, 256, 256)[0], "baseline with one header's column changed: FAILED")
    b = bytearray(td256)
    struct.pack_into("<I", b, lay["base"] + 12 * 9 + 4, 0x7ffff000)
    check(not L.baseline_layout(bytes(b), pa256, 256, 256)[0], "baseline with one stream outside the buffer: FAILED")
    check(L.moved_tiles(bytes(b[:0]) + td256[:lay["base"]] + b"\0" * 12 + td256[lay["base"] + 12:], lay, 256, 256)[0] ==
          {lay_tile(lay, 0)}, "the poked control's reading: one header zeroed -> that tile moved")
    k = tempfile.mkdtemp(prefix="k139.", dir=SCR)
    W.kept(k, "q139", ("model",))
    cases = L.read_cases(k)
    Q = S.preds("q139")
    tab = S.q139_table(Q)
    lays, ctls, _ = S.baselines(k, cases, Q, tab)
    check(all(v == "PASS" for v in ctls.values()) and len(ctls) == 2, "world model: both baselines PASS")
    for n, doctor, what in (("q139-c-256x256-ctl", "pixel", "one pixel wrong"),
                            ("q139-c-640x480-ctl", "header", "one header zeroed"),
                            ("q139-c-256x256-m1-B1-5", "move", "one header moved")):
        d2 = tempfile.mkdtemp(prefix="k139d.", dir=SCR)
        for f in os.listdir(k):
            os.symlink(os.path.join(k, f), os.path.join(d2, f))
        if doctor == "pixel":
            p = os.path.join(d2, n + ".txt.gz")
            t = L.read_text(p).replace("row 3: 0xff00ff00", "row 3: 0xff00ff01", 1)
            os.remove(p)
            gzw(p, t)
        else:
            p = os.path.join(d2, n + ".tri.tadata.bin.gz")
            b = bytearray(L.read_bytes(p))
            o = 0x4000 + 12 * 3
            if doctor == "header":
                b[o:o + 12] = b"\0" * 12
            else:
                struct.pack_into("<I", b, o, struct.unpack_from("<I", b, o)[0] ^ (0x40 << 16))
            os.remove(p)
            gzw(p, bytes(b))
        lays2, c2, _ = S.baselines(d2, cases, Q, tab)
        c3, _ = S.poked_control(d2, cases, Q, tab, lays2)
        c2.update(c3)
        check(c2[n] == "FAILED", "q139 control %s with %s: FAILED" % (n, what))
        s, lines = S.score("q139", d2)
        check("controls FAILED" in s, "  and the stage headline says controls FAILED")
        shutil.rmtree(d2)
    # refuse_unreadable
    for st in ("q293", "q139"):
        try:
            G.check_controls(st, [tuple(r) for r in table(st)])
            check(True, "refuse_unreadable passes on %s's controls" % st)
        except scorekit.ControlReadError as e:
            check(False, "refuse_unreadable on %s: %s" % (st, e))
    bad = {"q293-u2-ctl-t7": (("tri3",), {"args": table("q293")[1][5]})}
    try:
        scorekit.refuse_unreadable(bad, G.producible)
        check(False, "refuse_unreadable catches a control reading render 3 on a -n 2 row")
    except scorekit.ControlReadError:
        check(True, "refuse_unreadable catches a control reading render 3 on a -n 2 row")
    try:
        scorekit.refuse_unreadable({"x": (("image_tiles",), {"args": table("q293")[0][5]})}, G.producible)
        check(False, "refuse_unreadable catches a control reading --pixels tiles on a row without --pixels")
    except scorekit.ControlReadError:
        check(True, "refuse_unreadable catches a control reading --pixels tiles on a row without --pixels")
    # the files the scorer reads; score() never opens a held-out row
    k2 = tempfile.mkdtemp(prefix="k293.", dir=SCR)
    W.kept(k2, "q293", ("model",))
    for st, d in (("q293", k2), ("q139", k)):
        probs = sessioncheck.kept_problems(d, S.REQUIRED[st], sessioncheck.kept_rows(d), lambda: S.score(st, d))
        check(not probs, "sessioncheck kept --call: %s reads only REQUIRED files, all kept %s" % (st, probs[:2]))
    reads = sessioncheck.files_read(lambda: S.score("q139", k))
    ho = [n for n, (st, *_r) in tab.items() if st == "heldout"]
    check(not [p for p in reads if any(os.path.basename(p).startswith(n + ".") for n in ho)],
          "score('q139') opens no file of the %d held-out rows" % len(ho))
    s, lines = S.score("q139", k)
    check(not any(n in ln for ln in lines + [s] for n in ho), "score('q139') prints nothing about a held-out row")
    reads = sessioncheck.files_read(lambda: S.q139_fitdata(k))
    check(not [p for p in reads if any(os.path.basename(p).startswith(n + ".") for n in ho)],
          "q139-fitdata opens no file of a held-out row")
    for name, st, risk, knobs, tool, args in table("q293") + table("q139"):
        wd = tempfile.mkdtemp(prefix="wd.", dir=SCR)
        os.makedirs(os.path.join(wd, "dump"))
        os.makedirs(os.path.join(wd, "depth"))
        pr = sessioncheck.missing_outdirs([x.replace("$W", wd) for x in shlex.split(args)], dir_opts=("--dump-render",))
        shutil.rmtree(wd)
        if pr:
            check(False, "outdirs %s: %s" % (name, pr))
    check(True, "outdirs: every --dump-render directory is one the runner makes ($W/dump)")
    shutil.rmtree(k2)
    return k


def lay_tile(lay, slot):
    return next(t for t, s in lay["slot"].items() if s == slot)


# ---- 5. the world ------------------------------------------------------------------------------------------------------------------
def sec5(k139_model):
    print("== 5. world verdicts")
    expect293 = {
        "model": "(2 of 2 rows decided)",
        "obj2dark": "is not supported: 1 held, 1 FAILED",
        "plain": "controls FAILED: q293-u1-ctl-n3",
        "t7drift": "controls FAILED: q293-u2-ctl-t7",
        "nopoke": "controls FAILED: q293-u2-ctl-t7",
        "nodump": "cannot tell",
        "fault3": "cannot tell",
    }
    for tok, want in expect293.items():
        d = tempfile.mkdtemp(prefix="w293.", dir=SCR)
        W.kept(d, "q293", (tok,))
        s, lines = S.score("q293", d)
        check(want in s and (tok != "model" or s.startswith("q293: Q293:")), "q293 world %s: %s" % (tok, s[:150]))
        if tok == "model":
            r = subprocess.run([sys.executable, os.path.join(KP, "score", "score_dump.py"), "q293", d],
                               capture_output=True, text=True)
            last = r.stdout.strip().splitlines()[-1]
            check(r.returncode == 0 and last.startswith("SUMMARY: q293: Q293:") and r.stdout.count("SUMMARY:") == 1,
                  "CLI score_dump.py q293 KEPT: one SUMMARY line, exit 0")
            g = subprocess.run([sys.executable, os.path.join(KP, "score", "score_dump.py"), "gate", "q293", d],
                               capture_output=True, text=True)
            check(g.returncode == 0, "CLI gate q293: 0 (no driver gate)")
            att = tempfile.mkdtemp(prefix="att.", dir=SCR)
            os.symlink(d, os.path.join(att, "q293"))
            os.symlink(k139_model, os.path.join(att, "q139"))
            v = S.verdict(att)
            check(len(v) == 2 and all(x.startswith("SUMMARY: ") for x in v) and "Q293" in v[0] and "H-MOVED" in v[1],
                  "verdict(ATT): two SUMMARY lines, Q293 and Q139")
            heldout_cli(k139_model, att)
            shutil.rmtree(att)
        if tok == "nodump":
            check("READER-MISS" in "\n".join(lines), "  nodump names the READER-MISS")
        if tok == "nopoke":
            check(all("cannot tell: the pokes did not land" in ln for ln in lines if ln.startswith(("q293-u3", "q293-u4"))),
                  "  nopoke: u3 and u4 cannot tell (the pokes did not land)")
        shutil.rmtree(d)
    expect139 = {
        "model": "(10 of 10 rows decided)",
        "inplace": "is not supported",
        "movedrew": "headers moved for tiles that drew",
        "norepl": "10 fit rows dropped",
        "badbase": "controls FAILED: q139-c-256x256-ctl",
        "nodump": "cannot tell",
    }
    for tok, want in expect139.items():
        if tok == "model":
            d = k139_model
        else:
            d = tempfile.mkdtemp(prefix="w139.", dir=SCR)
            W.kept(d, "q139", (tok,))
        s, lines = S.score("q139", d)
        ok = want in s
        if tok == "model":
            ok = ok and s.startswith("q139: Q139 H-MOVED") and "dropped" not in s and "H-INPLACE in" not in s
        if tok == "inplace":
            ok = ok and "H-INPLACE in 10 fit rows" in s
        check(ok, "q139 world %s: %s" % (tok, s[:160]))
        if d != k139_model:
            shutil.rmtree(d)


def heldout_cli(k, att):
    Q = S.preds("q139")
    tab = S.q139_table(Q)
    ho = sorted(n for n, (st, *_r) in tab.items() if st == "heldout")
    model = {"model": "test: the datasets' maps", "cases": {n: {"wrong": sorted(
        "%d.%d" % t for t in L.tiles_parse(L.pred(Q, n, "kept_wrong")))} for n in ho}}
    path = os.path.join(att, "q139-model.json")
    raw = json.dumps(model, sort_keys=True).encode()
    with open(path, "wb") as f:
        f.write(raw)
    sha = hashlib.sha256(raw).hexdigest()
    lines, s = S.q139_heldout(os.path.join(att, "q139"), sha)
    check("(10 of 10 rows decided)" in s and "H-MOVED on the held-out rows: 10 held" in s,
          "q139-heldout with a model hashing to the given sha: %s" % s[:120])
    lines, s = S.q139_heldout(os.path.join(att, "q139"), "0" * 64)
    check("REFUSED" in s and len(lines) == 1, "q139-heldout with a wrong sha: REFUSED, nothing read")
    reads = sessioncheck.files_read(lambda: S.q139_heldout(os.path.join(att, "q139"), "0" * 64))
    check(not [p for p in reads if os.path.basename(p).startswith("q139-h-")], "  and it opened no held-out file")
    m2 = dict(model, cases={n: v for n, v in model["cases"].items() if n != ho[0]})
    raw2 = json.dumps(m2).encode()
    p2 = os.path.join(att, "m2.json")
    with open(p2, "wb") as f:
        f.write(raw2)
    lines, s = S.q139_heldout(os.path.join(att, "q139"), hashlib.sha256(raw2).hexdigest(), p2)
    check("REFUSED" in s, "q139-heldout with a model lacking a held-out row: REFUSED")
    r = subprocess.run([sys.executable, os.path.join(KP, "score", "score_dump.py"), "q139-heldout",
                        os.path.join(att, "q139"), sha], capture_output=True, text=True)
    check(r.returncode == 0 and r.stdout.strip().splitlines()[-1].startswith("SUMMARY: q139 held out:"),
          "CLI score_dump.py q139-heldout KEPT MODEL_SHA: SUMMARY line, exit 0")


def determinism():
    print("== generator determinism")
    outs = []
    for _ in range(2):
        d = tempfile.mkdtemp(prefix="gen.", dir=SCR)
        G.write(d)
        outs.append({rel: open(os.path.join(d, rel), "rb").read() for rel in
                     ("tables/q293.txt", "tables/q139.txt", "predictions/q293.tsv", "predictions/q139.tsv",
                      "gen/data/sources-dump.lst")})
        shutil.rmtree(d)
    check(outs[0] == outs[1], "two runs write identical bytes")
    check(all(outs[0][rel] == open(os.path.join(KP, rel), "rb").read() for rel in outs[0]),
          "the session's files are the generator's output (run `PY gen/g_dump.py` after a change)")
    srcs = outs[0]["gen/data/sources-dump.lst"].decode().split()
    check(all(os.path.isabs(s) and os.path.exists(s) and not s.startswith(KP) for s in srcs),
          "sources-dump.lst: %d absolute paths outside KP, all present" % len(srcs))
    for rel, sha in (("score/pbdump_dump.py", "pbdump.py"), ("score/region_tiles_dump.py", "region_tiles.py")):
        main = subprocess.run(["git", "-C", realmock.MAIN, "show", "1c64f3a:tools/usse-asm/" + sha], capture_output=True).stdout
        check(open(os.path.join(KP, rel), "rb").read() == main, "%s is a byte copy of 1c64f3a tools/usse-asm/%s" % (rel, sha))


def main():
    sec1()
    sec2()
    td, pa = sec3()
    k = sec4(td, pa)
    sec5(k)
    shutil.rmtree(k)
    determinism()
    print("%s: %d failed" % ("FAIL" if FAILS else "ok", len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
