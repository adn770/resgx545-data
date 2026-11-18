# SPDX-License-Identifier: MIT
"""mock/world.py: r35-pk's argv-driven fake laptop for kit/session.py mock. answer() sees the
tool's name, the argv and the world's tokens, never a case name: a row is named by its program
(colour.bin or ramp_xy.bin), its sideband's pack mode and its word 11 (--cmd 11=V). As strict as
sgxfive-test (resgx545 a581c06) on these forms: an option `probe` does not take, a missing value,
a second program, a --cmd other than word 11, a --sideband without an eot slot, a ramp row without
its pixpds (12 data dwords) and vtxuse slots and --vtx-coords 2, or a file that is not there is
refused (rc 2, usage).

Images: a colour row is its frozen control image (E031's kept image); a ramp row is synthesised
from the ramp's image by construction (gen/pk.py): mode 0 and the ARGB8888-like modes store it as
it is, modes 3 to 6 pack it by the world's rounding rule (gen/pk.py image16), r3's words follow
H-1136 (gen/pk.py rel1136), modes 9 and 10 store the colours in the first quarter or half, 12 and
13 every second or fourth dword and past the target into the scratch (1536 and 2816 dwords, E031).

Worlds (EXPECT: the driver's status and each stage's runner status; a stage whose gate closed is
skipped, so absent):
  model     H-RAMP, H-E031, H-E1136, H-RZ, H-AS0, H-WHOLE, H-1136 hold: 0 everywhere
  rn, rne, scale   the narrowed modes round by H-RN, H-RNE or H-SCALE: 0 everywhere
  alt       the rivals: each ARGB8888-like mode but 0 changes a green bit (H-AS0-PART), mode 9
            and mode 13's scratch store narrowed values (H-NARROW), r3's mode 5 rows ignore bit 25
            (H-LOWDEP): 0
  s0diff    E031's mode 4 colour image reads one alpha bit flipped: s0's control FAILED, so the
            later stages are skipped (their gate on s0 closes): 0
  ctlfail   (tests only, not a mock world) the ramp's mode 0 and mode 4 controls fail
  s0nopix   s0's first control prints no pixel rows: the premise stops s0 (25), which ends the
            session (on_stop = "end")
  r1nopix   r1's mode 9 and 10 rows print no pixel rows: the second stops r1 by its rule (24);
            r2, r3 and pw run: 0
  pwfault   mode 12's first ramp row faults (a BIF fault latched): pw stops (4), the session (4)
  r2hang    r2's mode 40 row never returns (timeout rc 124): r2 stops (6)
"""
import os

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGES = ("s0", "r1", "r2", "r3", "pw")
EXPECT = {"model": (0, {s: 0 for s in STAGES}),
          "rn": (0, {s: 0 for s in STAGES}),
          "rne": (0, {s: 0 for s in STAGES}),
          "scale": (0, {s: 0 for s in STAGES}),
          "alt": (0, {s: 0 for s in STAGES}),
          "s0diff": (0, {"s0": 0}),
          "s0nopix": (25, {"s0": 25}),
          "r1nopix": (0, {"s0": 0, "r1": 24, "r2": 0, "r3": 0, "pw": 0}),
          "pwfault": (4, {"s0": 0, "r1": 0, "r2": 0, "r3": 0, "pw": 4}),
          "r2hang": (6, {"s0": 0, "r1": 0, "r2": 6})}
USAGE = dict(rc=2, err="usage: sgxfive-test [--mock] COMMAND ... (see the source's header)\n")
VALS = {"--temps", "--tri", "--width", "--height", "--vtx-coords", "--cmd", "--sideband", "--slot"}
FLAGS = {"--pixels"}
SENT = 0xDEADBEEF
SCRATCH = {12: (1536, 8), 13: (2816, 16)}     # E031: dwords past the target and their stride
_C = {}


def gen():
    import sys
    sys.path.insert(0, os.path.join(KP, "gen"))
    sys.dont_write_bytecode = True
    import pk
    return pk


def parse(argv):
    o, pos, i = {}, [], 1
    while i < len(argv):
        a = argv[i]
        if a in FLAGS:
            o.setdefault(a, []).append(True)
            i += 1
        elif a in VALS and i + 1 < len(argv):
            o.setdefault(a, []).append(argv[i + 1])
            i += 2
        elif a.startswith("--"):
            return None
        else:
            pos.append(a)
            i += 1
    return o, pos


def ramp():
    """The ramp's image by construction: s0-m00-ref's frozen image."""
    if "ramp" not in _C:
        p = os.path.join(KP, "predictions", "s0", "s0-m00-ref.H-RAMP.txt")
        _C["ramp"] = [int(t, 16) for t in open(p).read().split()]
    return _C["ramp"]


def colour(mode):
    """E031's kept image of a colour row (s0's or pw's frozen control image)."""
    for st in ("s0", "pw"):
        p = os.path.join(KP, "predictions", st, f"{st}-m{mode:02d}-col.H-E031.txt")
        if os.path.exists(p):
            return [int(t, 16) for t in open(p).read().split()]
    return None


