#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""guard_names.py PATTERN [--allow REGEX] FILE...: the code lines (comments and docstrings left out, as guard_py.py reads them) of Python
files that match PATTERN and not the allow REGEX.  Exit 1 with the lines."""
import re
import sys

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import guard_py  # noqa: E402


def main(argv):
    pat = re.compile(argv[1])
    allow = None
    files = argv[2:]
    if files and files[0] == "--allow":
        allow, files = re.compile(files[1]), files[2:]
    st = 0
    for f in files:
        for n, line in sorted(guard_py.code_lines(f).items()):
            if pat.search(line) and not (allow and allow.search(line)):
                print(f"{f}:{n}: {line[:120]}")
                st = 1
    return st


if __name__ == "__main__":
    sys.exit(main(sys.argv))
