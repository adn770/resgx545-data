# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py on kept records it must hold on and must fail on.

- f1 on E1033's kept stage (render/closing-r13-flag f1, 16 pages): both references PASS (their
  images are the frozen ones), H-FAULTANY held 2 of 2 run, every post hoc form FAILED 2 of 2 (each
  predicts an image at 256 pages; at 16 pages E1033 faulted), f1-zero did not run. The fault rows
  read their page (+0x21000, +0x40000).
- f1 on the model's images (mock world model): H-TWP4096 held 3 of 3, H-FAULTANY FAILED. Must fail:
  E1033's f1-tw32 output as f1-ref-a (a fault where the control must draw): the control FAILED,
  its row cannot tell.
- f2 on E1007's kept 256 x 256 baseline and E959's kept 768 x 640 baseline as the controls (both
  PASS), the planned rows from the mock's fake (H-EVEN's headers, flag on H-LASTBLOCK): H-COVER,
  H-EVEN, H-LASTBLOCK held 4 of 4; R7-BLK FAILED 4; H-HIGHSLOT FAILED on the 768 x 640 rows (the
  256 x 256 rows do not part the flag's rivals). The alt world (flag on H-HIGHSLOT): the reverse. Must
  fail: the 768 x 640 baseline kept as the 256 x 256 control (not its image): that control
  FAILED and its rows cannot tell; every planned row faulted: H-FAULT23 held, the slot and flag
  models cannot tell."""
import gzip
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "mock"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import pins  # noqa: E402
import world as Wd  # noqa: E402

PY = sys.executable
HEAD = "\t".join(K.COLUMNS) + "\n"
R13F = "data:render/closing-r13-flag/out/20261113-220930/f1/"
E1007 = "data:render/closing-r10-geo/out/20261113-103256/q139c/q139c-ctl-256x256"
E959 = "data:render/closing-r9-lgeo/out/20261113-080029/q139b/q139b-ctl-768x640"


def kept(d, stage, rows):
    """rows: [(name, class, out text, dmesg text, {suffix: bytes})] -> a kept stage directory."""
    os.makedirs(d, exist_ok=True)
    t = {r["name"]: r for r in K.table(KP, stage)}
    lines = [HEAD]
    for name, cls, out, dm, extra in rows:
        r = t[name]
        lines.append("\t".join([name, stage, r["set"], r["risk"], " ".join(r["knobs"]), r["tool"],
                                r["args"], "0" if cls == "ok" else "3", cls, "-", "-", "999999"]) + "\n")
        for suf, data in ((".txt", out), (".dmesg", dm), *extra.items()):
            with gzip.open(os.path.join(d, name + suf + ".gz"), "wb") as f:
                f.write(data if isinstance(data, bytes) else data.encode())
    open(os.path.join(d, "cases.tsv"), "w").write("".join(lines))
    open(os.path.join(d, "void.tsv"), "w").write(HEAD)
    open(os.path.join(d, "readings.tsv"), "w").write("name\tkeys\treading\n")
    return d


def score(stage, d):
    """score.py STAGE d; f2 with its dumps (score.py dumps f2 d), f2-kit the kit's own call."""
    argv = ["dumps", "f2", d] if stage == "f2" else ["f2", d] if stage == "f2-kit" else [stage, d]
    r = subprocess.run([PY, "-B", os.path.join(KP, "score/score.py"), *argv], capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def summary(out, stage, model):
    return next(ln for ln in out.splitlines() if ln.startswith(f"SUMMARY: {stage}: ") and f" {model}:" in ln)


def gz(pin):
    return gzip.decompress(pins.blob(pin)).decode(errors="replace")


# ---- f1 ------------------------------------------------------------------------------------
def e1033_rows():
    cls = {"f1-ref-a": "ok", "f1-tw32": "fault", "f1-ref-b": "ok", "f1-small": "fault"}
    rows = []
    for n, c in cls.items():
        dm = gz(R13F + n + ".dmesg.gz") if c == "fault" else ""
        rows.append((n, c, gz(R13F + n + ".txt.gz"), dm, {}))
    return rows


def test_f1_on_e1033(tmp_path):
    out = score("f1", kept(str(tmp_path / "f1"), "f1", e1033_rows()))
    assert "CONTROL f1-ref-a" in out and out.count(": PASS") == 2, out
    assert "(2 of 3 rows decided)" in summary(out, "f1", "H-FAULTANY"), out
    for m in ("H-TWP4096", "H-TWP4128", "H-TWP4096-NS"):
        assert "0 held, 2 FAILED, 1 cannot tell" in summary(out, "f1", m), (m, out)
    assert "'fpage': '+0x21000'" in out and "'fpage': '+0x40000'" in out
    assert "past the scratch" in out


def mock_probe(name, world=frozenset({"model"})):
    a = Wd.f1(["probe", "--temps", "32", "--coords", "--pixels", "--scratch-pages", "256",
               os.path.join(KP, "bins", name + ".bin")], set(world))
    return a["out"]


def test_f1_on_the_model(tmp_path):
    rows = [(n, "ok", mock_probe(n), "", {}) for n in ("f1-ref-a", "f1-tw32", "f1-ref-b", "f1-small", "f1-zero")]
    out = score("f1", kept(str(tmp_path / "f1"), "f1", rows))
    assert "(3 of 3 rows decided)" in summary(out, "f1", "H-TWP4096"), out
    assert "0 held, 3 FAILED" in summary(out, "f1", "H-FAULTANY"), out
    assert "READING f1-zero: 2048 of 2048 pixels name a scratch dword" in out


def test_f1_control_fault_fails(tmp_path):
    rows = e1033_rows()
    rows[0] = ("f1-ref-a", "fault", rows[1][2], rows[1][3], {})
    out = score("f1", kept(str(tmp_path / "f1"), "f1", rows))
    assert "CONTROL f1-ref-a" in out and "FAILED" in out.split("CONTROL f1-ref-a")[1].splitlines()[0]
    assert "ROW f1-tw32 H-FAULTANY" in out and "cannot tell" in out.split("ROW f1-tw32 H-FAULTANY")[1].splitlines()[0]


# ---- f2 ------------------------------------------------------------------------------------
def baseline(pin):
    return (gz(pin + ".txt.gz"), {".tri.param.bin": gzip.decompress(pins.blob(pin + ".tri.param.bin.gz")),
                                  ".tri.tadata.bin": gzip.decompress(pins.blob(pin + ".tri.tadata.bin.gz"))})


def mock_tri(tmp, row, world):
    t = {r["name"]: r for r in K.table(KP, "f2")}[row]
    d = os.path.join(tmp, "w-" + row)
    os.makedirs(d, exist_ok=True)
    argv = t["args"].replace('"$W"', d).split()
    a = Wd.f2(argv, set(world))
    if a.get("latch"):
        return (row, "fault", a["out"], a["kmsg"][0], {})
    files = {suf: open(os.path.join(d, "tri" + suf), "wb").write(b) and b
             for suf, b in ((".param.bin", a["files"][os.path.join(d, "tri.param.bin")]),
                            (".tadata.bin", a["files"][os.path.join(d, "tri.tadata.bin")]))}
    return (row, "ok", a["out"], "", {".tri" + k: v for k, v in files.items()})


def f2_rows(tmp, world=("model",), ctl256=E1007):
    c256, c768 = baseline(ctl256), baseline(E959)
    rows = [("f2-ctl-256", "ok", c256[0], "", c256[1])]
    rows += [mock_tri(tmp, n, world) for n in ("f2-h-256-fx14", "f2-h-256-fx15")]
    rows += [("f2-ctl-768", "ok", c768[0], "", c768[1])]
    rows += [mock_tri(tmp, n, world) for n in ("f2-h-768-fx26", "f2-h-768-fx27")]
    return rows


def test_f2_on_the_kept_baselines_and_the_model(tmp_path):
    out = score("f2", kept(str(tmp_path / "f2"), "f2", f2_rows(str(tmp_path))))
    assert out.count(": PASS") == 2, out
    for m in ("H-COVER", "H-EVEN", "H-LASTBLOCK"):
        assert "(4 of 4 rows decided)" in summary(out, "f2", m), (m, out)
    assert "0 held, 4 FAILED" in summary(out, "f2", "blkrow"), out
    assert "0 held, 4 FAILED" in summary(out, "f2", "H-FAULT23"), out
    assert "2 held, 2 FAILED" in summary(out, "f2", "H-HIGHSLOT"), out


def test_f2_the_kits_call_reads_no_dump(tmp_path):
    """The kit's `score.py f2` (no dump in REQUIRED): ends and the controls' images only."""
    out = score("f2-kit", kept(str(tmp_path / "f2"), "f2", f2_rows(str(tmp_path))))
    assert out.count(": PASS") == 2 and "(4 of 4 rows decided)" in summary(out, "f2", "H-COVER"), out
    assert "SUMMARY: f2: H-EVEN" not in out and "NOTE: f2's slot and flag verdicts" in out
    sys.path.insert(0, os.path.join(KP, "score"))
    import sessioncheck
    import score as Sc
    d = str(tmp_path / "f2")
    assert sessioncheck.kept_problems(d, Sc.REQUIRED["f2"], sessioncheck.kept_rows(d),
                                      lambda: Sc.read_files("f2", d) or Sc.score_f2(d)) == []


def test_f2_highslot_world(tmp_path):
    out = score("f2", kept(str(tmp_path / "f2"), "f2", f2_rows(str(tmp_path), ("alt",))))
    assert "(4 of 4 rows decided)" in summary(out, "f2", "H-HIGHSLOT"), out
    assert "2 held, 2 FAILED" in summary(out, "f2", "H-LASTBLOCK"), out


def test_f2_wrong_baseline_fails(tmp_path):
    out = score("f2", kept(str(tmp_path / "f2"), "f2", f2_rows(str(tmp_path), ctl256=E959)))
    line = next(ln for ln in out.splitlines() if ln.startswith("CONTROL f2-ctl-256"))
    assert line.endswith("FAILED") or line.endswith("cannot tell"), line
    assert "ROW f2-h-256-fx14: slots and flag cannot tell" in out, out


def test_f2_all_faulted(tmp_path):
    out = score("f2", kept(str(tmp_path / "f2"), "f2", f2_rows(str(tmp_path), ("faultany",))))
    assert "(4 of 4 rows decided)" in summary(out, "f2", "H-FAULT23"), out
    for m in ("H-EVEN", "blkrow", "H-LASTBLOCK", "H-HIGHSLOT"):
        assert summary(out, "f2", m).endswith(f"{m}: cannot tell: no row decided"), out
