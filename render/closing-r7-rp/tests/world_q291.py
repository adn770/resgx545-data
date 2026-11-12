#!/usr/bin/env python3
"""world_q291.py: the fake tool's answers for the q291g and q291 rows, from ARGV ONLY (never a case
name), in the real t6 tool's words (sgxfive-test.c probe_tri_one, probe_report, probe_scratch; the
tri --depth lines of its mock), for the session's fake laptop and for kept() below.

  handles(tool, argv)   probe --tri with a q291 PDS program (q291_pos.bin, q291_vtx.bin); tri --depth
                        at H below 16 (the q291 depth twins; q287's depth rows are all H 18)
  answer(tool, argv, tokens) -> dict(out, err, rc, kmsg); writes --depth-dump DIR/depth.1.bin when
                        DIR exists; a missing DIR gets the real tool's line
                        `depth #1: --depth-dump: No such file or directory` and rc 0 (as t6 does:
                        sgxfive-test.c prints strerror and goes on; the runner's rc 23 catches it)
  kept(dir, stage, tokens)   a kept stage directory as run_stage.sh names it (cases.tsv,
                        NAME.txt.gz, NAME.err.gz, NAME.dmesg.gz, NAME.depth.1.bin.gz)

World words (FAKE_WORLD split on commas): model (H-BAND sets, H-LIN values, E808 lanes, rule A);
rivals htarget, htile (the valid set), clamp-value (values past the target clamped to its last
pixel), gate-miss (the 32 x 16 gate row: slot (31, 15) not stored and the lane bits swapped),
vfar (V rows: clip x 40 units off), ceil (twins: CEIL's band), fault (every pix_posstore row
faults on the 3D side), nodump (the depth dump is not written).
"""
import gzip
import os
import shlex
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(KP, "score"))
import score_q291 as M  # noqa: E402

FAULT3D = ("gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90100 at 0x10000016 "
           "(PD 0x30d6e000) stalls job 86, recovering")
SCRATCH_AT = 0x3E00B000
RIVALS = ("htarget", "htile", "clamp-value", "gate-miss", "vfar", "ceil", "fault", "nodump")


def _a(argv):
    return list(argv)


def handles(tool, argv):
    a = _a(argv)
    if not a:
        return False
    if a[0] == "probe" and "--tri" in a:
        return os.path.basename(a[-1]) in ("q291_pos.bin", "q291_vtx.bin")
    if a[0] == "tri" and "--depth" in a and "--height" in a:
        return int(a[a.index("--height") + 1]) < 16
    return False


def _row(a):
    return M.parse_row(" ".join(shlex.quote(x) for x in a))


def _probe(a, tok):
    r = _row(a)
    name = os.path.basename(a[-1])[:-4]
    W, H = r["W"], r["H"]
    v = M.vertices256(r)
    ms = M.model_sets(r)
    store = r["kind"] == "store"
    slots = ["vtxuse " if r["vtxuse"] else "", "pixel pixpds replaced"]
    out = ["programs asm", f"probe {name}: scratch at 0x{SCRATCH_AT:08x} (64 KiB)",
           f"probe {name}: tri {W}x{H}" + (f" ({r['coords']} coordinates)" if r["coords"] else "")
           + ", " + "".join(slots)]
    if r["full"]:
        out.append(f"probe {name}: triangle (0,0) ({3 * W},0) (0,{3 * H})")
    if r["v256"]:
        out.append(f"probe {name}: vertices256 " + " ".join(str(x) for x in r["v256"]))
    if store and "fault" in tok:
        out.append(f"probe {name}: failed: job faulted, context lost (Input/output error)")
        out.append(f"probe {name}: scratch unchanged")
        return dict(out="\n".join(out) + "\n", err="", rc=3, kmsg=[FAULT3D])
    # the image: o0 = pa0 at covered target pixels (both pixel programs end with o0 = pa0)
    def pa0(x, y):
        if r["set"] == "V":
            return 0
        return M.f32(x + 0.5)
    img = [[pa0(x, y) if M.covered(v, x, y) else M.BG_COLOUR for x in range(W)] for y in range(H)]
    flat = [w for row in img for w in row]
    cnt = {}
    for w in flat:
        cnt[w] = cnt.get(w, 0) + 1
    order = sorted(cnt, key=lambda w: -cnt[w])
    if len(order) == 1:
        out.append(f"probe {name}: o0 0x{order[0]:08x} ({len(flat)} of {len(flat)})")
    else:
        s = "".join(f" 0x{w:08x} x{cnt[w]}" for w in order[:4])
        rest = sum(cnt[w] for w in order[4:])
        out.append(f"probe {name}: o0 mixed{s}" + (f" other x{rest}" if rest else ""))
    if "--pixels" in a:
        out += [f"probe {name}: row {y}: " + " ".join(f"{w:08x}" for w in img[y]) for y in range(H)]
    if store:
        model = "H-TARGET" if "htarget" in tok else ("H-TILE" if "htile" in tok else "H-BAND")
        valid = set(ms[model])
        gate_row = W == 32 and H == 16 and r["full"] and r["set"] == "P"
        if "gate-miss" in tok and gate_row:
            valid.discard((31, 15))
        sc = {}
        for (x, y) in M.quads(valid):          # dword 0: every instance of a touched quad (E111)
            sc[4 * M.slot(x, y)] = M.f32(x + 0.5) if r["set"] == "P" else 0
        for (x, y) in valid:
            s = M.slot(x, y)
            if r["set"] == "P":
                xx, yy = (min(x, W - 1), min(y, H - 1)) if "clamp-value" in tok else (x, y)
                d1, d2 = M.f32(xx + 0.5), M.f32(yy + 0.5)
            else:
                d1 = 0
                d2 = M.f32((2 * x + 1) / W - 1 + (40 * 2 ** -23 if "vfar" in tok else 0))
            ln = M.lane(x, y)
            if "gate-miss" in tok and gate_row:
                ln = (ln >> 1) | (ln & 1) << 1
            sc[4 * s + 1], sc[4 * s + 2], sc[4 * s + 3] = d1, d2, M.LANE_TAG | ln
        out += [f"probe {name}: scratch +0x{4 * i:03x} 0x{sc[i]:08x}" for i in sorted(sc)
                if sc[i] != (0xD0000000 | i)]
    return dict(out="\n".join(out) + "\n", err="", rc=0, kmsg=[])


