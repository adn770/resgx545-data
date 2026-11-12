#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""guard_py.py FILE...: the forbidden list of the session guard, applied to the code lines of
Python files only (comments and docstrings are left out, string literals are checked, since a
command inside a string still runs).  Exit 1 with the lines."""
import io
import re
import sys
import tokenize

BAD = re.compile(r"reboot|shutdown|poweroff|kexec|grub|mkinitcpio|make (-j|bzImage|modules)|build-kernel|"
                 r"install-test-kernel|boot-test-kernel|push-gma500|trc_hazard|CLKGATE|clkgate|kreg_write|"
                 r"[\"']kreg[\"']|kpoke|/dev/mem|git (stash|clean|reset)|(^|[^a-z_])rm [-a-z]|unlink|os\.remove|"
                 r"rmtree|rmdir|xfer_sync")


def code_lines(path):
    src = open(path).read()
    keep = {}
    prev = tokenize.INDENT
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.COMMENT:
            continue
        # a string that is a whole statement (a docstring) follows a NEWLINE, INDENT or DEDENT
        if tok.type == tokenize.STRING and prev in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.NL):
            prev = tok.type
            continue
        if tok.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
            for n in range(tok.start[0], tok.end[0] + 1):
                keep.setdefault(n, []).append(tok.string)
        prev = tok.type
    return {n: "".join(v) for n, v in keep.items()}      # joined without spaces: `os . remove` reads os.remove


def main(files):
    st = 0
    for f in files:
        for n, line in sorted(code_lines(f).items()):
            if BAD.search(line):
                print(f"{f}:{n}: {line[:120]}")
                st = 1
    return st


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
