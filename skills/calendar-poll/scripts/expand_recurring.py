#!/usr/bin/env python3
"""Expand recurring Calendar.app events into a window (AppleScript's `whose start date` misses them).
Input: lines 'calendar|startISO|endISO|RRULE|title' (from the AppleScript in SKILL.md).
usage: expand_recurring.py <dump.txt> <YYYY-MM-DD from> <YYYY-MM-DD to-exclusive>"""
import sys, datetime as dt
from dateutil.rrule import rrulestr
f, a, b = sys.argv[1], dt.datetime.fromisoformat(sys.argv[2]), dt.datetime.fromisoformat(sys.argv[3])
seen, hits = set(), []
for line in open(f):
    p = line.rstrip("\n").split("|")
    if len(p) < 5: continue
    cal, s, e, r, name = p[0], p[1], p[2], p[3], "|".join(p[4:])
    if (s, r, name) in seen: continue
    seen.add((s, r, name))
    try:
        st, en = dt.datetime.fromisoformat(s), dt.datetime.fromisoformat(e)
        for o in rrulestr(r.replace("Z", ""), dtstart=st, ignoretz=True).between(a, b, inc=True):
            hits.append((o, o + (en - st), cal, name))
    except Exception:
        pass
for o, e, c, n in sorted(hits):
    print(o.strftime("%a %Y-%m-%d %H:%M"), "-", e.strftime("%H:%M"), "|", c, "|", n)
