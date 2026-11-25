#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Josep Torra
# the fake tool of the kit's mock, installed at each tool's laptop path: the session's
# mock/world.py answers from the argv and the tool's own path, never from a case name
exec "${KIT_PY:?}" "${KIT_FAKE:?}/tool.py" "$0" "$@"
