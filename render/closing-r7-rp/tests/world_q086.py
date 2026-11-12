"""world_q086.py: the fake t4 for q086's rows, answering from ARGV ONLY (never a case name).

  handles(tool, argv) -> bool     t4 and `tri ... --aa4`
  answer(tool, argv, tokens)      dict(out, err, rc, kmsg); the 4x render with the words the argv's --kpoke-render lines (else the rule's
                                  R words) and the target size give

World words (FAKE_WORLD split on commas): model (default: H-COV, every frozen prediction holds), hx, hy, harea (the rival rules: a
job completes iff the grid covers in x / in y / by area), fxok (the FX bridge, the closed 64 x 64 words, completes under every rule:
E886 depended on the old module), tafault (a U2-poked row that would fault faults TA side (the FX bridge stays 3D side): BIF fault 0x90004 at 0x20006061), ctlfail
(R controls complete with wrong pixels: diff nonzero, rc 1).  A render with no kpoke (R) always completes (unless ctlfail).
A 3D-side fault: kmsg line (BIF fault 0x90100 at 0x10000016) and out `job: failed: job faulted`, rc 1.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
sys.path[:0] = [os.path.join(KP, "gen")]
import g_q086 as G  # noqa: E402

FAULT3D = "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90100 at 0x10000016 (PD 0x30d6e000) stalls job 86, recovering"
FAULTTA = "gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault 0x90004 at 0x20006061 (PD 0x30d6e000) stalls job 86, recovering"
GREEN = 0xFF00FF00
FXWORDS = {143: 0x00802002, 144: 0x00802002, 146: 4}


def handles(tool, argv):
    return tool == "t4" and argv[:1] == ["tri"] and "--aa4" in argv


def _opt(a, name, cast=str):
    return cast(a[a.index(name) + 1])


def answer(tool, a, tokens):
    W, H = _opt(a, "--width", int), _opt(a, "--height", int)
    kp = {int(i): int(v, 16) for i, v in (re.match(r"1:ta:(\d+)=(0x[0-9a-f]+)$", a[j + 1]).groups()
                                          for j, t in enumerate(a) if t == "--kpoke-render")}
    rule = "H-X" if "hx" in tokens else "H-Y" if "hy" in tokens else "H-AREA" if "harea" in tokens else "H-COV"
    ta = False
    if not kp:
        ok = True
    elif kp == FXWORDS and "fxok" in tokens:
        ok = True
    else:
        ok = G.completes(rule, W, H, kp)
        ta = not ok and "tafault" in tokens and kp != FXWORDS
    head = ["tri: render context for targets up to %dx%d" % (W, H),
            "tri: render context made for 4x targets (DRM_SGXFIVE_CTX_RENDER_AA_4X)"]
    head += ["tri: kpoke before render 1: ta:%d=0x%x" % (i, kp[i]) for i in sorted(kp)]
    wrong = ok and not kp and "ctlfail" in tokens
    pix = ["row %d: %s" % (y, " ".join(["0x%08x" % (GREEN if not (wrong and y == 3) else 0xFF203040)] * W)) for y in range(H)] \
        if "--pixels" in a else []
    if ok and not wrong:
        out = head + ["job: ok", "target: %dx%d hash 0x2" % (W, H), "diff: 0 of %d pixels" % (W * H), "outside: 0 dwords"] + pix + \
            ["tri %dx%d #1: %d triangle, 0 background, 0 other" % (W, H, W * H), "tri: 1 renders ok"]
        return dict(out="\n".join(out) + "\n", err="", rc=0, kmsg=[])
    if wrong:
        out = head + ["job: ok", "target: %dx%d hash 0x4" % (W, H), "diff: %d of %d pixels, first (0, 3) 0xff203040 expected 0xff00ff00" % (W, W * H),
                      "outside: 0 dwords"] + pix + ["tri: 1 renders ok"]
        return dict(out="\n".join(out) + "\n", err="", rc=1, kmsg=[])
    out = head + ["job: failed: job faulted, context lost (Input/output error)", "target: %dx%d hash 0x3" % (W, H),
                  "diff: %d of %d pixels, first (128, 0) 0xdeadbeef expected 0xff00ff00" % (W * H // 2, W * H), "outside: 0 dwords"] + pix + \
        ["tri: FAILED after 0 renders"]
    return dict(out="\n".join(out) + "\n", err="", rc=1, kmsg=[FAULTTA if ta else FAULT3D])
