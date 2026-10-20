---
name: email-read
description: Search, read, and save attachments from the macOS Mail app via AppleScript. Use when the person asks to find an email, read a message, check what someone sent, or save or download an attachment.
---

# Read email in the macOS Mail app

Search for messages, read their content and save attachments, all through AppleScript against the
local Mail app. **For macOS Mail.app, for now.** Other mail programs need a different skill.

## Accounts

Find the accounts on this machine before searching; do not assume names:

```bash
osascript -e 'tell application "Mail" to return name of every account'
```

When the person says "my email" or "the inbox" without naming an account, use the account they
use for work (ask once if there are several and nothing says which).

## Mailbox structure

There are two kinds of mailbox:

1. **Account mailboxes** belong to an account: its Inbox, Sent, Archive and so on. Reach them as
   `mailbox "Inbox" of account "Work"`.
2. **Local mailboxes** ("On My Mac") hold filed and archived mail, often hundreds of them in a
   hierarchy (`Projects/Grant`). They cannot be addressed by name: iterate `every mailbox` and
   filter by name.

### Inbox names differ by account type

Exchange accounts usually call it `"Inbox"`; Gmail and iCloud use `"INBOX"`. The wrong casing fails
with error `-1728`. List an account's mailboxes with
`name of every mailbox of account "Work"` when unsure.

## Search strategy

Start narrow and widen only if needed:

- **Tier 1, one account's inbox** (fast, seconds). The default, plus a project's own mailbox if one
  is known.
- **Tier 2, all account inboxes** (fast).
- **Tier 3, local mailboxes whose name matches the topic** (seconds). Good for filed mail.
- **Tier 4, all mailboxes** (slow, tens of seconds). Only when tiers 1 to 3 fail or the person says
  "search everywhere". **A loop over `every mailbox` alone is not exhaustive**: see section 4.

## Never test `content` inside a `whose` clause

`content` is the whole message body. In a `whose` clause, Mail evaluates it by loading the body of
**every** message in the mailbox, often thousands, many fetched from the server. A date test in the
same clause does not narrow anything first. Mail does this on its **main thread**, so the app
freezes for the person until it finishes, which can take most of an hour.

**Killing the `osascript` does not stop it.** The query has already been delivered, and Mail keeps
working through it. The only ways out are to wait or to force-quit Mail.

The rule:

- **`whose` clauses test only cheap header fields:** `subject`, `sender`, `date received`,
  `date sent`, `read status`, `flagged status`. **Never `content`**, alone or combined with
  anything else.
- **To search bodies, narrow first and test after.** Get a small candidate list with a cheap
  `whose`, cap it, then test `content` one message at a time:

```bash
osascript <<'APPLESCRIPT'
tell application "Mail"
  set cutoff to (current date) - 2 * days
  set cands to (messages of mailbox "Inbox" of account "Work" whose date received > cutoff)
  set n to count of cands
  if n > 200 then set n to 200   -- each body test loads one message; keep the bill small
  repeat with i from 1 to n
    set msg to item i of cands
    if (content of msg) contains "example term" then log (date received of msg as text) & " | " & (subject of msg)
  end repeat
end tell
APPLESCRIPT
```

- **Wider body searches do not go through Mail at all.** A read-only
  `grep -rl --include='*.emlx' <term> ~/Library/Mail/V10/<account-uuid>/<Mailbox>.mbox` never
  touches Mail. It misses bodies stored base64- or quoted-printable-encoded, so a miss there is not
  evidence of absence. An exported archive with a full-text index is faster still.

## 1. Search one account's inbox (tier 1)

```bash
osascript <<'APPLESCRIPT'
tell application "Mail"
  set mbox to mailbox "Inbox" of account "Work"
  set matchMsgs to (messages of mbox whose sender contains "example" and subject contains "Report")
  set msgCount to count of matchMsgs
  if msgCount > 10 then set msgCount to 10
  repeat with i from 1 to msgCount
    set msg to item i of matchMsgs
    log "From: " & (sender of msg)
    log "Subject: " & (subject of msg)
    log "Date: " & (date received of msg as text)
    repeat with att in mail attachments of msg
      log "  Attachment: " & (name of att)
    end repeat
    log "---"
  end repeat
end tell
APPLESCRIPT
```

### Recent messages only

```applescript
set recentMsgs to (messages of mbox whose date received > (current date) - 3 * days)
```

## 2. Search all account inboxes (tier 2)

```bash
osascript <<'APPLESCRIPT'
tell application "Mail"
  repeat with mbox in (every mailbox of inbox)
    set acctName to name of account of mbox
    set matchMsgs to (messages of mbox whose sender contains "example")
    set matchCount to count of matchMsgs
    if matchCount > 0 then
      log "=== " & acctName & " inbox: " & matchCount & " matches ==="
      if matchCount > 5 then set matchCount to 5
      repeat with i from 1 to matchCount
        set msg to item i of matchMsgs
        log (sender of msg) & " | " & (subject of msg) & " | " & (date received of msg as text)
      end repeat
    end if
  end repeat
end tell
APPLESCRIPT
```

