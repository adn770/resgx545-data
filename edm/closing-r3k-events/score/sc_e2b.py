# SPDX-License-Identifier: MIT
"""sc_e2b.py: the scorer of stage e2b (Q098's write direction): rows R (read), S (control: E748's `mov sa67`), C4 / C5 / C6 (`mov pa3`, `mov
pa4`, `mov pa2`), Z67 / Z68 (the restores).  Area A = the registers at the writer pass's entry, area C = the same-pass read-backs (the pa
and its sa alias), area B = the next pass (command 9).  Each read-back is classed `M` (the marker the row wrote), `old` (the value at entry)
or the hex of something else, and compared with the frozen H-D (alias: both M), H-B (lost: both old) and H-P (private: the pa M, the sa
old) rows.  Standard library only."""
import scorelib as C
import r3layout as L

F = {n: i for i, n in enumerate(L.PW_FIELDS)}
OF = {"c4": ("pa3", "sa67"), "c5": ("pa4", "sa68"), "c6": ("pa2", "sa66"), "s": ("pa3", "sa67"), "z67": ("pa3", "sa67"), "z68": ("pa4", "sa68")}


def cls(v, marker, old):
    if v is None:
        return None
    if marker is not None and v == marker:
        return "M"
    if v == old:
        return "old"
    return f"{v:#x}"


def yn(b):
    return "yes" if b else "no"


def score_e2b(S):
    verdict = {"H-D alias": [], "H-B lost": [], "H-P private": []}
    ctl = []
    for j in S.table["jobs"]:
        n, row = j["name"], j["row"]
        rec = C.record(S.d, n)
        if rec is not None and rec.get("class") == "skipped":
            S.p(f"{n}: not run ({rec.get('note', '').strip()})")
            continue
        if rec is None or rec.get("class") != "ok" and rec.get("class") != "stop":
            S.nodata(n, f"class {None if rec is None else rec.get('class')}")
            continue
        if rec["class"] == "stop":
            sg = C.rec_sig(rec)
            S.stop_names.append(n)
            for pr in S.preds:
                if pr["case"] == n:
                    S.t.add(n, pr["quantity"], pr["model"], pr["set"], None, "the tick stopped")
            S.p(f"{n}: a TICK STOP after the writer's pass; {C.sig_line(sg)}; {C.mark_text(C.marks_of(S, rec))}; {C.p3_text(rec)}")
            continue
        a, c, b = rec.get("area_a") or [], rec.get("area_c") or [], rec.get("area_b") or []
        if len(a) < 12 or len(b) < 12 or len(c) < 8:
            S.nodata(n, "an area was not read")
            continue
        A = {f: a[i] for f, i in F.items()}
        B = {f: b[i] for f, i in F.items()}
        marker = j["marker"]
        if row == "R":
            words = all(A[k] == L.E748[k] for k in ("pa0", "pa1", "pa2", "pa3", "pa4", "sa64", "sa65", "sa66", "sa67", "sa68", "sa0"))
            same = all(B[k] == A[k] for k in ("pa3", "pa4", "sa67", "sa68", "sa64", "sa65"))
            C.Stage.tally_value(S, n, "e748_words", yn(words))
            C.Stage.tally_value(S, n, "next_same", yn(same))
            ctl.append(words and same)
            S.p(f"{n}: class ok; entry words as E748 {words} ({ {k: hex(A[k]) for k in ('pa2', 'pa3', 'pa4', 'sa0')} }); next pass the same {same}")
            continue
        key = {"S": "s", "Z67": "z67", "Z68": "z68", "C4": "c4", "C5": "c5", "C6": "c6"}[row]
        pa, sa = OF[key]
        co = L.PW_C_OF[j["cmd"]][0] - L.PW_C
        pa_same = cls(c[co], marker, A[pa]) if j["cmd"] in (4, 5, 6) else cls(c[co], marker, A[pa])
        sa_same = cls(c[co + 1], marker, A[sa])
        if j["cmd"] in (2, 3):          # E748's writers: the sa is written, the pa read back (cmd 2: r17 = pa, r18 = sa)
            pass
        pa_next, sa_next = cls(B[pa], marker, A[pa]), cls(B[sa], marker, A[sa])
        neigh = [x for x in ("pa3", "pa4", "sa67", "sa68") if x not in (pa, sa)]
        neighbours = all(B[x] == A[x] for x in neigh)
        q = {f"{pa}_same": pa_same, f"{sa}_same": sa_same, f"{pa}_next": pa_next, f"{sa}_next": sa_next, "neighbours_unchanged": yn(neighbours)}
        for quantity, got in q.items():
            if any(pr["case"] == n and pr["quantity"] == quantity for pr in S.preds):
                C.Stage.tally_value(S, n, quantity, got)
        if row in ("C4", "C5", "C6"):
            for m in verdict:
                ok = []
                for pr in S.preds:
                    if pr["case"] == n and pr["model"] == m and pr["quantity"] in q:
                        ok.append(q[pr["quantity"]] == pr["value"])
                if ok:
                    verdict[m].append(all(ok))
        else:
            ctl.append(pa_same == "M" and sa_next == "M")
        S.p(f"{n}: class ok; marker {marker:#x}; {pa} same pass {pa_same} ({c[co]:#x}), {sa} same pass {sa_same} ({c[co + 1]:#x}); next pass {pa} {pa_next}, "
            f"{sa} {sa_next}; neighbours {neigh} unchanged {neighbours}")
    note = S.stage_note()
    alive = [m for m, v in verdict.items() if v and all(v)]
    dead = [m for m, v in verdict.items() if v and not all(v)]
    ctls = "R/S/Z controls held" if ctl and all(ctl) else "a CONTROL DIFFERS" if ctl else "no control read"
    return (f"e2b: {ctls}; write direction: consistent with {alive or 'none'}, refuted {dead or 'none'}; stops {len(S.stop_names)} {S.stop_names}; Q098 rows: "
            f"{S.t.line()}" + (f"; {note}" if note else ""))
