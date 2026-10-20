#!/usr/bin/env python3
"""when2meet helper. Run with Python 3.9 or newer (standard library only).

  inspect <url>                      grid days/hours in the person's time zone + participants
  slots <blocks.json>                blocks {"YYYY-MM-DD":[["07:00","09:30"],...]} -> unix slot lists
  fill <url> <blocks.json>           mark those blocks in the signed-in Chrome tab (SAVES LIVE)
  verify <url> <blocks.json> <name>  reload from server, compare saved slots with the plan
  probe <url>                        signed-in user id/name and how many slots are marked

All times are in the person's time zone: the POLL_TZ environment variable, else "tz" in
~/.config/office-skills/calendar-poll.json, else this computer's local zone.
"""
import sys, re, json, time, subprocess, urllib.request, datetime as dt, os
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
def _tz():
    name = os.environ.get("POLL_TZ")
    if not name:
        try:
            cfg = os.path.expanduser("~/.config/office-skills/calendar-poll.json")
            name = json.load(open(cfg)).get("tz")
        except Exception:
            name = None
    if name:
        return ZoneInfo(name)
    return dt.datetime.now().astimezone().tzinfo   # this computer's local zone

TZ = _tz()

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode(errors="ignore")

def grid(html):
    idx = {int(i): int(t) for i, t in re.findall(r"TimeOfSlot\[(\d+)\]=(\d+);", html)}
    names = re.findall(r"PeopleNames\[(\d+)\] = '([^']*)';", html)
    ids = re.findall(r"PeopleIDs\[(\d+)\] = (\d+);", html)
    avail = re.findall(r"AvailableAtSlot\[(\d+)\]\.push\((\d+)\);", html)
    return idx, dict(names), dict(ids), avail

def slots(blocks):
    out = []
    for day, bl in blocks.items():
        for a, b in bl:
            s = dt.datetime.fromisoformat(f"{day}T{a}").replace(tzinfo=TZ)
            e = dt.datetime.fromisoformat(f"{day}T{b}").replace(tzinfo=TZ)
            ts = []
            while s < e:
                ts.append(int(s.timestamp())); s += dt.timedelta(minutes=15)
            out.append(ts)
    return out

def frag(url):
    m = re.search(r"\?(\d+-\w+)", url); return m.group(1) if m else url

def chrome(url, js):
    r = subprocess.run(["osascript", f"{HERE}/chrome_js.applescript", frag(url), js],
                       capture_output=True, text=True)
    if r.returncode: sys.exit(r.stderr.strip())
    out = r.stdout.strip()
    if out == "NO TAB": sys.exit("No Chrome tab with this poll is open. Open it (and have the person sign in) first.")
    return out

def main_world(url, body, attr):
    """Run `body` in the PAGE's JS world; it must write its result to document.body[data-attr]."""
    inj = ("var s=document.createElement('script');s.textContent=" + json.dumps(body) +
           f";document.body.removeAttribute('data-{attr}');document.head.appendChild(s);'ok'")
    chrome(url, inj)
    for _ in range(60):
        v = chrome(url, f"document.body.getAttribute('data-{attr}')")
        if v and v not in ("missing value", "null"): return json.loads(v)
        time.sleep(1)
    sys.exit("timed out waiting for page script")

cmd = sys.argv[1]
if cmd == "inspect":
    idx, names, ids, avail = grid(fetch(sys.argv[2]))
    # contiguous runs in local time (a grid built in another zone can wrap past midnight)
    runs, prev = [], None
    for t in sorted(idx.values()):
        if prev is None or t - prev != 900: runs.append([t, t])
        else: runs[-1][1] = t
        prev = t
    for a, b in runs:
        A, B = dt.datetime.fromtimestamp(a, TZ), dt.datetime.fromtimestamp(b + 900, TZ)
        print(A.strftime("%a %Y-%m-%d %H:%M"), "->", B.strftime("%a %H:%M"), f"({(b - a) // 900 + 1} slots)")
    print("participants:", sorted(set(names.values())))
elif cmd == "slots":
    print(json.dumps(slots(json.load(open(sys.argv[2])))))
elif cmd == "probe":
    print(main_world(sys.argv[2], "document.body.setAttribute('data-probe',JSON.stringify({user:(typeof UserID!=='undefined')?UserID:null,"
        "marked:(typeof UserID!=='undefined')?AvailableAtSlot.filter(function(a){return a.indexOf(UserID)>=0}).length:null,people:PeopleNames}))", "probe"))
elif cmd == "fill":
    B = json.dumps(slots(json.load(open(sys.argv[3]))))
    body = open(f"{HERE}/fill.js").read().replace("__BLOCKS__", B)
    print(json.dumps(main_world(sys.argv[2], body, "fill")))
elif cmd == "verify":
    url, plan, name = sys.argv[2], sys.argv[3], sys.argv[4]
    idx, names, ids, avail = grid(fetch(url))
    pids = {ids[i] for i, n in names.items() if n == name and i in ids}
    saved = {idx[int(i)] for i, p in avail if p in pids}
    want = {t for b in slots(json.load(open(plan))) for t in b}
    f = lambda S: sorted(dt.datetime.fromtimestamp(t, TZ).strftime("%a %d %H:%M") for t in S)
    print(f"person ids {sorted(pids)}; saved {len(saved)}, planned {len(want)}, match {saved == want}")
    print("extra:", f(saved - want)); print("missing:", f(want - saved))