def rule(world):
    Q = gen()
    for w, m in (("rne", "H-RNE"), ("rn", "H-RN"), ("scale", "H-SCALE")):
        if w in world:
            return Q.RULES[m]
    return Q.rz


def image(form, mode, word, world):
    """(target image, {scratch dword index: value}) of a row."""
    Q = gen()
    if form == "colour":
        img = list(colour(mode))
        if "s0diff" in world and mode == 4:
            img[20 * 64 + 30] ^= 0x8000
        return img, {}
    src = ramp()
    if "ctlfail" in world and mode == 0 and word == Q.W080:
        img = list(src)
        img[next(i for i, v in enumerate(src) if v != Q.BG)] ^= 1
        return img, {}
    if mode in Q.FORMATS:
        ref = Q.image16(src, mode, rule(world), Q.W080)
        if word == Q.W080:
            if "ctlfail" in world and mode == 4:
                ref = [v ^ 0x80008000 if v != SENT else v for v in ref]
            return ref, {}
        if mode == 4:
            return Q.rel1136(ref, src, 4, word), {}
        return (ref if "alt" in world and mode == 5 else Q.rel1136(ref, src, mode, word)), {}
    if mode == 0 and word != Q.W080:
        return Q.rel1136(src, src, 0, word), {}
    if mode in (9, 10):
        n = 1024 if mode == 9 else 2048
        img = [src[i] for i in range(n)] + [SENT] * (4096 - n)
        if "alt" in world and mode == 9:
            img[300] &= 0xF0F0F0F0
        return img, {}
    if mode in SCRATCH:
        step = 2 if mode == 12 else 4
        img = [src[i // step] if i % step == 0 else SENT for i in range(4096)]
        n, stride = SCRATCH[mode]
        scr = {k * stride // 4: src[(k * 7) % 4096] for k in range(n)}
        if "alt" in world and mode == 13:
            k = next(iter(scr))
            scr[k] &= 0xF0F0F0F0
        return img, scr
    img = list(src)
    if "alt" in world and mode in Q.ARGB40:
        i = next(i for i, v in enumerate(src) if v != Q.BG)
        img[i] ^= 0x00000100
    return img, {}


def answer(tool, argv, world):
    if tool != "t10" or not argv or argv in (["fill"], ["tri"]):
        return None
    if argv[0] != "probe":
        return USAGE
    r = parse(argv)
    if r is None or len(r[1]) != 1:
        return USAGE
    o, (path,) = r
    one = {k: v[0] for k, v in o.items() if len(v) == 1}
    if (one.get("--temps") != "32" or one.get("--tri") != "pixel" or "--pixels" not in o or
            one.get("--width") != "64" or one.get("--height") != "64" or
            len(o.get("--cmd", [])) != 1 or len(o.get("--sideband", [])) != 1):
        return USAGE
    k, _, v = one["--cmd"].partition("=")
    if k != "11" or not v:
        return USAGE
    word = int(v, 16)
    sb = int(one["--sideband"], 16)
    slots = dict(s.split("=", 1) for s in o.get("--slot", []) if "=" in s)
    form = {"colour.bin": "colour", "ramp_xy.bin": "ramp"}.get(os.path.basename(path))
    if form is None or "eot" not in slots:
        return USAGE
    want = {"eot"} if form == "colour" else {"eot", "pixpds", "vtxuse"}
    if set(slots) != want or (form == "ramp" and (one.get("--vtx-coords") != "2" or
                                                  not slots["pixpds"].endswith(":12"))):
        return USAGE
    if form == "colour" and "--vtx-coords" in o:
        return USAGE
    for f in [path, slots["eot"]] + ([slots["pixpds"][:-3], slots["vtxuse"]]
                                     if form == "ramp" else []):
        if not os.path.isfile(f):
            return dict(rc=2, err="sgxfive-test: %s: No such file or directory\n" % f)
    mode = sb & 0x3F
    case = form
    if "pwfault" in world and form == "ramp" and mode == 12:
        return dict(rc=3, out="probe %s: failed: job faulted\n" % case,
                    kmsg=["sgxfive: BIF fault 0x90004 at 0x1000c016 stalls job 9"],
                    latch=(4, 0x1000c016))
    if "r2hang" in world and form == "ramp" and mode == 40:
        return dict(rc=124, out="")
    out = ["programs asm", "probe %s: scratch at 0x3e006000 (64 KiB)" % case,
           "probe %s: tri 64x64 (command words 11) (sideband 0x%08x), eot pixel replaced"
           % (case, sb)]
    if ("s0nopix" in world and form == "ramp" and mode == 0) or (
            "r1nopix" in world and form == "ramp" and mode in (9, 10)):
        return dict(out="\n".join(out) + "\n")
    img, scr = image(form, mode, word, world)
    out += ["probe %s: row %d: " % (case, y) + " ".join("%08x" % x for x in img[64 * y:64 * y + 64])
            for y in range(64)]
    out += ["probe %s: scratch +0x%03x 0x%08x" % (case, 4 * k, v) for k, v in sorted(scr.items())]
    return dict(out="\n".join(out) + "\n")