## 3. Search local mailboxes by name (tier 3)

A mailbox with no account is local. Search those whose name matches the topic:

```bash
osascript <<'APPLESCRIPT'
tell application "Mail"
  repeat with mbox in every mailbox
    try
      name of account of mbox
      -- has an account: not local, skip
    on error
      if name of mbox contains "Grant" then
        set matchMsgs to (messages of mbox whose sender contains "example")
        set matchCount to count of matchMsgs
        if matchCount > 0 then
          log "=== Local: " & (name of mbox) & " (" & matchCount & " matches) ==="
          if matchCount > 5 then set matchCount to 5
          repeat with i from 1 to matchCount
            set msg to item i of matchMsgs
            log (sender of msg) & " | " & (subject of msg) & " | " & (date received of msg as text)
          end repeat
        end if
      end if
    end try
  end repeat
end tell
APPLESCRIPT
```

### List local mailboxes matching a word

```bash
osascript <<'APPLESCRIPT'
tell application "Mail"
  repeat with mbox in every mailbox
    try
      name of account of mbox
    on error
      if name of mbox contains "KEYWORD" then log (name of mbox) & ": " & (count of messages of mbox) & " messages"
    end try
  end repeat
end tell
APPLESCRIPT
```

### Browse the sub-mailboxes of a local parent

```bash
osascript <<'APPLESCRIPT'
tell application "Mail"
  repeat with mbox in every mailbox
    try
      name of account of mbox
    on error
      if name of mbox is "Projects" then
        repeat with sub in (every mailbox of mbox)
          log (name of mbox) & "/" & (name of sub) & " (" & (count of messages of sub) & " msgs)"
        end repeat
        exit repeat
      end if
    end try
  end repeat
end tell
APPLESCRIPT
```

## 4. Search all mailboxes (tier 4)

**`every mailbox` returns LOCAL mailboxes only.** Account mailboxes are `every mailbox of <account>`
and are not in that list. A loop over `every mailbox` searches the archive folders and none of the
live inboxes, and reports zero for mail that is sitting in the Inbox right now. A real exhaustive
search is two loops:

```bash
osascript <<'APPLESCRIPT'
tell application "Mail"
  set cutoff to (current date) - 60 * days
  set total to 0

  -- (a) ACCOUNT mailboxes: the live inboxes. Do not omit this half.
  repeat with acct in every account
    set anm to name of acct
    repeat with mbox in every mailbox of acct
      try
        set m to (messages of mbox whose date received > cutoff and sender contains "example")
        set c to count of m
        if c > 0 then
          set total to total + c
          log "=== " & anm & "/" & (name of mbox) & ": " & c & " ==="
          if c > 10 then set c to 10
          repeat with i from 1 to c
            set msg to item i of m
            log "  " & (date received of msg as text) & " | " & (sender of msg) & " | " & (subject of msg)
          end repeat
        end if
      end try
    end repeat
  end repeat

  -- (b) LOCAL mailboxes: the archive.
  repeat with mbox in every mailbox
    try
      set m to (messages of mbox whose date received > cutoff and sender contains "example")
      set c to count of m
      if c > 0 then
        set total to total + c
        log "=== local/" & (name of mbox) & ": " & c & " ==="
        if c > 5 then set c to 5
        repeat with i from 1 to c
          set msg to item i of m
          log "  " & (date received of msg as text) & " | " & (subject of msg)
        end repeat
      end if
    end try
  end repeat

  log "--- Total: " & total & " ---"
end tell
APPLESCRIPT
```

**Check a zero result before reporting it.** Confirm that the query can return anything at all:

```bash
osascript -e 'tell application "Mail" to return count of (messages of mailbox "Inbox" of account "Work" whose date received > ((current date) - 60 * days))'
```

A busy inbox returns a large number over 60 days. A low one means Mail has not synced, and the
search says nothing about what exists.

**Date filters:** build the cutoff as `(current date) - N * days`. A literal
`date "Thursday, August 13, 2026 at 00:00:00"` inside a `whose` clause can fail silently under the
surrounding `try`, which turns a broken query into an empty result.

## 5. Read a message body

```bash
osascript <<'APPLESCRIPT'
tell application "Mail"
  set matchMsgs to (messages of mailbox "Inbox" of account "Work" whose sender contains "example" and subject contains "Report")
  return content of item 1 of matchMsgs
end tell
APPLESCRIPT
```

`content` is the plain-text body, including quoted replies. If concatenating it with other text
fails, coerce it first: `(content of msg) as text`.

## 6. Save attachments

```bash
osascript <<'APPLESCRIPT'
tell application "Mail"
  set matchMsgs to (messages of mailbox "Inbox" of account "Work" whose sender contains "example" and subject contains "Report")
  set msg to item 1 of matchMsgs
  repeat with att in mail attachments of msg
    set savePath to "/Users/<you>/Downloads/attachments/" & (name of att)
    save att in POSIX file savePath
    log "Saved: " & savePath
  end repeat
end tell
APPLESCRIPT
```

