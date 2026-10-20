#!/usr/bin/env python3
"""email-archive: open and search a mail archive of exported mailboxes (Thunderbird-layout mbox).

    email-archive [open] [--dry-run]   open the archive in its own Thunderbird profile
    email-archive where                print the archive folder that profile points at
    email-archive point DIR            point the profile at DIR (only while that Thunderbird is quit)
    email-archive index [DIR]          build or refresh the search index for the archive
    email-archive search TERMS...      search it: id, date, mailbox, sender, subject per hit
    email-archive show ID              print one message (headers and text) from the archive
    email-archive eml ID OUT.eml       write one message out as a .eml file

SETUP (once). Make a separate Thunderbird profile for the archive (thunderbird -P, "Create
Profile"), keep it apart from any profile you read live mail in, and name its folder in a config
file, ~/.config/office-skills/email-archive.json:

    {"profile": "~/Library/Thunderbird/Profiles/<archive-profile>",
     "volume_hint": "Is the external disk connected?"}

or in the environment variable OFFICE_EMAIL_ARCHIVE_PROFILE (MAIL_ARCHIVE_PROFILE is still read).
Optional keys: "server_pref" (default mail.server.server1.directory, the profile's Local Folders),
"volume_hint" (added to every "not there" message). OFFICE_EMAIL_ARCHIVE_CONFIG names another
config file. Then run  email-archive point <archive folder>  once, with that Thunderbird closed.

RULES THIS FILE KEEPS
  * The archive profile ONLY, as a separate instance (-n, -no-remote). Never a profile you read
    live or private mail in: the two kinds of mail stay apart.
  * The archive is READ, never written. The index is a SIBLING file, <archive>.index.sqlite, not a
    file inside the archive folder, where Thunderbird might take it for a mail folder.
  * "The archive" is whatever the profile's user.js points at (the server_pref line), so open,
    index and search agree without a second setting that could drift. Pass DIR to override.
  * The index is rebuildable from the mbox files at any time and refreshes only mailboxes whose file
    changed (size, mtime). The archive is static, so rebuild after each export.
  * No Full Disk Access needed for an archive on an ordinary volume. Only exporting out of
    ~/Library/Mail needs it, and that is not this tool.
Stdlib only; the index needs SQLite 3.43 or newer (FTS5 with contentless_delete).
Exit codes: 0 ok, 1 nothing found or not available, 2 refused, not configured, or usage.
"""
import argparse, email.policy, email.utils, mmap, os, re, sqlite3, subprocess, sys, time
from email.parser import BytesParser
from html.parser import HTMLParser

import json

CONFIG = os.path.expanduser(os.environ.get("OFFICE_EMAIL_ARCHIVE_CONFIG",
                                           "~/.config/office-skills/email-archive.json"))
_CFG = None


def cfg():
    """The setup: profile folder, the profile pref that names the archive, and a hint for errors."""
    global _CFG
    if _CFG is None:
        data = {}
        if os.path.exists(CONFIG):
            try:
                data = json.load(open(CONFIG, encoding="utf-8"))
            except (OSError, ValueError) as e:
                die("cannot read %s: %s" % (CONFIG, e))
        prof = (os.environ.get("OFFICE_EMAIL_ARCHIVE_PROFILE") or os.environ.get("MAIL_ARCHIVE_PROFILE")
                or data.get("profile"))
        if not prof:
            die("no archive profile configured: put {\"profile\": \"<Thunderbird profile folder>\"} in %s, "
                "or set OFFICE_EMAIL_ARCHIVE_PROFILE" % CONFIG)
        prof = os.path.expanduser(prof)
        _CFG = {"profile": prof, "userjs": os.path.join(prof, "user.js"),
                "pref": data.get("server_pref", "mail.server.server1.directory"),
                "hint": data.get("volume_hint", "Is the disk that holds it connected?")}
    return _CFG
