#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""pinned.py: the published dump readers stage v's scorer uses, imported from their blobs at the
commits session.toml's [freeze] names (never a working tree: main and data may move after the
freeze), each checked against the sha256 FROZEN.commits gives it.

  resgx545  tools/usse-asm/pbdump.py, tools/usse-asm/dpm_words.py
  data      cited/closing6/dpm/offline/f3_streams.py, f1_brackets.py, r6lib.py

load() installs a finder ahead of the path finders that serves these module names from the blobs
(a module's __file__ is its path in the repository, so the files' own sys.path lines resolve);
any other import is the standard library's."""
from __future__ import annotations

import hashlib
import importlib.abc
import importlib.util
import os
import pathlib
import subprocess
import sys
import tomllib

KP = pathlib.Path(__file__).resolve().parent.parent
REPOS = {"resgx545": os.environ.get("RESGX545_TREE", str(pathlib.Path.home() / "src/resgx545")),
         "data": os.environ.get("RESGX545_DATA", str(pathlib.Path.home() / "src/resgx545-data"))}
MODULES = {"pbdump": ("resgx545", "tools/usse-asm/pbdump.py"),
           "dpm_words": ("resgx545", "tools/usse-asm/dpm_words.py"),
           "f3_streams": ("data", "cited/closing6/dpm/offline/f3_streams.py"),
           "f1_brackets": ("data", "cited/closing6/dpm/offline/f1_brackets.py"),
           "r6lib": ("data", "cited/closing6/dpm/offline/r6lib.py")}


def _frozen():
    out = {}
    f = KP / "FROZEN.commits"
    for ln in (f.read_text().splitlines() if f.exists() else []):
        p = ln.split()
        if len(p) == 3 and ":" in p[2]:
            out[p[2]] = p[0]
    return out


def blob(repo, path):
    c = tomllib.loads((KP / "session.toml").read_text())["freeze"][repo]
    r = subprocess.run(["git", "-C", REPOS[repo], "show", f"{c}:{path}"], capture_output=True,
                       timeout=60)
    if r.returncode:
        raise ImportError(f"{repo}:{path} at {c[:12]}: {r.stderr.decode().strip()}")
    want = _frozen().get(f"{repo}:{path}")
    if want and hashlib.sha256(r.stdout).hexdigest() != want:
        raise ImportError(f"{repo}:{path} is not the frozen blob")
    return r.stdout


class _Finder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, name, path=None, target=None):
        if name not in MODULES:
            return None
        repo, rel = MODULES[name]
        return importlib.util.spec_from_loader(name, self, origin=os.path.join(REPOS[repo], rel))

    def create_module(self, spec):
        return None

    def exec_module(self, mod):
        repo, rel = MODULES[mod.__name__]
        mod.__file__ = os.path.join(REPOS[repo], rel)
        exec(compile(blob(repo, rel), mod.__file__, "exec"), mod.__dict__)


def load():
    if not any(isinstance(f, _Finder) for f in sys.meta_path):
        sys.meta_path.insert(0, _Finder())
    os.environ.setdefault("RESGX545_DATA", REPOS["data"])
    os.environ.setdefault("RESGX545_TREE", REPOS["resgx545"])
    import f3_streams
    import pbdump
    return f3_streams, pbdump