def _depth(a, tok):
    W, H = int(a[a.index("--width") + 1]), int(a[a.index("--height") + 1])
    pages = int(a[a.index("--depth-pages") + 1])
    ctl = int(a[a.index("--depth-ctl") + 1], 16)
    rule = "CEIL" if "ceil" in tok else "A"
    words = [M.DEPTH_FILL] * (pages * 1024)
    aw, ah = M.area_wh(W, H)
    band = M.band_set(rule, W, H)
    for y in range(ah):
        for x in range(aw):
            words[M.dword_index(x, y, W)] = 0x3E800000 + x + y if (x, y) in band else M.DEPTH_BG
    ddir = a[a.index("--depth-dump") + 1]
    out = [f"tri: render context for targets up to {W}x{H}",
           f"depth: 0x3e001000 {pages} pages, fill 0xdeadbeef, base 0x3e000000, control 0x{ctl:08x}",
           f"tri: triangle (0,0) ({3 * W},0) (0,{3 * H}), depth 0.25 0.75 0.25", "job: ok",
           f"depth #1: {pages * 1024} dwords, {len(band)} changed"]
    if os.path.isdir(ddir) and "nodump" not in tok:
        with open(os.path.join(ddir, "depth.1.bin"), "wb") as f:
            f.write(struct.pack("<%dI" % len(words), *words))
    else:
        out.append("depth #1: --depth-dump: No such file or directory")
    out += [f"target: {W}x{H} hash 0xde21ed09441e14a5", f"diff: 0 of {W * H} pixels",
            "outside: 0 dwords", "layout: fb 0x3e012000",
            f"tri {W}x{H} #1: {W * H} triangle, 0 background, 0 other; wrong 0 inside, 0 outside, "
            "0 at edges; 0 if flipped; guard 0", "tri: 1 renders ok"]
    return dict(out="\n".join(out) + "\n", err="", rc=0, kmsg=[])


def answer(tool, argv, tokens):
    a = _a(argv)
    tok = set(tokens) if tokens else {"model"}
    if a[0] == "probe":
        return _probe(a, tok)
    return _depth(a, tok)


def _gz(path, data):
    with open(path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as f:
        f.write(data)


def kept(d, stage, tokens=("model",), kp=KP):
    """A kept stage directory as run_stage.sh writes it, every row of tables/STAGE.txt answered by
    this world from its argv ($W a fresh work dir with depth/ and dump/, $S the session's bins/)."""
    os.makedirs(d, exist_ok=True)
    head = "name\tstage\tset\trisk\tknobs\ttool\targs\trc\tclass\tfault_req\tfault_word\tfree_kb\n"
    lines = [head]
    for ln in open(os.path.join(kp, "tables", stage + ".txt")).read().splitlines():
        if not ln or ln.startswith("#"):
            continue
        name, sset, risk, knobs, tl, args = ln.split("|", 5)
        w = tempfile.mkdtemp(prefix="w.", dir=d)
        os.makedirs(os.path.join(w, "depth"))
        os.makedirs(os.path.join(w, "dump"))
        argv = shlex.split(args.replace("$W", w).replace("$S", os.path.join(kp, "bins")))
        assert handles(tl, argv), name
        res = answer(tl, argv, set(tokens))
        for suf, txt in ((".txt", res["out"]), (".err", res["err"]),
                         (".dmesg", "\n".join(res["kmsg"]))):
            _gz(os.path.join(d, name + suf + ".gz"), txt.encode())
        for sub in ("depth", "dump"):
            for fn in sorted(os.listdir(os.path.join(w, sub))):
                with open(os.path.join(w, sub, fn), "rb") as src:
                    _gz(os.path.join(d, f"{name}.{fn}.gz"), src.read())
        for sub in ("depth", "dump"):
            for fn in os.listdir(os.path.join(w, sub)):
                os.remove(os.path.join(w, sub, fn))
            os.rmdir(os.path.join(w, sub))
        os.rmdir(w)
        rc = res["rc"]
        cls = "fault" if res["kmsg"] else ("ok" if rc == 0 or (rc == 1 and "diff:" in res["out"])
                                           else "fail")
        fr, fw = ("256", "0x10000016") if res["kmsg"] else ("-", "-")
        lines.append("\t".join([name, stage, sset, risk, knobs, tl, args, str(rc), cls, fr, fw,
                                "999999"]) + "\n")
    with open(os.path.join(d, "cases.tsv"), "w") as f:
        f.writelines(lines)
    return d


if __name__ == "__main__":
    print(__doc__)
