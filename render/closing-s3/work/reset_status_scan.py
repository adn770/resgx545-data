"""Offline scan (S3 prep, not a run): for every kernel log kept in resgx545-data and in S1's out/,
pair each BIF fault the kernel reported with the next "SGX reset: BIF_FAULT x EVENT_STATUS a/b"
line (sgxfive_clear_faults prints it after sgxfive_halt, before it clears anything).

Usage: python reset_status_scan.py LISTFILE   (LISTFILE: one path a line, .gz or text)
Prints one row a fault: file, fault word, fault address, reset's EVENT_STATUS/2, the gap in lines.
Also the idle resets (no fault before them) are counted by their status pair.
"""
import collections
import gzip
import re
import sys

FAULT = re.compile(r"BIF fault (0x[0-9a-f]+) at (0x[0-9a-f]+)")
HELD = re.compile(r"recovery held \(debugfs hold_recovery\)")
RESET = re.compile(r"SGX reset: BIF_FAULT (0x[0-9a-f]+|0) EVENT_STATUS (0x[0-9a-f]+|0)/(0x[0-9a-f]+|0)")
NAME = re.compile(r"(journal|kernel|dmesg|klog|run|\.log)", re.I)


def lines_of(path):
    opener = gzip.open if path.endswith(".gz") else open
    try:
        with opener(path, "rt", errors="replace") as f:
            for line in f:
                yield line
    except (OSError, EOFError):
        return


def main():
    rows = []
    idle = collections.Counter()
    seen_text = set()
    for path in open(sys.argv[1]).read().split("\n"):
        if not path or not NAME.search(path.rsplit("/", 1)[-1]):
            continue
        pending = None
        for n, line in enumerate(lines_of(path)):
            m = FAULT.search(line)
            if m:
                pending = (m.group(1), m.group(2), n)
                continue
            r = RESET.search(line)
            if r:
                st = (r.group(2), r.group(3))
                if pending:
                    key = (path, pending[2])
                    if key not in seen_text:
                        seen_text.add(key)
                        rows.append((path, pending[0], pending[1], r.group(1), st, n - pending[2]))
                    pending = None
                else:
                    idle[st] += 1
    by_word = collections.defaultdict(collections.Counter)
    for path, word, addr, bf, st, gap in rows:
        by_word[word][st] += 1
        print("%s\t%s\t%s\tBIF_FAULT-after-halt %s\tstatus %s/%s\tgap %d" % (
            path.replace("/Users/jtorra/src/", ""), word, addr, bf, st[0], st[1], gap))
    print("\n## by fault word: the reset's EVENT_STATUS/EVENT_STATUS2 (read after the halt)")
    for word in sorted(by_word):
        print(word, dict(by_word[word]))
    print("\n## resets with no fault before them:", dict(idle))


if __name__ == "__main__":
    main()
