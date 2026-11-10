#!/usr/bin/env python3
"""Rewrap a markdown file to 98 columns: paragraphs and list items are reflowed, wide tables become lists, code blocks and
headings are kept.  usage: mdwrap.py FILE..."""
import re, sys, textwrap

W = 98

def cells(l):
    out, cur, tick = [], "", False
    for ch in l.strip().strip("|"):
        if ch == "`":
            tick = not tick
        if ch == "|" and not tick:
            out.append(cur.strip()); cur = ""
        else:
            cur += ch
    out.append(cur.strip())
    return out

def table_to_list(block):
    hdr = cells(block[0]); out = []
    for l in block[2:]:
        c = cells(l)
        head = c[0]
        if len(hdr) <= 3:
            rest = "; ".join(v for v in c[1:] if v and v != "-")
            out.append(f"- **{head}**: {rest}")
        else:
            rest = "; ".join(f"{h}: {v}" for h, v in zip(hdr[1:], c[1:]) if v and v != "-")
            out.append(f"- **{head}**: {rest}")
    return out

def wrap_item(text, indent):
    sub = " " * len(indent)
    return textwrap.fill(text, width=W, initial_indent=indent, subsequent_indent=sub,
                         break_long_words=False, break_on_hyphens=False).splitlines()

def process(lines):
    out, i = [], 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out += lines[i:j + 1]; i = j + 1; continue
        if l.startswith("|"):
            j = i
            while j < len(lines) and lines[j].startswith("|"):
                j += 1
            blk = lines[i:j]
            out += blk if max(len(x) for x in blk) <= 100 else process(table_to_list(blk))
            i = j; continue
        if not l.strip() or l.startswith("#"):
            out.append(l); i += 1; continue
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", l)
        ind = (m.group(1) + m.group(2) + " ") if m else ""
        j = i + 1
        body = [m.group(3) if m else l.strip()]
        while j < len(lines) and lines[j].strip() and not lines[j].startswith(("#", "```", "|")) \
                and not re.match(r"^\s*([-*]|\d+\.)\s+", lines[j]):
            body.append(lines[j].strip()); j += 1
        out += wrap_item(" ".join(body), ind) if len(" ".join(body)) + len(ind) > W or True else [l]
        i = j
    return out

for f in sys.argv[1:]:
    lines = open(f).read().splitlines()
    open(f, "w").write("\n".join(process(lines)) + "\n")
