# SPDX-License-Identifier: MIT
"""tests/test_score.py: score/score.py on kept records it must hold on and must fail on.

- f1: E566's kept tw32-ctl output as f1-ref-a (the control PASSes) and its kept tw32-t3b14 output
  as f1-tw32 (a fault without a kernel line, as E566 kept it): H-E566 and H-FAULTANY held, H-TWIDX
  and H-TWX-WRAP FAILED, H-TWX cannot tell (no fault page). Must fail: E566's kept tw32-t3b10 output
  as the control (another image): the control FAILED and no headline.
- f2: E383's bit-12 mode 0 run as the control (PASS) and its bit-11 outputs with their kernel
  lines (modes 0, 4, 8, the log's order): H-E383 and H-E383-PAGE held 3 of 3, H-NOFAULT FAILED.
  Must fail: a fault line on another page: H-E383-PAGE FAILED.
- f3: the classes of gen/f3.py's M3 run: M3 held 8 of 8, M1 FAILED on f3-v1c0. Must fail: the
  control completing: controls FAILED.
- the gate: closed after a kept `SGX recovery failed` line of an earlier stage, open without."""
import gzip
import os
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.dont_write_bytecode = True
import f1  # noqa: E402
import f2  # noqa: E402
import f3  # noqa: E402
import kitscore as K  # noqa: E402
import pins  # noqa: E402

PY = sys.executable
E566 = "data:texture/p1132/tx-t3/%s.txt.gz"
HEAD = "\t".join(K.COLUMNS) + "\n"


def kept(d, stage, rows):
    """rows: [(name, class, out text, dmesg text)] -> a kept stage directory."""
    os.makedirs(d, exist_ok=True)
    t = {r["name"]: r for r in K.table(KP, stage)}
    lines = [HEAD]
    for name, cls, out, dm in rows:
        r = t[name]
        lines.append("\t".join([name, stage, r["set"], r["risk"], " ".join(r["knobs"]), r["tool"],
                                r["args"], "0", cls, "-", "-", "999999"]) + "\n")
        for suf, text in ((".txt", out), (".dmesg", dm)):
            with gzip.open(os.path.join(d, name + suf + ".gz"), "wt") as f:
                f.write(text)
    open(os.path.join(d, "cases.tsv"), "w").write("".join(lines))
    open(os.path.join(d, "void.tsv"), "w").write(HEAD)
    open(os.path.join(d, "readings.tsv"), "w").write("name\tkeys\treading\n")
    return d


