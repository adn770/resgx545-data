# SPDX-License-Identifier: MIT
"""tests/test_e0.py: control E0 (slot 1 = M1 and job 1's run id, cmd 0) read where LC2 reads it:
in job 1's record (its `slot` and `cmd_after`), as fwtask_run.py read them when job 1 ended and
before job 2 was posted. H3 (r41-n3f-h3, attempt 20261120-161633) read them on the page dumped
after the row: job 2 had been posted (cmd word 6) and was never served (the firmware had stopped),
so E0 failed through the read point, not the hardware, and the frozen rule said CANNOT TELL.
Here: the scorer on H3's kept stage (copied verbatim into tests/h3/, checked against its
raw.sha256), on fabricated attempts with job 2 posted but unserved, and on the kit mock's world
ownstop2 (the fake runner leaves job 2's cmd word 6 on the page as the laptop did)."""
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys

import pytest

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "tests"))
sys.path.insert(0, os.path.join(KP, "gen"))
sys.dont_write_bytecode = True
import attempt  # noqa: E402
import make  # noqa: E402

H3 = os.path.join(KP, "tests/h3/20261120-161633/lc")
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
M1 = 0x5A5A3301
pytestmark = pytest.mark.skipif(make.E0_AT[make.STEP] != "j1rec", reason="LC2 only")


def score(d, stage="lc"):
    r = subprocess.run([sys.executable, "-B", "score/score.py", stage, d], cwd=KP,
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0 and "SUMMARY:" in r.stdout, r.stdout + r.stderr
    return r.stdout


def control(out, k):
    m = re.search(rf"^CONTROL lc1-a:{k}: (.*)$", out, re.M)
    return m and m.group(1)


def kept(d, name):
    return gzip.decompress(open(os.path.join(d, name + ".gz"), "rb").read())


def test_the_h3_copy_is_the_kept_stage():
    """tests/h3/ holds H3's kept stage byte for byte: every file raw.sha256 names, unpacked."""
    want = {}
    for ln in open(os.path.join(H3, "raw.sha256")).read().splitlines():
        name, size, sha = ln.split()
        want[name] = (int(size), sha)
    assert len(want) == 16
    for name, (size, sha) in want.items():
        b = kept(H3, name)
        assert (len(b), hashlib.sha256(b).hexdigest()) == (size, sha), name


def test_h3_s_page_held_job_2_s_posted_command_and_job_1_s_record_its_own():
    """The slip: the page after the row has job 2's cmd word 6 (posted, never served); job 1's
    record has slot 1 = M1, run id 1 and cmd_after 0, read before job 2 was posted."""
    page = json.loads(kept(H3, "lc1-a.own_res.json"))
    page = page["page"] if isinstance(page, dict) else page
    run = json.loads(kept(H3, "lc1-a.txt"))
    r1, r2 = run["records"]
    assert page[1] == 6 and r2["job"]["n"] == 6 and r2["done"] is False and r2["cmd_after"] == 6
    assert r1["done"] is True and r1["cmd_after"] == 0 and r1["slot"][:2] == [M1, 1]
    assert page[0x44:0x46] == [M1, 1]


def test_h3_rescored_with_e0_at_job_1_s_end():
    """For the record only (H3's frozen verdict stays CANNOT TELL): with E0 read from job 1's
    record, every control the rule needs passes and the rule names LC-EARLY."""
    out = score(H3)
    assert [control(out, k) for k in ("PG", "E0", "T0", "J1")] == ["PASS"] * 4, out
    assert control(out, "B") == "FAILED"            # BIF_FAULT 0xf: read by LC-EARLY
    assert re.search(r"^OUTCOME lc1-a LC-EARLY: held$", out, re.M)
    assert re.search(r"^Q128-N3F-LC RULE: LC-EARLY$", out, re.M), out
    assert re.search(r"^PREDICTION LC-EARLY: predicted held, read held: held$", out, re.M)
    assert re.search(r"^PREDICTION LC-REBASE: .*: not reached \(LC-EARLY\)$", out, re.M)


@pytest.mark.parametrize("base", ["land", "b11a"])
def test_e0_passes_with_job_2_posted_and_unserved(tmp_path, base):
    d = attempt.build(str(tmp_path / base), "lc", (base, "j2stop"))
    page = json.loads(kept(d, "lc1-a.own_res.json"))["page"]
    assert page[1] == 6                              # job 2's cmd word, posted, not served
    out = score(d)
    assert control(out, "E0") == "PASS", out
    assert re.search(r"^Q128-N3F-LC RULE: LC-EARLY\b", out, re.M), out


@pytest.mark.parametrize("token", ["e0bad", "e0cmd"])
def test_e0_fails_on_job_1_s_record(tmp_path, token):
    d = attempt.build(str(tmp_path / token), "lc", ("land", "j2stop", token))
    out = score(d)
    assert control(out, "E0") == "FAILED", out
    assert re.search(r"^Q128-N3F-LC RULE: CANNOT TELL \(.*control E0 FAILED", out, re.M), out


def test_e0_with_no_job_1_record_cannot_tell(tmp_path):
    d = attempt.build(str(tmp_path / "norec"), "lc", ("land", "after2=rebase"))
    run = json.loads(kept(d, "lc1-a.txt"))
    del run["records"][0]["slot"], run["records"][0]["cmd_after"]
    with open(os.path.join(d, "lc1-a.txt.gz"), "wb") as f:
        f.write(gzip.compress(json.dumps(run).encode(), mtime=0))
    out = score(d)
    assert control(out, "E0") == "cannot tell", out


def test_the_mock_s_ownstop2_world_posts_job_2_and_e0_passes():
    """The kit mock, world ownstop2: job 1 done, job 2 posted and never served (the runner's stop,
    rc 4). Its kept stage has job 2's cmd word 6 on the page; scored, E0 passes and LC-EARLY
    holds (the rule cannot tell only through T0: the fake regs have no timer word)."""
    m = subprocess.run([sys.executable, "-B", "kit/session.py", "mock", ".", "--world",
                        "ownstop2"], cwd=KP, capture_output=True, text=True, env=ENV)
    assert m.returncode == 0, m.stdout + m.stderr
    top = re.search(r"files in (\S+)$", m.stdout, re.M).group(1)
    d = os.path.join(top, "ownstop2/out/ownstop2/lc")
    page = json.loads(kept(d, "lc1-a.own_res.json"))
    page = page["page"] if isinstance(page, dict) else page
    r1, r2 = json.loads(kept(d, "lc1-a.txt"))["records"]
    assert page[1] == 6 and r2["done"] is False and r2["cmd_after"] == 6, page[:8]
    assert r1["done"] is True and r1["cmd_after"] == 0 and r1["slot"][:2] == [M1, 1]
    out = score(d)
    assert control(out, "E0") == "PASS", out
    assert re.search(r"^OUTCOME lc1-a LC-EARLY: held$", out, re.M), out
    # the fake regs have no timer word (0x0acc): T0 alone cannot tell, E0 is not named
    rule = re.search(r"^Q128-N3F-LC RULE: .*$", out, re.M).group(0)
    assert rule == "Q128-N3F-LC RULE: CANNOT TELL (control T0 cannot tell)", out
