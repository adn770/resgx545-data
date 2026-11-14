# SPDX-License-Identifier: MIT
"""tests/test_twin.py: the table against the plan (closing19/plan/rank-round19.md section 5, S4;
closing19/DECISIONS-R19.md R19-3 a) and the session build rules: one stage, fl, flagged (on_stop
end, no gate, no soft row); its first job is the safe control, which reads keys its row produces,
does not expectfault and has frozen predictions; #limit counts exactly the expectfault rows that
are not controls (E946) and is 2; the last row is one of them; both planned rows are ld's form
(the control's argv) plus E631's ramp fill of page 6 before render 2 and nothing else; no fl-thr1
row (R19-3 a: fl-junk only); the knobs the rows write are declared, render_final_pb_pages only
at 0; every tool is t18b; no forbidden option."""
import os
import sys
import tomllib

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KP, "kit"))
sys.path.insert(0, os.path.join(KP, "score"))
sys.dont_write_bytecode = True
import kitscore as K  # noqa: E402
import score  # noqa: E402
import scorekit as SK  # noqa: E402

CFG = tomllib.loads(open(os.path.join(KP, "session.toml")).read())
T = K.table(KP, "fl")
FILL = "--tadata-fill-render 2:6:0xa5000000:ramp"


def test_stage_is_flagged_and_ends_the_session():
    assert list(CFG["stages"]) == ["fl"]
    assert CFG["stages"]["fl"]["on_stop"] == "end"
    assert not CFG["stages"]["fl"].get("gate")
    assert CFG["srcversion"] == "E0CC40275493F8AEAD8180B" and CFG["prefix"] == "r19f"


def test_rows_and_limit():
    assert [r["name"] for r in T] == ["fl-ctl", "fl-junk-a", "fl-junk-b"]
    assert [r["set"] for r in T] == ["control", "fit", "heldout"]
    lim = [int(ln.split()[1]) for ln in open(os.path.join(KP, "tables", "fl.txt")) if ln.startswith("#limit")]
    planned = [r["name"] for r in T if "expectfault" in r["knobs"] and r["set"] != "control"]
    assert lim == [len(planned)] == [2]
    assert planned[-1] == T[-1]["name"]
    assert all("soft" not in r["knobs"] and "noreset" not in r["knobs"] for r in T)
    assert all("after" in r["knobs"] for r in T)            # strict health after every job
    assert "thr1" not in open(os.path.join(KP, "tables", "fl.txt")).read()


def test_control_can_fail_and_is_the_junk_rows_twin():
    c = T[0]
    assert c["risk"] == "safe" and "expectfault" not in c["knobs"] and c["tool"] == "t18b"
    assert set(c["reads"]) == {"job", "ovf", "thr", "lists"}
    SK.refuse_unreadable(K.controls(KP, "fl"), score.producible)
    assert K.predictions(KP, "fl")["fl-ctl"].keys() == {"job", "ovf", "thr", "lists"}
    for r in T[1:]:
        assert r["risk"] == "risky" and r["tool"] == "t18b"
        assert r["args"] == c["args"] + " " + FILL
        assert [w for w in r["knobs"] if w.startswith("dbg:")] == [w for w in c["knobs"] if w.startswith("dbg:")]


def test_the_form_is_lds():
    a = T[0]["args"].split()
    for pair in (("--width", "1024"), ("--height", "768"), ("-n", "2"), ("--geometry", "1"),
                 ("--final-pb-pages", "0x100")):
        assert a[a.index(pair[0]) + 1] == pair[1]
    assert "--keep-overflow" in a and "--dump-each" in a and "--wait-ms" in a
    # N = 0x100: 0x0624 = N - 0x22 = 0xde; P = 0x28 (E625: one partial render)
    assert 0x100 - 0x22 == 0xde and K.predictions(KP, "fl")["fl-ctl"]["thr"]["H-REF"] == "0xde"
    assert "dbg:render_pb_pages=0x28" in T[0]["knobs"]


def test_knobs_declared_and_nothing_forbidden():
    assert CFG["knobs"]["render_final_pb_pages"] == {"default": "0", "values": ["0"]}
    assert CFG["knobs"]["render_pb_pages"]["default"] == "0x422"
    assert "0x28" in CFG["knobs"]["render_pb_pages"]["values"]
    for r in T:
        a = r["args"].split()
        assert not set(a) & {"--kreg-render", "--kpoke-render", "--kpoke-job", "--refill", "--ctx2",
                             "--fault", "--scratch-at", "--low", "--late"}
        assert "idle:" not in " ".join(r["knobs"])


def test_predictions_cover_the_four_models_on_both_rows():
    p = K.predictions(KP, "fl")
    for n in ("fl-junk-a", "fl-junk-b"):
        ends = {m: v for m, v in p[n]["end"].items()}
        assert ends == {"H-NOLOAD": "ok", "H-LOAD-FAULT": "fault", "H-LOAD-HANG": "hang",
                        "H-LOAD-CORRUPT": "ok"}
        assert p[n]["same"] == {"H-NOLOAD": "1", "H-LOAD-CORRUPT": "0"}