def score(stage, d, *roots):
    r = subprocess.run([PY, "-B", os.path.join(KP, "score/score.py"), stage, d, *roots],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def summary(out, model):
    return next(ln for ln in out.splitlines() if ln.startswith("SUMMARY:") and f": {model}:" in ln)


def e566(name):
    return gzip.decompress(pins.blob(E566 % name)).decode()


def toks_out(prog, toks):
    return "".join(f"probe {prog}: row {y}: {' '.join(toks[y * 64:(y + 1) * 64])}\n" for y in range(32))


def f1_rows(ctl):
    ref_b = ["%08x" % v for v in f1.image_b("REF")]
    small = ["%08x" % v for v in f1.image_b("H-TWX")]
    return [("f1-ref-a", "ok", e566(ctl), ""), ("f1-tw32", "fault", e566("tw32-t3b14"), ""),
            ("f1-ref-b", "ok", "probe f1-ref-b: scratch at 0x3e003000 (64 KiB)\n" + toks_out("f1-ref-b", ref_b), ""),
            ("f1-small", "ok", "probe f1-small: scratch at 0x3e003000 (64 KiB)\n" + toks_out("f1-small", small), "")]


def test_f1_holds_on_e566(tmp_path):
    out = score("f1", kept(str(tmp_path / "f1"), "f1", f1_rows("tw32-ctl")))
    assert "CONTROL f1-ref-a" in out and "PASS" in out.split("CONTROL f1-ref-a")[1].splitlines()[0]
    assert "not supported: 1 held, 1 FAILED" in summary(out, "H-FAULTANY")
    assert "not supported: 0 held, 2 FAILED" in summary(out, "H-TWX-WRAP")
    assert "(1 of 1 rows decided)" in summary(out, "H-E566")
    assert "not supported: 0 held, 2 FAILED" in summary(out, "H-TWIDX")
    assert "ROW f1-tw32 H-TWX:" in out and "cannot tell" in out.split("ROW f1-tw32 H-TWX:")[1].splitlines()[0]
    assert "(1 of 2 rows decided)" in summary(out, "H-TWX")


def test_f1_fails_on_another_control_image(tmp_path):
    out = score("f1", kept(str(tmp_path / "f1"), "f1", f1_rows("tw32-t3b10")))
    assert "FAILED" in out.split("CONTROL f1-ref-a")[1].splitlines()[0]
    assert all(ln.split(": ", 2)[2].startswith("controls FAILED") for ln in out.splitlines()
               if ln.startswith("SUMMARY:"))


def f2_rows(page_shift=0):
    raw12 = pins.blob(f2.RAW12).decode()
    faults = f2.e383_faults(pins.blob)
    rows = [("f2-ctl", "ok", raw12, "")]
    for m in f2.MODES:
        out = pins.blob(f"{f2.E383}/pbe-sideband-channels-bit11-0a0{m}/raw.txt").decode()
        s, a = faults[m]
        a = f"{int(a, 16) + page_shift:#x}"
        dm = f"[ 1.0] gma500 0000:00:02.0: [drm] *ERROR* sgxfive: BIF fault {s} at {a} (PD 0x5736000) stalls job 1796, recovering\n"
        rows.append((f"f2-b11-m{m}", "fault", out, dm))
    return rows


def test_f2_holds_on_e383(tmp_path):
    out = score("f2", kept(str(tmp_path / "f2"), "f2", f2_rows()))
    assert "PASS" in out.split("CONTROL f2-ctl")[1].splitlines()[0]
    assert "(3 of 3 rows decided)" in summary(out, "H-E383-PAGE")
    assert "(3 of 3 rows decided)" in summary(out, "H-E383")
    assert "0 held, 3 FAILED" in summary(out, "H-NOFAULT")


def test_f2_fails_on_another_page(tmp_path):
    out = score("f2", kept(str(tmp_path / "f2"), "f2", f2_rows(0x1000)))
    assert "0 held, 3 FAILED" in summary(out, "H-E383-PAGE")
    assert "(3 of 3 rows decided)" in summary(out, "H-E383")


def f3_rows(ctl_end="hang"):
    sim = f3.simulate("M3")
    sim["f3-c-b"] = ctl_end
    out = []
    for n, *_ in f3.ROWS:
        dm = "[ 1.0] gma500 0000:00:02.0: [drm] *ERROR* sgxfive: job 12 hung, recovering\n" if sim[n] == "hang" else ""
        out.append((n, sim[n], "job: ok\n" if sim[n] == "ok" else "job: failed: job hung, context lost\n", dm))
    return out


def test_f3_holds_on_m3s_run(tmp_path):
    out = score("f3", kept(str(tmp_path / "f3"), "f3", f3_rows()))
    assert "(8 of 8 rows decided)" in summary(out, "M3")
    assert "7 held, 1 FAILED" in summary(out, "M1")
    assert "2 held, 1 FAILED" in summary(out, "H-C05")


def test_f3_fails_when_the_control_completes(tmp_path):
    out = score("f3", kept(str(tmp_path / "f3"), "f3", f3_rows("ok")))
    assert all(": controls FAILED" in ln for ln in out.splitlines() if ln.startswith("SUMMARY:"))


def test_gate_closes_after_a_failed_recovery(tmp_path):
    root = tmp_path / "att"
    kept(str(root / "f1"), "f1", f1_rows("tw32-ctl"))
    g = lambda st: subprocess.run([PY, "-B", os.path.join(KP, "score/score.py"), "gate", st,
                                   str(root)], capture_output=True, text=True)
    assert g("f2").returncode == 0 and g("f3").returncode == 0
    with gzip.open(root / "f1" / "f1-tw32.dmesg.gz", "wt") as f:
        f.write("gma500 0000:00:02.0: [drm] *ERROR* SGX recovery failed: -110\n")
    assert g("f2").returncode == 1 and g("f3").returncode == 1
