#!/usr/bin/env python3
"""test_static.py: `bash -n` of every script, and every command word the laptop-side runner (run/run_h.sh with run/lib_h.sh) can call
is a function defined in those two files, a bash builtin or keyword, or a command of the laptop allow-list (the one tests/run_mock.sh
gives the staged runner as its whole PATH).  Complements the mock's dynamic "command not found" search (which sees only the paths a
world takes): this one reads every line, the stop paths included.  Exit 0 if clean.
"""
import os
import re
import subprocess
import sys

KP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAPTOP = set("bash sh cat awk grep sed gzip mkfifo mktemp tee mkdir date uname seq sleep wc tr cut head tail kill ls env rm dirname "
             "basename sudo timeout df modinfo sha256sum shasum test".split())
BUILTIN = set("if then else elif fi for in do done case esac while until function return exit local set shift trap exec eval read "
              "printf echo test [ [[ ]] true false wait cd command export unset break continue . source declare : let".split())
fails = 0


def check(cond, msg):
    global fails
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        fails += 1


for f in ["run/lib_f.sh", "run/run_f.sh", "run/f.sh", "run/stage_f.sh", "run/freeze_f.sh", "run/guard_f.sh", "run/lib_check.sh",
          "tests/run_mock.sh", "tests/run_all.sh", "tests/fake_tool.sh"] + ["tests/shims/" + s for s in ("sudo", "ssh", "scp", "df", "timeout")]:
    r = subprocess.run(["bash", "-n", os.path.join(KP, f)], capture_output=True, text=True)
    check(r.returncode == 0, "bash -n %s %s" % (f, r.stderr.strip()[:120]))

def unknown_words(src):
    defined = set()
    for t in src.values():
        defined |= set(re.findall(r"^([a-z_][a-z0-9_]*)\(\)\s*\{", t, re.M))
    unknown = {}
    for f, t in src.items():
        # an awk program in single quotes over several lines (word_problem): its lines are an argument, never commands
        out, inside = [], False
        for l in t.splitlines():
            if l.lstrip().startswith("#"):
                out.append(l)
                continue
            odd = re.sub(r"(^|\s)#.*$", "", re.sub(r'"(\\.|[^"\\])*"', '""', l)).count("'") % 2 == 1
            if inside:
                out.append("" if not odd else "'" + l.split("'", 1)[1])
                inside = not odd
            else:
                out.append(l + ("'" if odd else ""))
                inside = odd
        t = "\n".join(out)
        for n, line in enumerate(t.splitlines(), 1):
            s = line
            if line.lstrip().startswith("#"):
                continue
            # strip quoted strings (their words are arguments, never commands)
            s = re.sub(r"'[^']*'", "''", s)
            s = re.sub(r'"(\\.|[^"\\])*"', '""', s)
            s = re.sub(r"\$\(\(.*?\)\)", "0", s)                                # arithmetic
            s = re.sub(r"\$\{[^}]*\}", "X", s)                                    # parameter expansions
            s = re.sub(r"^\s*[\w.*$|:-]+\)\s", " ", s)                             # a case label
            s = re.sub(r"(^|\s)#.*$", "", s)                                        # a comment
            for seg in re.split(r"\$\(|;;|;|&&|\|\||\||\{|\(|\bthen\b|\bdo\b|\belse\b|`", s):
                seg = seg.strip()
                seg = re.sub(r"^([A-Za-z_][A-Za-z0-9_]*=\S*\s+)+", "", seg)       # VAR=value prefixes
                m = re.match(r"([a-z_][a-z0-9_.-]*)\b", seg)
                if not m:
                    continue
                w = m.group(1)
                if w in BUILTIN or w in defined or w in LAPTOP:
                    continue
                if re.match(r"^[a-z_][a-z0-9_]*=", seg) or seg.startswith(w + ")") or seg.startswith(w + "|"):
                    continue                                                       # an assignment or a case label
                unknown.setdefault(w, []).append("%s:%d" % (f, n))
    return unknown


src = {f: open(os.path.join(KP, f)).read() for f in ("run/lib_f.sh", "run/run_f.sh")}
unknown = unknown_words(src)
defined = set(re.findall(r"^([a-z_][a-z0-9_]*)\(\)\s*\{", "".join(src.values()), re.M))
# words that are case labels or arguments in context, checked by hand: listed here with the reason
KNOWN_ARGS = {"gate", "plain", "held", "fault", "hang", "ok", "fail", "fill", "health", "flush", "expectdiff", "rgn", "cell", "hypo", "probe", "clr", "long", "ctl640", "set", "clear", "exit", "begin", "end",
              "reg", "rc", "class", "mode", "step", "tri", "busy", "no", "yes"}
real = {w: v for w, v in unknown.items() if w not in KNOWN_ARGS}
check(not real, "every command word of the laptop runner is defined, a builtin or on the laptop PATH%s" %
      ("" if not real else ": unknown " + "; ".join("%s at %s" % (w, ",".join(v[:3])) for w, v in sorted(real.items()))))
check(len(defined) >= 30, "%d functions defined in lib_f.sh and run_f.sh" % len(defined))
inj = dict(src)
inj["run/run_f.sh"] = inj["run/run_f.sh"].replace("\tsnap \"$name\" 2\n", "\tpeek_now \"$name\" 2\n", 1)
check("peek_now" in unknown_words(inj), "self-test: a call of an undefined function (peek_now) is caught")
print("static checks: %s" % ("PASS" if not fails else "%d FAILED" % fails))
sys.exit(1 if fails else 0)