BODY_MAX = 200_000          # characters of text per message kept in the index
SKIP_EXT = (".msf", ".dat", ".json", ".sqlite", ".html", ".txt", ".log")


def die(msg, code=2):
    # Double-clicked from Finder there is no terminal to read stderr, so say it in a dialog too.
    print(msg, file=sys.stderr)
    if not sys.stderr.isatty() and "1" not in (os.environ.get("OFFICE_EMAIL_ARCHIVE_NO_ALERT"),
                                                os.environ.get("MAIL_ARCHIVE_NO_ALERT")):
        subprocess.run(["osascript", "-e", 'display alert "Mail archive" message %s'
                        % ('"' + msg.replace('"', "'") + '"')], capture_output=True)
    sys.exit(code)


# ---- the profile -------------------------------------------------------------------------------
def pointed_dir():
    c = cfg()
    if not os.path.isdir(c["profile"]):
        die("no archive profile at %s" % c["profile"])
    try:
        text = open(c["userjs"], encoding="utf-8").read()
    except OSError:
        die("%s has no user.js yet: run  email-archive point <archive folder>  once" % c["profile"])
    m = re.search(r'user_pref\("%s",\s*"([^"]*)"\);' % re.escape(c["pref"]), text)
    if not m:
        die("%s has no %s line: run  email-archive point <archive folder>  once" % (c["userjs"], c["pref"]))
    return m.group(1)


def archive_running():
    # A plain scan, not `pgrep -f "-profile …"`: pgrep reads a pattern that starts with "-" as an
    # option and finds nothing. That bug let a test launch a real Thunderbird (2026-09-26).
    out = subprocess.run(["ps", "-axo", "command="], capture_output=True, text=True).stdout
    prof = cfg()["profile"]
    return any("thunderbird" in l.lower() and ("-profile " + prof) in l for l in out.splitlines())


def cmd_open(a):
    d = pointed_dir()
    if not os.path.isdir(d):
        die("the archive folder %s is not there. %s" % (d, cfg()["hint"]), 1)
    cmd = ["open", "-n", "-a", "Thunderbird", "--args", "-profile", cfg()["profile"], "-no-remote"]
    if archive_running():
        print("the archive Thunderbird is already open (%s)" % d)
        return 0
    if a.dry_run:
        print(" ".join(cmd)); return 0
    subprocess.run(cmd, check=True)
    print("opened the archive profile on %s" % d)
    return 0


def cmd_where(a):
    d = pointed_dir()
    print(d if os.path.isdir(d) else "%s   (NOT PRESENT. %s)" % (d, cfg()["hint"]))
    return 0


def cmd_point(a):
    new = os.path.abspath(os.path.expanduser(a.dir))
    if not os.path.isdir(new):
        die("%s is not a folder" % new)
    c = cfg()
    if not os.path.isdir(c["profile"]):
        die("no archive profile at %s: create it in Thunderbird's profile manager first" % c["profile"])
    if archive_running():
        die("quit the archive Thunderbird first: its settings are only safe to change while it is closed")
    USERJS, DIR_PREF, PROFILE = c["userjs"], c["pref"], c["profile"]
    text = open(USERJS, encoding="utf-8").read() if os.path.exists(USERJS) else ""
    line = 'user_pref("%s", "%s");' % (DIR_PREF, new)
    out, n = re.subn(r'user_pref\("%s",\s*"[^"]*"\);' % re.escape(DIR_PREF), lambda _: line, text)
    if n == 0:                                    # first setup: the profile has no such line yet
        out = (text.rstrip("\n") + "\n" if text else "") + line + "\n"
    elif n != 1:
        die("expected exactly one %s line in %s, found %d" % (DIR_PREF, USERJS, n))
    # THUNDERBIRD PREFERS THE RELATIVE PREF (found 2026-09-26): prefs.js keeps a "directory-rel"
    # from the last run, and it wins over "directory". Setting only "directory" left Thunderbird
    # on the deleted pilot folder, which it quietly recreated. So user.js carries both.
    rel_line = 'user_pref("%s-rel", "[ProfD]%s");' % (DIR_PREF, os.path.relpath(new, PROFILE))
    out, n = re.subn(r'user_pref\("%s-rel",\s*"[^"]*"\);' % re.escape(DIR_PREF), lambda _: rel_line, out)
    if n == 0:
        out = out.replace(line, line + "\n" + rel_line, 1)
    backup = USERJS + ".bak-" + time.strftime("%Y%m%d-%H%M%S")
    open(backup, "w", encoding="utf-8").write(text)
    open(USERJS, "w", encoding="utf-8").write(out)
    if pointed_dir() != new:
        die("wrote %s but it does not read back; the backup is %s" % (USERJS, backup))
    print("the archive profile now points at %s (backup: %s)" % (new, backup))
    return 0


