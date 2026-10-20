---
name: email-sweep
description: Sweep the mail inbox since the last sweep for actionable signals (deadlines, requests that need a reply or a decision), triage them with the person, and file each one where it belongs (the todo list with a deadline, a project's file, a notes file, or a question). The bridge from email into the files your sessions read. Use at the start of a working day or a daily brief, or when asked to "sweep email", "check the inbox for deadlines", "what came in by email".
---

# email-sweep: from the mail inbox into your files

**For macOS Mail.app, through AppleScript, for now.**

Nothing else reads the mail inbox. A deadline in an unread email is invisible to every todo
list, brief and audit, because all of them assume an item has already been written down. That is
how deadlines get missed. This skill reads the inbox, finds what needs action, and files it with a
deadline where the rest of your setup will see it.

**It captures; it does not remind.** Once an item is on the todo list with a deadline, whatever
reads that list every morning (a daily brief, a todo report) carries it. Do not build a second
reminder loop here.

## Where things go: the setup

The sweep files into places the setup names. Find them in this order:

1. `~/.config/session-dashboard/where.json`, if it exists. It gives `todo` (the todo list),
   `register` (the register of work, which names each project and where it lives), `inbox` (a
   capture file for unclear items) and `hub` (the folder that holds them).
2. Otherwise, or for what where.json does not name, `~/.config/office-skills/email-sweep.json`:

   | Key | What it names | If missing |
   |---|---|---|
   | `todo` | the todo list file | ask |
   | `register` | a file listing projects and their folders, to route project items | file project items as todos |
   | `notes` | a notes file for operational knowledge that is not a task | ask, or use `inbox` |
   | `inbox` | a capture file for items that are unclear | ask |
   | `state` | the watermark file | `<hub>/.email-sweep-state.md`, or `~/.config/office-skills/email-sweep-state.md` |
   | `reports` | the folder for each run's ledger | `email-sweep-reports/` beside the todo list |
   | `account`, `inbox_mailbox` | the Mail account and inbox to sweep | ask; note that some account types call it `Inbox` and others `INBOX`, and the wrong case fails with error -1728 |
   | `sent_accounts` | accounts whose Sent boxes to check | every account |
   | `noise` | sender or subject patterns that are never actionable | the categories in step 4 |
   | `calendar` | a calendar for optional deadline reminders | none; ask per item |

3. If neither names a place, ask the person once, and offer to write the config file.

## State: the watermark, which makes this reliable

The failure is "I didn't run the sweep". The watermark makes a missed run heal itself: every run
covers last-swept to now, so skipping the sweep for days still catches everything next time.

The state file holds:
- `last-swept:` the ISO timestamp of the previous **completed** sweep;
- `triaged-ids:` message IDs already shown and dismissed, so re-runs don't show them again. Keep
  the most recent ~200 and prune older ones.

**First run, or no watermark:** if `last-swept` is missing or reads `UNINITIALIZED`, look back
**14 days** and say so: "No prior sweep recorded, so scanning the last 14 days. Say a different
window if you want." The person may choose another window ("last 30 days", "since June 1").

## Workflow

1. **Get today's date and time** with `date "+%Y-%m-%d %H:%M:%S %Z"`. Never trust a date from
   earlier in a long conversation.

2. **Read the watermark** and set the start of the window (the watermark, or 14 days on a first
   run).

3. **Pull every header since the watermark: no bodies, no cap.** Headers are cheap and bodies are
   not. Reading every body and stopping at N silently drops the *oldest* mail, which is exactly
   where a missed deadline hides. So take the whole window's headers first, and read bodies only
   for what survives the noise filter (step 4).
   ```bash
   osascript <<'APPLESCRIPT'
   tell application "Mail"
     set mbox to mailbox "Inbox" of account "ACCOUNT"     -- from the setup
     set cutoff to (current date) - N * days              -- from the watermark
     set newMsgs to (messages of mbox whose date received > cutoff)
     log "TOTAL:" & (count of newMsgs)
     repeat with m in newMsgs
       log (date received of m as text) & " || " & (sender of m) & " || " & (subject of m) & " || ATT:" & (count of mail attachments of m)
     end repeat
   end tell
   APPLESCRIPT
   ```
   Build dates as `(current date) - N * days`. A literal date string inside a `whose` clause can
   fail silently and return nothing.

3b. **A long window is pulled in slices, never in one query.** "No cap" is about coverage; this is
   about how the window is read. One long query can lock Mail for many minutes while the person is
   trying to use it.

   **Slice anything longer than about 7 days** into windows of about four days, with **one
   separate `osascript` process per slice**, appending to one file. A short query finishes before
   Mail gives up, and a slice that fails costs only its own four days.

   ```bash
   for HI in 0 4 8 12 16 20; do
     LO=$((HI+4))
     osascript <<APPLESCRIPT >> "$OUT" 2>&1
   with timeout of 600 seconds
     tell application "Mail"
       set mbox to mailbox "Inbox" of account "ACCOUNT"
       set lo to (current date) - $LO * days
       set hi to (current date) - $HI * days
       repeat with m in (messages of mbox whose date received > lo and date received < hi)
         log (date received of m as text) & " || " & (sender of m) & " || " & (subject of m)
       end repeat
     end tell
   end timeout
   APPLESCRIPT
   done
   ```

   **Three failure modes, easily mistaken for one another:**

   | Symptom | Cause | Not fixed by |
   |---|---|---|
   | output stops mid-window, no error | piping the dump through `head -N` | anything. It is a bug in the caller, and it silently drops the OLDEST mail |
   | `AppleEvent timed out (-1712)` | Mail gave up on a long `whose` | a longer *shell* timeout; the limit is in the Apple Event layer, so use `with timeout of N seconds` |
   | `Connection is invalid (-609)` after a few messages | Mail dropped a connection held too long | waiting; only shorter queries help |

   **Repeated Apple Event errors mean stop, not retry.** Mail is a foreground application the
   person is using, and a sweep has no claim on it. Two consecutive Apple Event failures end the
   run: report the partial result, leave the watermark, and say what was not covered. Treating each
   error as a puzzle to route around is how a sweep ends up locking Mail for many minutes.

   **Never redirect a pull to a file you then overwrite.** A clobbered dump has to be pulled again,
   which is exactly the extra load Mail does not need.

   **Never test `content` inside a `whose` clause.** `content` is the whole message body, and Mail
   evaluates it by loading the body of every message in the mailbox, on its main thread, so the
   app freezes until it finishes. Killing the `osascript` does not stop it. `whose` may test only
   cheap header fields: `subject`, `sender`, `date received`, `date sent`, `read status`, `flagged
   status`. Read bodies one message at a time, for a capped list, as in step 5.

4. **Filter the noise by sender and subject, from the headers alone.** Most inbox volume is
   automated bulk that never carries a personal action. Drop these from the candidates, without
   reading their bodies:
   - **Newsletters and digests:** news sites, Substack and similar, journal and magazine briefings,
     vendor marketing.
   - **Automated notifications:** chat and forum notifications, mailing-list moderator requests,
     literature alerts and preprint digests, list-server traffic (*unless* a person is clearly
     asking something), voting systems, calendar and renewal confirmations, spam-quarantine
     notices.
   - **Receipts and statements:** keep them as records, not tasks, unless they ask for an
     approval.
   - The setup's own `noise` patterns, if it has any.

   **Keep** anything from a real person, and anything that names an approval, signature,
   deadline, payment, RSVP, review or scheduling request, even from an automated sender (an
   approval workflow, a data-deletion notice). **When unsure, keep it.** Report the noise and keep
   counts, so the filter stays honest: no silent drops.

5. **Read the bodies of the survivors only**, in batches, oldest first. Cut each body to about
   1400 characters, which is enough to spot a deadline or a request. If there are more than about
   60, read them in pages and say so. Skip IDs already in `triaged-ids`.

6. **Classify each survivor** from subject and body. This is judgement, not a keyword match: catch
   paraphrased deadlines like "before the board meets Friday".

   | Class | Signal | Proposed action |
   |---|---|---|
   | **A: action, hard deadline** | an explicit or paraphrased due date, "sign and return", "RSVP by", "submit by", "respond by", a registration cutoff | a todo with its deadline |
   | **B: action, no date** | a request to the person for a reply, decision or task, with no date | a todo; ask for a deadline or a default |
   | **C: FYI, no action** | newsletter, notification, cc only, already handled | skip; record the ID in `triaged-ids` |

   For class A, resolve relative dates ("next Friday") against today's date and show the ISO date
   you inferred, so the person can correct it. Mark a date you are unsure of `[verify]`.

6b. **Check the Sent boxes for what is already answered.** People often reply on the spot, outside
   any list. Without this check, such an email resurfaces as "needs a reply" on every run. Before
   presenting, scan the Sent boxes and mark what looks handled.

   Pull Sent headers since the watermark, across the setup's `sent_accounts` (every account by
   default):
   ```bash
   osascript <<'APPLESCRIPT'
   tell application "Mail"
     set cutoff to (current date) - N * days
     repeat with acct in every account
       repeat with boxName in {"Sent", "Sent Items", "Sent Messages"}
         try
           set sbox to mailbox (boxName as text) of acct
           repeat with m in (messages of sbox whose date sent > cutoff)
             repeat with r in (to recipients of m)
               log (date sent of m as text) & " || TO:" & (address of r) & " || " & (subject of m)
             end repeat
           end repeat
         end try
       end repeat
     end repeat
   end tell
   APPLESCRIPT
   ```

   **Match by subject**, because AppleScript cannot follow Mail's threads reliably. An inbox
   candidate from sender **S** with subject **X**, received at **T**, is "likely handled" if a Sent
   message went **to S** with a matching subject after **T**. Before comparing, strip leading
   `Re:`, `Fwd:`, `AW:`, `WG:` and trim.

   **Flag and confirm, never drop silently.** A reply is not always a resolution ("I'll get back to
   you"). Keep likely-handled items in the table, mark them, and **default them to skip**; the
   person confirms. A changed subject line means a miss, and the item shows once more. That is
   acceptable.

7. **Present the candidates in one compact table**, and let the person approve them in a batch.
   Show the already-replied flag; likely-handled items default to skip:
   ```
   === Email Sweep, YYYY-MM-DD (since LAST-SWEPT) ===
   Scanned N messages · F noise-filtered · M actionable · H look already-handled

   #  From             Subject                          Deadline      Status            → Proposed
   1  A. Colleague     Award nominations due            2026-06-15    -                 todo (Urgent)
   2  Grants office    Amendment: sign & return        2026-06-12    replied 06-17 ↩   skip (confirm?)
   3  B. Collaborator  Curriculum follow-up             (none)        -                 todo; set deadline?
   ...
   Approve all / edit (# date|dest) / keep # (override a skip) / skip # / done
   ```
   For each item the person can approve it, change the deadline or the destination, skip it, or
   **keep** an item that was skipped as already replied but is not resolved.

8. **File the approved items:**
   - **A task of the person's own** → the **todo list**, in
     the list's own line format, for example `- [ ] Description, Priority: X, Deadline: YYYY-MM-DD`. Items due today or overdue go at
     the top, under the list's "today" heading if it has one.
   - **Belongs to a project in the register** → that project's own file, under its todos, with
     "(from email sweep)".
   - **Operational knowledge, not a task** → the **notes** file.
   - **Unclear** → the **inbox** capture file, for later triage.
   - **Needs the person's decision before it can be filed anywhere** → a question they can answer
     in a sentence. If the setup has review cards (the session dashboard's), raise a card;
     otherwise ask in the conversation *and* record it in the inbox file. **Dismissing a question
     is cheap; losing an item is not.**
   - **A hard external deadline (optional, ask first):** offer a calendar reminder with lead time
     (the `calendar` skill), one confirmation per item. No background jobs: the todo list and the
     brief carry it.

9. **Update the state.** Set `last-swept:` to the timestamp from step 1, append the IDs of the
   survivors you showed (filed and skipped) to `triaged-ids`, and prune to ~200. Bulk mail removed
   by the noise filter need not be recorded, because the watermark covers it.

10. **Write the ledger, and announce project filings.** An item filed into a project's file is
    recorded, but nobody is looking there: a brief reads the todo list, not every project file.
    Filing into a project without saying so is the same loss as not filing.

    - **A ledger file every run**, `<reports>/YYYY-MM-DD.md` (add `-2` for a second run that day),
      with sections in this order:
      1. **Filed into projects**, grouped by project: one line per item with sender, date, what is
         asked, deadline, and **the file it went to**. This is why the ledger exists, so it comes
         first.
      2. Filed to the todo list, with deadlines.
      3. Questions raised (cards or inbox entries).
      4. Notes and inbox entries.
      5. Already replied (skipped, awaiting the person's confirmation).
      6. Counts (scanned, noise, kept) and the slices that ran.
    - **If anything went into a project, one announcement per run:** a review card if the setup
      has them, titled `Email sweep YYYY-MM-DD: N items filed into projects`. It lists *project, one-line
      ask, deadline* per item, names the ledger file, and ends **FYI, nothing owed
      unless a line is wrong**. Otherwise give the same list in the closing summary. If nothing went
      into a project, there is no announcement.
    - **The closing summary comes last:** "Swept N messages since LAST-SWEPT (F noise, M
      actionable). Filed K to the todo list, J into projects, C questions." Called from a daily
      brief, hand the new deadlines and the project-filed items back to the brief.

## Rules

- **Never send, reply to, file, move or delete email.** This skill only reads the inbox and the
  Sent boxes, and writes the setup's files. Managing mail in Mail.app stays with the person.
- **Record first, approve second.** The approval gate governs *acting* on an item, not *recording*
  it. File the item, then seek confirmation. An unconfirmed line in the todo list costs one line to
  delete, and an unrecorded item costs a missed deadline. A person cannot disposition hundreds of
  findings in one sitting, and the ones they don't reach must not vanish.
- **Already replied is flag-and-confirm, never a silent drop.** Sent-box evidence lowers an item's
  priority; it does not authorise dropping it.
- **No silent caps.** Headers cover the whole window. Only body reading is paged, and if it is,
  say so. Report the noise and keep counts, so the filter can be checked.
- **Slice a long window, never one query.** Over ~7 days, pull ~4-day slices, one `osascript`
  process each, inside `with timeout of 600 seconds` (step 3b).
- **Two consecutive Apple Event errors end the run.** Report the partial result and leave the
  watermark. Mail belongs to the person, not to the sweep.
- **Headers first, always.** Never read every body and then cap: that drops the oldest mail, the
  exact failure this skill exists to prevent.
- **Never `content` in a `whose` clause** (step 3b).
- **Verify inferred dates.** Show the ISO date computed from any relative reference, and mark
  uncertain ones `[verify]`.
- **The watermark advances only on a completed run.** A run is completed when **every actionable
  item has a home**, not when the script finished. If the sweep is interrupted, leave `last-swept`
  unchanged so the next run covers the gap again.

### Todo, question, or drop: the routing test

Questions to the person are a triage tool, not an overflow bin. Used well, they keep the todo list
clean: what remains there is work, not a mix of work and unresolved questions. One test:

> **Does the person's answer change what happens next?**

| | |
|---|---|
| **Todo** | The action is already determined; only *when* is open. Their answer changes nothing. "Sign the form." |
| **Question** | The next action is undefined until they supply something only they have. Two different outcomes hang on one sentence. |
| **Drop** | No action, no decision, no cost to silence. Log the drop in the ledger; do not surface it. |

**The easiest signal in the moment:** *received requests are todos; findings the sweep produced
are questions.* Someone asking for a signature is a task with an owner. "These two emails
contradict each other" is something **nobody asked about**. It surfaced only because the sweep
compared two sources, and it has no owner until the person gives it one.

An example of the difference: a collaborator writes that their team must book travel now for a
meeting the person declined a month earlier. Neither email says anything is wrong; the finding
exists only in the pairing. As a todo it reads as a vague "reply to them" that sits for weeks. As a
question it asks the one thing that resolves it, *did you tell them?*, where "yes" costs a click
and "no" keeps a collaborator from spending money on a false premise.

**Inference alone does not make a question; an unresolved action does.** If the next step is the
same whatever the person says (relay an answer that arrived elsewhere), it stays a todo, with the
finding written into it.

**When genuinely unsure, ask.** Dismissing a question costs a click. A dropped item costs a missed
deadline. A decision buried in the todo list costs both: it cannot be done, so it rots there and
devalues everything around it.

### Hardening

These rules come from a real loss. A run once detected a signature request, named it in its own
notes and mentioned it in the conversation, but never wrote it anywhere. The watermark then
advanced, marking the window as swept. Every step had reported success, and the person later did
the task unprompted.

- **The conversation is not a destination.** Reporting an item in chat is *not* filing it. The
  session ends and the item is gone, while the watermark says the window was covered. An item is
  filed when it is in a file: the todo list, a project, the notes, the inbox, or a review card.
- **In doubt, file it.** Prefer a spurious todo or a dismissable question to a judgement that
  something was probably handled.
- **A paused run leaves a stub.** Before stopping mid-sweep, write the undecided items to the inbox
  file (or as questions) with their dates and senders. The next run will re-read the mail, but it
  will not know what this run had already judged.
- **Project filings are surfaced, not buried.** Every item filed into a project appears in the
  run's ledger and in its announcement (step 10).
- **Report the ledger, not just the count.** The closing report states *where each actionable item
  went*. "Surfaced N items" is not an outcome; "filed N, asked M, dismissed K" is. An item you
  cannot name a destination for is the finding.

## State file template

```markdown
# Email Sweep State
last-swept: UNINITIALIZED
triaged-ids:
```

## This setup's own rules

If this setup has an addendum for this skill, read it now: the file `email-sweep.md` in the folder
`addenda` names in `~/.config/session-dashboard/where.json`, or, without that file, in
`~/.config/office-skills/addenda/`. Where it differs from the text above, it wins.
