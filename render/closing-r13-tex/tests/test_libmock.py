# SPDX-License-Identifier: MIT
"""tests/test_libmock.py: the library-mock replay of the t10p rows (srgb3, addr4, t3c), which the
kit's replay skips (session.toml: t10p is t10's binary with a no_source reason). libsgxfive's
in-process mock at t10's source (a581c06) runs a copy (probe --coords) only with its own copy
shader; any program of ours is "an unknown program" there (mock.c) and the job faults. So each
row is replayed on that mock, built by the kit from t10's pinned source (kit/session.py
libmock_build), and must end exactly so: the argv accepted (the probe prints its scratch line),
no usage line, no `job: rejected`, rc 3 with `failed: job faulted` and no other failure. Control
that can fail: the same replay of a row with --scratch-pages 99 is the tool's usage refusal."""
import os
import pathlib
import subprocess
import sys

KP = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KP / "kit"))
sys.dont_write_bytecode = True
import session as S  # noqa: E402


def libmock():
    b, why = S.libmock_build(KP, S.config(KP), "t10")
    assert b is not None, why
    return b


def rows():
    out = []
    for st in ("srgb3", "addr4", "t3c"):
        for ln in (KP / "tables" / f"{st}.txt").read_text().splitlines():
            if ln.strip() and not ln.startswith("#"):
                out.append(ln.split("|", 5))
    return out


def replay(b, args, tmp):
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(tmp), "W": str(tmp),
           "S": str(KP), "SGXFIVE_KPOKE": str(tmp / "kpoke")}
    (tmp / "kpoke").write_text("")
    argv = S._expand(args, env)
    assert argv is not None
    return subprocess.run([str(b), "--mock", *argv], capture_output=True, text=True, env=env,
                          cwd=tmp, timeout=120)


def test_every_t10p_row_reaches_its_job(tmp_path):
    b = libmock()
    rs = rows()
    assert len(rs) == 37 and all(r[4] == "t10p" for r in rs)
    for name, st, risk, knobs, tool, args in rs:
        r = replay(b, args, tmp_path)
        out = r.stdout + r.stderr
        assert "usage" not in out and "job: rejected" not in out, (name, out[-300:])
        assert f"probe {name}: scratch at " in r.stdout, (name, out[-300:])
        fails = [ln for ln in out.splitlines() if "failed:" in ln]
        assert r.returncode == 3 and fails == [
            f"probe {name}: failed: job faulted, context lost (Input/output error)"], (name, out)


def test_the_replay_can_fail(tmp_path):
    b = libmock()
    name, st, risk, knobs, tool, args = rows()[0]
    r = replay(b, args.replace("--temps 32", "--temps 32 --scratch-pages 99"), tmp_path)
    assert r.returncode == 2 and "usage" in r.stderr