# ---- the index ---------------------------------------------------------------------------------
def index_path(archive):
    return archive.rstrip("/") + ".index.sqlite"


def connect(path):
    db = sqlite3.connect(path)
    db.executescript("""
      CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, size INT, mtime REAL, messages INT);
      CREATE TABLE IF NOT EXISTS msgs(id INTEGER PRIMARY KEY, file TEXT, offset INT, length INT,
          mailbox TEXT, date TEXT, sender TEXT, recipients TEXT, subject TEXT, message_id TEXT,
          attachments TEXT);
      CREATE INDEX IF NOT EXISTS msgs_file ON msgs(file);
      CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(sender, recipients, subject, attachments,
          body, content='', contentless_delete=1, tokenize='unicode61 remove_diacritics 2');
    """)
    return db


def mbox_files(archive):
    for root, dirs, files in os.walk(archive):
        dirs[:] = sorted(d for d in dirs if d.endswith(".sbd"))   # .mozmsgs etc. are not mail
        for f in sorted(files):
            p = os.path.join(root, f)
            if f.startswith(".") or f.endswith(SKIP_EXT) or os.path.getsize(p) == 0:
                continue
            with open(p, "rb") as fh:
                if fh.read(5) == b"From ":
                    yield p


def mailbox_name(archive, path):
    return os.path.relpath(path, archive).replace(".sbd" + os.sep, "/")


def offsets(mm):
    starts, pos = [0], 0
    while True:
        pos = mm.find(b"\nFrom ", pos)
        if pos < 0:
            break
        starts.append(pos + 1); pos += 1
    ends = starts[1:] + [len(mm)]
    return list(zip(starts, ends))