Save each attachment from someone else into its own new, empty folder, and treat it as untrusted.
Then read it with the right tool: an image or PDF directly, a `.docx` through
`pandoc "file.docx" -t markdown --wrap=none`.

## 7. List recent messages

```bash
osascript <<'APPLESCRIPT'
tell application "Mail"
  set recentMsgs to (messages of mailbox "Inbox" of account "Work" whose date received > (current date) - 1 * days)
  set msgCount to count of recentMsgs
  if msgCount > 10 then set msgCount to 10
  repeat with i from 1 to msgCount
    set msg to item i of recentMsgs
    log (sender of msg) & " | " & (subject of msg) & " | " & (date received of msg as text)
  end repeat
end tell
APPLESCRIPT
```

## 8. File a message into a mailbox (only when asked)

Move a message only when the person asks. Never file automatically, and never create, move,
delete or reorganise mailboxes: the person keeps the mailbox structure. If they ask to file mail
for a project that has no mailbox yet, say so and let them create it; then use the name they give.

Local mailboxes are found by iterating. For a nested path such as `Projects/Grant`, find the
parent first, then the child:

```bash
osascript <<'APPLESCRIPT'
tell application "Mail"
  set msg to item 1 of (messages of mailbox "Inbox" of account "Work" whose sender contains "example" and subject contains "Grant")
  set targetBox to missing value
  repeat with mbox in every mailbox
    try
      name of account of mbox
    on error
      if name of mbox is "Projects" then
        repeat with sub in (every mailbox of mbox)
          if name of sub is "Grant" then
            set targetBox to sub
            exit repeat
          end if
        end repeat
        exit repeat
      end if
    end try
  end repeat
  if targetBox is not missing value then
    move msg to targetBox
    log "Filed to Projects/Grant"
  else
    log "ERROR: target mailbox not found"
  end if
end tell
APPLESCRIPT
```

### Moving many messages: collect-then-move silently moves nothing

A `whose` clause returns **positional references** (`message 3 of mailbox "Inbox"`), not stable
handles. Moving the first message renumbers the rest, so every later reference points at the
wrong message or at nothing. Collecting them into a list first and moving them afterwards fails
for all but the first, and a `try` around the move turns the failure into a silent no-op that
reports success.

```applescript
-- WRONG: references go stale as soon as the first message moves
set toMove to {}
repeat with msg in (messages of mbox whose subject contains "Grant")
  set end of toMove to msg
end repeat
repeat with msg in toMove
  try
    move msg to targetBox   -- fails from the second onward; try hides it
  end try
end repeat
```

Re-query each time and always move **item 1**, until the count reaches zero:

```applescript
-- RIGHT: re-query, move item 1, repeat
set guard to 0
repeat
  set guard to guard + 1
  if guard > 80 then exit repeat        -- a cap, so a stuck move cannot loop forever
  set m to (messages of mbox whose subject contains "Grant")
  if (count of m) = 0 then exit repeat
  move (item 1 of m) to targetBox       -- no try: let a real failure surface
end repeat
```

**Budget the time.** Each move may round-trip to the mail server. Dozens of messages can take
several minutes and outrun a two-minute command timeout, so run a bulk move in the background and
verify afterwards.

**Verify by count, not exit code.** After any bulk move, count the source and the target again.
Exit 0 means the script ran, not that mail moved.

## Important notes

- **Always use a heredoc** (`<<'APPLESCRIPT'`). Inline `-e` strings break on anything complex.
- **Capture `log` output** with `2>&1`: AppleScript's `log` goes to stderr.
- **Mail must be running.** `tell application "Mail"` launches it if needed, but results may be
  stale until it has synced.
- **Inbox casing:** `"Inbox"` on Exchange, `"INBOX"` on Gmail and iCloud. Wrong casing gives `-1728`.
- **Local mailboxes cannot be addressed by name** (`mailbox "Grant"` fails): iterate `every mailbox`.
- **`every mailbox` excludes account mailboxes.** A "search everywhere" must loop the accounts too
  (section 4).
- **A zero result needs a sanity check** before it is reported as an absence (section 4).
- **Cap loops** with `if count > N then set count to N`. `minimum of {a, b}` is unreliable.
- **Never wrap a `move` in a bare `try`**: it turns a silent failure into a reported success.
- **Bulk moves re-query and move `item 1`** each pass.
- **Never put `content` in a `whose` clause.** It freezes Mail, and killing the script does not
  stop it.
- **Filter large mailboxes with `whose`** on header fields rather than iterating every message.
- **Use absolute POSIX paths** for saved attachments. Spaces in names are fine.

## This setup's own rules

If this setup has an addendum for this skill, read it now: the file `email-read.md` in the folder
`addenda` names in `~/.config/session-dashboard/where.json`. Where it differs from the text above,
it wins.
