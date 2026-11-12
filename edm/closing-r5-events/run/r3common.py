# SPDX-License-Identifier: MIT
"""r3common.py: what the runner and its op modules share (one class, so that `except Stop` in r3_run.py, which runs as __main__, catches the
Stop an op module raises).  Laptop file, frozen with the runner."""


class Stop(Exception):
    """A reason to end the stage: code is the runner's exit code (1 preflight, 3 watchdog, 4 job, 5 reset or gate, 6 no return, 7 table, 8 budget)."""

    def __init__(self, code, why):
        super().__init__(why)
        self.code = code
