#!/usr/bin/env python3
"""test_gen.py: gen/g7gen.py is deterministic and faithful.
  1. a second run in a scratch copy writes the same tables, predictions, TABLES.md, stages.txt, controls.tsv and programs, byte for byte;
  2. the iteration programs equal E606's (the dataset's manifest-1138.sha256), the texture control program equals E725's
     stage-bin (asserted in the generator too), every program fits the tool's 256 USSE words;
  3. the frozen predictions reproduce the records' kept values (E884 hashes, E606 hashes and dump sha256s, E680 hash) and the
     models give them (asserted in the generator: a mismatch makes it fail);
  4. every control declares a reading its row can produce (scorekit.refuse_unreadable, run by the generator) and a control that
     reads nothing or reads `dump` on a colour-only row is refused;
  5. the generated cases keep their envelope: inside the target, a covered pixel, gradient below 0.03, range below 0.05."""
import filecmp
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
KP = os.path.dirname(HERE)
PY = sys.executable
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "score"))
import models as M  # noqa: E402
import scorekit as SK  # noqa: E402

bad = n = 0


def check(c, what):
    global bad, n
    n += 1
    print(("ok   " if c else "FAIL ") + what)
    bad += 0 if c else 1


T = tempfile.mkdtemp(prefix="gen.", dir=os.path.join(KP, "debug"))
for d in ("gen", "templates", "score"):
    shutil.copytree(os.path.join(KP, d), os.path.join(T, d), ignore=shutil.ignore_patterns("__pycache__"))
for d in ("tables", "predictions", "bins", "debug"):
    os.makedirs(os.path.join(T, d), exist_ok=True)
os.symlink(os.path.join(KP, "debug/asm"), os.path.join(T, "debug/asm"))
r = subprocess.run([PY, os.path.join(T, "gen/g7gen.py")], capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
check(r.returncode == 0, "the generator runs in a scratch copy (its asserts against the kept records pass): " + r.stdout.strip()[-80:])
same = []
for d in ("tables", "predictions", "bins"):
    names = sorted(os.listdir(os.path.join(KP, d)))
    m, mis, err = filecmp.cmpfiles(os.path.join(KP, d), os.path.join(T, d), names, shallow=False)
    same.append(not mis and not err and sorted(os.listdir(os.path.join(T, d))) == names)
for f in ("TABLES.md", "stages.txt", "gen/data/controls.tsv"):
    same.append(filecmp.cmp(os.path.join(KP, f), os.path.join(T, f), shallow=False))
check(all(same), "a second run writes the same tables, predictions, programs, TABLES.md, stages.txt and controls.tsv")

man = {ln.split()[1].split("/")[-1]: ln.split()[0] for ln in open("/Users/jtorra/src/resgx545-data/isp/arith-1138/manifest-1138.sha256") if "stage-bins/" in ln}
for b in ("p1138-it-a0__0.bin", "pix_pa0.bin", "vtx_attr_zx.bin"):
    check(hashlib.sha256(open(os.path.join(KP, "bins", b), "rb").read()).hexdigest() == man[b], "%s is E606's (manifest-1138.sha256)" % b)
check(open(os.path.join(KP, "bins/r7g-ty3-32x16.bin"), "rb").read() == open("/Users/jtorra/src/resgx545-data/texture/p1141/stage-bins/p1141-types__2.bin", "rb").read(),
      "the texture control program is E725's p1141-types__2.bin byte for byte")
check(all(os.path.getsize(os.path.join(KP, "bins", b)) // 8 <= 256 for b in os.listdir(os.path.join(KP, "bins")) if b.endswith(".bin")),
      "every program fits PROBE_MAX_WORDS (256 USSE words)")

P = {}
for st in ("xf", "zd", "zi", "zf", "zs"):
    for ln in open(os.path.join(KP, "predictions", st + ".tsv")).read().splitlines()[1:]:
        c, q, v, m, s = ln.split("\t")
        P[(c, q, m)] = v
check(P[("xf-ctl-128x64-x10", "hash", "E884")] == "0xa817f56116104325" and P[("xf-base-128x64", "hash", "E884")] == "0xf7befd67a3c8e325",
      "xf controls: E884's kept hashes")
check(P[("zi-ctl-e680-1024x768", "hash", "E680")] == "0x2b7de99c1a459850", "zi's E680 control: case 1400246's kept hash")

ctl = [ln.rstrip("\n").split("\t") for ln in open(os.path.join(KP, "gen/data/controls.tsv"))][1:]
rows = {ln.split("|")[0]: ln for st in ("xf", "tx", "zd", "zi", "zf", "zs") for ln in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines() if ln and not ln.startswith("#")}
sys.path.insert(0, os.path.join(KP, "gen"))
import g7gen as G  # noqa: E402
check(not SK.control_read_problems({n_: (r_.split(), rows[n_]) for n_, _, r_ in ctl}, G.producible), "every control's reading is producible (%d controls)" % len(ctl))
probs = SK.control_read_problems({"zi-ctl-e680-1024x768": (("dump",), rows["zi-ctl-e680-1024x768"]), "xf-base-128x64": ((), rows["xf-base-128x64"])}, G.producible)
check(len(probs) == 2, "a control reading `dump` on a colour-only row and one reading nothing are refused: " + "; ".join(probs)[:120])
nset = {}
for name, ln in rows.items():
    s = ln.split("|")
    nset.setdefault(s[1], 0)
    nset[s[1]] += 1
for st in ("zd", "zi", "zf"):
    okc = True
    for ln in open(os.path.join(KP, "tables", st + ".txt")).read().splitlines():
        if ln.startswith("#") or "-ctl-" in ln:
            continue
        a = ln.split("|", 5)[5]
        import shlex
        t = shlex.split(a)
        w, h = int(t[t.index("--width") + 1]), int(t[t.index("--height") + 1])
        v = [int(x) for x in t[t.index("--tri-v") + 1].split(",")]
        z = [M.Fraction(x) for x in t[t.index("--tri-z") + 1].split(",")]
        inside = all(256 <= v[i] <= (w - 1) * 256 for i in (0, 2, 4)) and all(256 <= v[i] <= (h - 1) * 256 for i in (1, 3, 5))
        okc = okc and inside and M.cover(v, w, h).any() and M.gradient(v, z) < 0.03 and M.value_range_per_root_area(v, z) < 0.05
    check(okc, "%s: every case inside the target, a pixel covered, gradient below 0.03, clip-z range per root area below 0.05" % st)
print("%d of %d gen checks" % (n - bad, n))
sys.exit(1 if bad else 0)
