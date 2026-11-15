# SPDX-License-Identifier: MIT
"""The scorer on kept records it must hold on and must fail on (resgx545-data at the frozen data
commit, pinned in session.toml): E1087's o1-big-a (a 1024x768 owner at P 0x422, both copies, its
words.101 and ta3d.101), E1084's o2-p30 (not raised, lists after) and o2-c-a (P 0x28, raised, zero
after). An empty copy after the close (E1085) is cannot tell; owt's kick rule on made timelines."""
import gzip
import os
import struct
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "score"))
sys.path.insert(0, os.path.join(KP, "kit"))
import kitscore as K  # noqa: E402
import score as S  # noqa: E402

DATA = os.environ.get("RESGX545_DATA_REPO", os.path.expanduser("~/src/resgx545-data"))
DATA_COMMIT = "ba3990f01eb2b2a29fce03c9f48dd071d89b34e6"
OWN1 = "render/closing-r19-own1b/out/20261114-230658/own1/"
OWN2 = "render/closing-r19-own/out/20261114-223625/own2/"


def rec(path):
    r = subprocess.run(["git", "-C", DATA, "show", f"{DATA_COMMIT}:{path}.gz"], capture_output=True)
    assert r.returncode == 0, r.stderr
    return gzip.decompress(r.stdout)


BIG = {k: rec(OWN1 + "o1-big-a." + k) for k in ("kept.1.bin", "kept.closed.1.bin", "ta3d.101.bin")}
WORDS = rec(OWN1 + "o1-big-a.words.101.txt").decode()
P30 = {k: rec(OWN2 + "o2-p30." + k) for k in ("kept.1.bin", "kept.closed.1.bin", "ta3d.101.bin")}
CA = {k: rec(OWN2 + "o2-c-a." + k) for k in ("kept.1.bin", "kept.closed.1.bin", "ta3d.101.bin")}
O = 0x20406000


def tl(seq, regs=(0x62c, 0x634, 0x694, 0x698)):
    out = ["timeline: regs " + " ".join(f"0x{r:04x}" for r in regs) + " samples 1 seconds 0"]
    for i, (b, t) in enumerate(seq):
        v = {0x62c: b, 0x694: t, 0x698: t}
        out.append(f"tl {i * 1000} " + " ".join(f"{v.get(r, 0):08x}" for r in regs))
    return "\n".join(out) + "\n"


TA = tl([(O, 0), (O, 4), (O + 0x400000, 4), (O, 2), (O + 0x400000, 1)])
END = tl([(O, 0), (O, 4), (O + 0x400000, 4), (O + 0x400000, 1), (O, 2)])


def kept_dir(tmp, stage, files, reading, text=""):
    """the runner's kept directory: files {name: {suffix: bytes}} (a row not there did not run)"""
    hdr = "\t".join(K.COLUMNS)
    lines = [hdr]
    for r in K.table(KP, stage):
        if r["name"] not in files:
            continue
        lines.append("\t".join([r["name"], stage, r["set"], r["risk"], " ".join(r["knobs"]),
                                r["tool"], r["args"], "0", "ok", "-", "-", "5000000"]))
        for k, b in files[r["name"]].items():
            with gzip.open(os.path.join(tmp, f"{r['name']}.{k}.gz"), "wb") as f:
                f.write(b)
        with open(os.path.join(tmp, r["name"] + ".txt"), "w") as f:
            f.write("tri: 1 renders ok\n" + text)
        with open(os.path.join(tmp, r["name"] + ".words.101.txt"), "w") as f:
            f.write(WORDS)
    open(os.path.join(tmp, "cases.tsv"), "w").write("\n".join(lines) + "\n")
    open(os.path.join(tmp, "void.tsv"), "w").write(hdr + "\n")
    open(os.path.join(tmp, "readings.tsv"), "w").write(
        "name\tkeys\treading\n" + "".join(f"{n}\tovf kept size\t{v}\n" for n, v in reading.items()))
    return tmp


def run(stage, d):
    controls, rows, lines = S.verdicts(stage, d)
    return controls, rows, "\n".join(lines)


def moved_cover(b, mts):
    x = bytearray(b)
    x[6 * 4096:7 * 4096] = bytes(4096)
    for k, m in enumerate(mts):
        struct.pack_into("<2I", x, 6 * 4096 + 8 * m, (1 << 16) | (2 + k), 2 + k)
    return bytes(x)