class _Strip(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.out = []; self.skip = 0
    def handle_starttag(self, t, _):
        if t in ("script", "style"): self.skip += 1
    def handle_endtag(self, t):
        if t in ("script", "style") and self.skip: self.skip -= 1
    def handle_data(self, d):
        if not self.skip: self.out.append(d)


def text_of(msg):
    try:
        part = msg.get_body(preferencelist=("plain", "html"))
        if part is None:
            return ""
        s = part.get_content()
        if part.get_content_type() == "text/html":
            p = _Strip(); p.feed(s); s = " ".join(p.out)
        return re.sub(r"\s+", " ", s)[:BODY_MAX]
    except Exception:
        return ""


def attachments_of(msg):
    names = []
    for part in msg.walk():
        try:
            fn = part.get_filename()
        except Exception:
            fn = None
        if fn:
            names.append(fn)
    return " ; ".join(names)


def raw_message(mm, start, end):
    nl = mm.find(b"\n", start, end)                 # drop the mbox "From " separator line
    return mm[nl + 1:end] if nl >= 0 else mm[start:end]


def parse_one(raw):
    msg = BytesParser(policy=email.policy.default).parsebytes(raw)
    def h(k):
        try:
            return str(msg.get(k, "") or "")
        except Exception:
            return ""
    try:
        date = email.utils.parsedate_to_datetime(h("Date")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        date = ""
    recips = ", ".join(x for x in (h("To"), h("Cc")) if x)
    return date, h("From"), recips, h("Subject"), h("Message-ID"), attachments_of(msg), text_of(msg)


def cmd_index(a):
    archive = os.path.abspath(os.path.expanduser(a.dir)) if a.dir else pointed_dir()
    if not os.path.isdir(archive):
        die("%s is not there. %s" % (archive, cfg()["hint"]), 1)
    ipath = index_path(archive)
    db = connect(ipath)
    seen, done, skipped, errors, total = set(), 0, 0, 0, 0
    t0 = time.time()
    for path in mbox_files(archive):
        seen.add(path)
        st = os.stat(path)
        row = db.execute("SELECT size, mtime FROM files WHERE path=?", (path,)).fetchone()
        if row and row[0] == st.st_size and row[1] == st.st_mtime:
            skipped += 1; continue
        with db:
            old = [r[0] for r in db.execute("SELECT id FROM msgs WHERE file=?", (path,))]
            db.executemany("DELETE FROM fts WHERE rowid=?", [(i,) for i in old])
            db.execute("DELETE FROM msgs WHERE file=?", (path,))
            box, n = mailbox_name(archive, path), 0
            with open(path, "rb") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                for start, end in offsets(mm):
                    try:
                        date, frm, to, subj, mid, att, body = parse_one(raw_message(mm, start, end))
                    except Exception:
                        errors += 1; date = frm = to = subj = mid = att = body = ""
                    cur = db.execute("INSERT INTO msgs(file, offset, length, mailbox, date, sender, "
                                     "recipients, subject, message_id, attachments) VALUES "
                                     "(?,?,?,?,?,?,?,?,?,?)",
                                     (path, start, end - start, box, date, frm, to, subj, mid, att))
                    db.execute("INSERT INTO fts(rowid, sender, recipients, subject, attachments, body) "
                               "VALUES (?,?,?,?,?,?)", (cur.lastrowid, frm, to, subj, att, body))
                    n += 1
            db.execute("INSERT OR REPLACE INTO files VALUES (?,?,?,?)",
                       (path, st.st_size, st.st_mtime, n))
        done += 1; total += n
        print("  indexed %-60s %6d messages" % (box[:60], n), file=sys.stderr)
    gone = [p for (p,) in db.execute("SELECT path FROM files") if p not in seen]
    with db:
        for p in gone:
            old = [r[0] for r in db.execute("SELECT id FROM msgs WHERE file=?", (p,))]
            db.executemany("DELETE FROM fts WHERE rowid=?", [(i,) for i in old])
            db.execute("DELETE FROM msgs WHERE file=?", (p,))
            db.execute("DELETE FROM files WHERE path=?", (p,))
    count = db.execute("SELECT count(*) FROM msgs").fetchone()[0]
    print("index %s: %d mailboxes refreshed (%d messages), %d unchanged, %d removed, %d parse "
          "errors (indexed without text), %d messages in total, %.0f s"
          % (ipath, done, total, skipped, len(gone), errors, count, time.time() - t0))
    return 0


def open_index(a):
    archive = os.path.abspath(os.path.expanduser(a.archive)) if a.archive else pointed_dir()
    ipath = index_path(archive)
    if not os.path.exists(ipath):
        die("no search index for %s yet: run  email-archive index" % archive, 1)
    return connect(ipath)


def fts_query(terms, raw):
    if raw:
        return " ".join(terms)
    return " ".join('"%s"' % t.replace('"', '""') for t in terms)


def cmd_search(a):
    db = open_index(a)
    sql = ("SELECT m.id, m.date, m.mailbox, m.sender, m.subject FROM fts JOIN msgs m ON m.id=fts.rowid "
           "WHERE fts MATCH ?")
    args = [fts_query(a.terms, a.raw)]
    if a.mailbox:
        sql += " AND m.mailbox LIKE ?"; args.append("%" + a.mailbox + "%")
    if a.since:
        sql += " AND m.date >= ?"; args.append(a.since)
    if a.until:
        sql += " AND m.date <= ?"; args.append(a.until + " 99")
    sql += " ORDER BY " + ("m.date DESC" if a.by_date else "fts.rank") + " LIMIT ?"
    args.append(a.n)
    try:
        rows = db.execute(sql, args).fetchall()
    except sqlite3.OperationalError as e:
        die("search failed: %s (with --raw, check the FTS5 query syntax)" % e)
    for r in rows:
        print("%7d  %-16s  %-28s  %-30s  %s" % (r[0], r[1] or "-", (r[2] or "")[:28],
                                               (r[3] or "")[:30], r[4] or ""))
    print("%d hit(s)%s" % (len(rows), " (limit reached; use -n)" if len(rows) == a.n else ""),
          file=sys.stderr)
    return 0 if rows else 1


def fetch(a):
    db = open_index(a)
    row = db.execute("SELECT file, offset, length, mailbox FROM msgs WHERE id=?", (a.id,)).fetchone()
    if not row:
        die("no message %d in the index" % a.id, 1)
    path, off, length, box = row
    with open(path, "rb") as fh:
        fh.seek(off); data = fh.read(length)
    nl = data.find(b"\n")
    return data[nl + 1:], box


def cmd_show(a):
    raw, box = fetch(a)
    msg = BytesParser(policy=email.policy.default).parsebytes(raw)
    for k in ("Date", "From", "To", "Cc", "Subject"):
        if msg.get(k):
            print("%-8s %s" % (k + ":", msg.get(k)))
    print("%-8s %s" % ("Mailbox:", box))
    att = attachments_of(msg)
    if att:
        print("%-8s %s" % ("Attach:", att))
    print()
    print(text_of(msg) if a.flat else (msg.get_body(preferencelist=("plain", "html")) or msg).get_content())
    return 0


def cmd_eml(a):
    if os.path.exists(a.out):
        die("%s exists; not overwriting" % a.out)
    raw, _ = fetch(a)
    open(a.out, "wb").write(raw)
    print("wrote %s (%d bytes)" % (a.out, len(raw)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="email-archive", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    o = sub.add_parser("open", help="open the archive in its own Thunderbird profile")
    o.add_argument("--dry-run", action="store_true", help="print the command, do not run it")
    sub.add_parser("where", help="print the archive folder the profile points at")
    p = sub.add_parser("point", help="point the profile at another archive folder")
    p.add_argument("dir")
    i = sub.add_parser("index", help="build or refresh the search index")
    i.add_argument("dir", nargs="?")
    s = sub.add_parser("search", help="search the archive")
    s.add_argument("terms", nargs="+")
    s.add_argument("-n", type=int, default=25)
    s.add_argument("--mailbox"); s.add_argument("--since"); s.add_argument("--until")
    s.add_argument("--by-date", action="store_true", help="newest first instead of best match")
    s.add_argument("--raw", action="store_true", help="pass TERMS as an FTS5 query, e.g. 'subject:budget'")
    s.add_argument("--archive")
    sh = sub.add_parser("show", help="print one message")
    sh.add_argument("id", type=int); sh.add_argument("--archive")
    sh.add_argument("--flat", action="store_true", help="HTML stripped to text")
    e = sub.add_parser("eml", help="write one message as .eml")
    e.add_argument("id", type=int); e.add_argument("out"); e.add_argument("--archive")
    a = ap.parse_args(argv)
    if a.cmd is None:
        a = ap.parse_args(["open"] + (argv or sys.argv[1:]))
    return {"open": cmd_open, "where": cmd_where, "point": cmd_point, "index": cmd_index,
            "search": cmd_search, "show": cmd_show, "eml": cmd_eml}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
