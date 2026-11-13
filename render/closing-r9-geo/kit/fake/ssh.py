#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
"""ssh.py [-o OPT]... HOST COMMAND: the fake ssh of the kit's mock. "The laptop" is the directory
$KIT_FAKE_HOME: the command runs in bash there under an empty environment (env -i) holding only
HOME, the laptop PATH ($KIT_LAPTOP_PATH: the fake commands and /usr/bin:/bin) and the mock's own
variables (KIT_*, FAKE_*, RESET_WAIT, HEALTH_WAIT, TEE_GRACE), so the staged tree cannot lean on
anything of the Mac's environment. stdin passes through (the staging tar)."""
import os
import sys

KEEP = ("KIT_", "FAKE_")
NAMES = ("RESET_WAIT", "HEALTH_WAIT", "TEE_GRACE")


def main(argv):
    a = argv[1:]
    while a and a[0].startswith("-"):
        a = a[2:] if a[0] == "-o" else a[1:]
    if len(a) < 2:
        sys.stderr.write("fake ssh: no command\n")
        return 255
    cmd = " ".join(a[1:])
    home = os.environ["KIT_FAKE_HOME"]
    env = {"HOME": home, "PATH": os.environ["KIT_LAPTOP_PATH"]}
    env.update({k: v for k, v in os.environ.items() if k.startswith(KEEP) or k in NAMES})
    os.chdir(home)
    os.execve("/bin/bash", ["bash", "-c", cmd], env)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
