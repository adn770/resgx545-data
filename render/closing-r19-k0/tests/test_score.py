# SPDX-License-Identifier: MIT
"""r19-k0: the frozen scorer replayed. k0 on the kept B60AB0B4 twins (r13-dpm pr2-c1/c4, r10-dpm
a0-cal-2048, r13-zls zb-c-ctl) with the geometry rows from the mock: every control PASS and H-SAME
held where the twin gives the value; it must FAIL on a twin that is not the row's (pr2-c4 in the
place of pr2-c1, a depth store one dword short). f0 on the mock's worlds: model (H-UPD) passes the
controls and holds H-UPD, H-STORE and H-GEO0; ign fails f0-same's control; late passes the controls
and fails H-UPD at f0-down."""
import os
import subprocess
import sys

from common import KP, R10, R13, Z13, kept_dir, mock_job, pin, table

PY = sys.executable


def score(*args):
    r = subprocess.run([PY, str(KP / "score/score.py"), *map(str, args)], capture_output=True,
                       text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def k0_jobs(tmp, swap=False, short=False):
    pr1 = f"{R13}/pr2-c4-1.txt.gz" if swap else f"{R13}/pr2-c1-1.txt.gz"
    store = pin(f"{Z13}/zb-c-ctl.depth-store.1.bin.gz")
    if short:
        store = store[:4 * 2047] + (0xDEADBEEF).to_bytes(4, "little") + store[4 * 2048:]
    z = {".txt": pin(f"{Z13}/zb-c-ctl.txt.gz"), ".depth-store.1.bin": store}
    jobs = {"k0-pr1-1": (3, {".txt": pin(pr1)}),
            "k0-pr1-2": (3, {".txt": pin(f"{R13}/pr2-c1-2.txt.gz")}),
            "k0-pr4": (3, {".txt": pin(f"{R13}/pr2-c4-2.txt.gz")}),
            "k0-a0": (3, {".txt": pin(f"{R10}/a0-cal-2048.txt.gz"),
                          ".p1139-green.param.bin": pin(f"{R10}/a0-cal-2048.p1139-green.param.bin.gz"),
                          ".p1139-green.tadata.bin": pin(f"{R10}/a0-cal-2048.p1139-green.tadata.bin.gz")}),
            "k0-z-t10": (0, z), "k0-z-t18b": (0, z)}
    return {n: jobs[n] for n in table("k0")}


def hooked(d, jobs):
    """readings.tsv as the runner writes it: each control's hook words (run/hooks.sh rd_words)."""
    import read as R
    lines = ["name\tkeys\treading"]
    for n, r in table("k0").items():
        if r["set"] == "control":
            rd = R.reading(str(d), n)
            keys = next(w[6:] for w in r["knobs"].split() if w.startswith("reads:"))
            lines.append(f"{n}\t{keys.replace(',', ' ')}\t" +
                         " ".join(f"{k}={v}" for k, v in R.words(rd).items()))
    (d / "readings.tsv").write_text("\n".join(lines) + "\n")
    for n in table("k0"):           # the runner keeps no file the stage does not declare
        for f in d.glob(f"{n}.*"):
            if not f.name.endswith(".txt"):
                f.unlink()
    return d


def k0_kept(path, **kw):
    return hooked(kept_dir(path, "k0", k0_jobs(path.parent, **kw)), None)


def kg_kept(path, world="model"):
    rows = table("kg")
    return kept_dir(path, "kg", {n: mock_job(r, (world,), path.parent / "m" / n) for n, r in rows.items()})


def test_k0_holds_on_kept_twins(tmp_path):
    out = score("k0", k0_kept(tmp_path / "k0"))
    assert out.count(": PASS") == 5, out
    assert ": FAILED" not in out and " 0 FAILED" in out, out
    assert "SUMMARY: k0: H-SAME: H-SAME holds" in out, out
    assert "ROW k0-a0 [H-SAME, control]: held: param" in out
    out = score("kg", kg_kept(tmp_path / "kg"))
    assert out.count(": PASS") == 2 and ": FAILED" not in out, out
    assert "ROW k0-geo-t18b-2 [H-SAME, heldout]: held: same" in out, out


def test_k0_fails_on_a_wrong_twin(tmp_path):
    out = score("k0", k0_kept(tmp_path / "a" / "k0", swap=True))
    assert "CONTROL k0-pr1-1:" in out and "FAILED" in out.split("CONTROL k0-pr1-1:")[1].splitlines()[0]
    out = score("k0", k0_kept(tmp_path / "b" / "k0", short=True))
    line = out.split("CONTROL k0-z-t10:")[1].splitlines()[0]
    assert "FAILED" in line, out
    assert "gate" not in out


def f0_run(tmp, world):
    rows = table("f0")
    jobs = {n: mock_job(r, (world,), tmp / world / n) for n, r in rows.items()}
    root = tmp / world / "att"
    kept_dir(root / "f0", "f0", jobs)
    kg_kept(root / "kg", world)
    return score("f0", root / "f0", root)


def test_f0_model(tmp_path):
    out = f0_run(tmp_path, "model")
    assert out.count(": PASS") == 4, out
    for m in ("H-UPD", "H-STORE"):
        assert f"SUMMARY: f0: {m}: {m} holds" in out, out
    assert "ROW f0-geo f0-up-1 [H-GEO0, control]: held" in out, out
    assert "SUMMARY: f0: H-STICK: H-STICK holds is not supported" in out, out


def test_f0_ign_fails_the_control(tmp_path):
    out = f0_run(tmp_path, "ign")
    assert "FAILED" in out.split("CONTROL f0-same-1:")[1].splitlines()[0], out


def test_f0_late(tmp_path):
    out = f0_run(tmp_path, "late")
    assert out.count(": PASS") == 4, out
    assert "ROW f0-down-1 [H-UPD, heldout]: FAILED: ovf2" in out, out
    assert "ROW f0-down-1 [H-LATE, heldout]: held: ovf2" in out, out


def gate(stage, root):
    return subprocess.run([PY, str(KP / "score/score.py"), "gate", stage, str(root)],
                          capture_output=True, text=True)


def test_gate(tmp_path):
    d = tmp_path / "att"
    k0_kept(d / "k0")
    assert gate("kg", d).returncode == 0
    assert gate("f0", d).returncode == 1           # kg has not run
    kg_kept(d / "kg")
    r = gate("f0", d)
    assert r.returncode == 0, r.stdout
    e = tmp_path / "bad"
    k0_kept(e / "k0", short=True)
    kg_kept(e / "kg")
    assert gate("kg", e).returncode == 1 and gate("f0", e).returncode == 1
    assert os.path.isdir(d / "k0")
