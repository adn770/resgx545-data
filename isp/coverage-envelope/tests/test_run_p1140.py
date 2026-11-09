import gzip
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "run"))
import run_p1140 as R  # noqa: E402

TOOL = os.path.join(ROOT, "tool/userspace/libsgxfive/build/sgxfive-test")
CASES = R.load_cases(os.path.join(ROOT, "cases-1140.tsv"))


def test_cases_load():
    assert len(CASES) == 1832
    assert {c["set"] for c in CASES} == {"fit", "heldout", "pilot", "repeat"}
    c = CASES[0]
    assert c["set"] == "pilot" and c["v"][:2] == [2048, 2048] and c["unit"] == 8


def test_build_cmd_is_a_colour_only_rle_job():
    c = CASES[1]
    cmd = R.build_cmd(c, "/t/sgxfive-test-1140")
    assert cmd[:5] == ["sudo", "-n", "timeout", "120", "/t/sgxfive-test-1140"] and cmd[5] == "tri"
    assert cmd[cmd.index("--width") + 1] == str(c["w"]) and cmd[cmd.index("--tri-unit") + 1] == str(c["unit"])
    assert cmd[cmd.index("--tri-v") + 1] == ",".join(str(x) for x in c["v"])
    assert "--pixels-rle" in cmd and "--depth" not in cmd and "--poke" not in cmd and "--kpoke" not in cmd


def test_far_cases_are_last_and_ordered():
    ids = [c["id"] for c in CASES]
    assert ids == sorted(ids)
    far = [i for i, c in enumerate(CASES) if c["group"] == "S4"]
    assert far == list(range(len(CASES) - len(far), len(CASES)))


def test_mock_run_keeps_every_job(tmp_path):
    out = tmp_path / "o"
    r = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "run/run_p1140.py"), "--cases", os.path.join(ROOT, "cases-1140.tsv"),
                        "--out", str(out), "--sets", "pilot", "--tool", TOOL, "--mock"], capture_output=True, text=True,
                       timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    rows = [l.split("\t") for l in open(out / "jobs.tsv")]
    assert len(rows) == 6 and all(f[1] == "0" and f[5] == "-" for f in rows), rows
    for f in rows:
        raw = gzip.open(out / "raw" / ("%s.txt.gz" % f[0])).read().decode()
        assert re.search(r"^tri: clip2 0x", raw, re.M) and re.search(r"^rle 0: ", raw, re.M)
        assert "row 0:" not in raw