def test_ow_holds_h_second_on_e1087(tmp_path):
    f = {n: BIG for n in ("ow-c", "ow-m1-a", "ow-m1-b", "ow-m2")}
    controls, rows, text = run("ow", kept_dir(str(tmp_path), "ow", f, {"ow-c": "ovf=0 kept=2 size=69632"}))
    assert controls == {"ow-c": True}, text
    assert rows == [("ow", True)] * 3 and "H-SECOND 3" in text, text


def test_ow_h_owner_and_failures(tmp_path):
    own = dict(BIG, **{"kept.1.bin": moved_cover(BIG["kept.1.bin"], [0, 1, 2, 3, 4, 5, 6, 8, 9, 12])})
    f = {"ow-c": BIG, "ow-m1-a": own, "ow-m1-b": P30, "ow-m2": own}
    controls, rows, text = run("ow", kept_dir(str(tmp_path), "ow", f, {"ow-c": "ovf=0 kept=2 size=69632"}))
    assert rows == [("ow", False)] * 3, text
    assert "H-OWNER 1" in text and "fits none" in text


def test_ow_control_fails_on_other_pages(tmp_path):
    f = {"ow-c": P30}
    controls, rows, text = run("ow", kept_dir(str(tmp_path), "ow", f, {"ow-c": "ovf=0 kept=2 size=69632"}))
    assert controls == {"ow-c": False}, text


def test_empty_copy_after_the_close_is_cannot_tell(tmp_path):
    e = dict(BIG, **{"kept.closed.1.bin": b""})
    f = {"ow-c": e, "ow-m1-a": e, "ow-m1-b": BIG}
    controls, rows, text = run("ow", kept_dir(str(tmp_path), "ow", f, {"ow-c": "ovf=0 kept=1 size=0"}))
    assert controls == {"ow-c": None} and rows == [("ow", None), ("ow", True), ("ow", None)], text


def test_owp_holds_on_e1084(tmp_path):
    f = {"owp-30-a": P30, "owp-30-b": P30, "owp-30m": P30, "owp-2c": CA, "owp-34": P30}
    controls, rows, text = run("owp", kept_dir(str(tmp_path), "owp", f, {"owp-30-a": "ovf=1 kept=2 size=69632"}))
    assert controls == {"owp-30-a": True}, text
    assert [v for g, v in rows if g == "owp"] == [True] * 5, text
    assert [v for g, v in rows if g == "owpw"] == [True], text


def test_owp_fails(tmp_path):
    # not raised with a zero page; raised with lists; the moved owner's lists (H-OWNER)
    zero = dict(P30, **{"kept.1.bin": bytes(0x11000)})
    lists = dict(CA, **{"kept.1.bin": P30["kept.1.bin"]})
    own = dict(P30, **{"kept.1.bin": moved_cover(P30["kept.1.bin"], [0, 1, 2, 3])})
    f = {"owp-30-a": P30, "owp-30-b": zero, "owp-30m": own, "owp-2c": lists, "owp-34": zero}
    controls, rows, text = run("owp", kept_dir(str(tmp_path), "owp", f, {"owp-30-a": "ovf=1 kept=2 size=69632"}))
    assert [v for g, v in rows if g == "owp"] == [True, False, True, False, False], text
    assert [v for g, v in rows if g == "owpw"] == [False] and "H-OWNER" in text, text


def test_owt_kick(tmp_path):
    assert S.kick(TA, O) == "ta" and S.kick(END, O) == "end"
    assert S.kick(tl([(O, 0), (O, 4)]), O).startswith("cannot tell")
    assert S.kick("", O).startswith("cannot tell") and S.kick(TA, None).startswith("cannot tell")
    for text, want in ((TA, True), (END, False)):
        d = tmp_path / str(want)
        os.makedirs(d)
        controls, rows, out = run("owt", kept_dir(str(d), "owt", {"owt-a": BIG, "owt-b": BIG},
                                                  {"owt-a": "ovf=0 kept=2 size=69632"}, text))
        assert controls == {"owt-a": True} and rows == [("owt", want)] * 2, out


def test_required_is_what_is_read():
    for st in ("ow", "owt", "owp"):
        assert set(S.REQUIRED[st]) >= {".txt", ".kept.closed.1.bin", ".kept.1.bin",
                                        ".words.101.txt", ".ta3d.101.bin", "cases.tsv"}
