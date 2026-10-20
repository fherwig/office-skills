---
name: calendar-poll
description: Answer a scheduling poll (when2meet; the method carries to Doodle and similar) from the person's calendar. Read the poll's grid, work out their free blocks from Calendar.app (including repeating events and public holidays), show them the plan, and on their go-ahead mark the blocks in their signed-in Chrome tab, then verify against the server. Use for "fill in the when2meet", "answer the poll", "put my availability in the doodle", "look at my calendar and fill in the poll".
---

# Calendar poll

Works on macOS: the person's calendar in Calendar.app through AppleScript, and the poll in their
own signed-in Google Chrome tab, for now. Every rule below is something that went wrong or cost
time on a real poll.

## The one fact that changes the plan: when2meet has no draft

**Entering a name, and every cell marked, is saved to the poll the instant it happens.** There is
no submit button and no unsubmitted state. So "fill it in but don't submit, let me review" cannot
be done on the live page. Say so up front, then:

1. Work out the free blocks and **show them as a table** (step 3). That table *is* the review.
2. Mark the poll only after the person says go. They may sign in themselves first, which is fine
   and saves a step.

Never type a name into the poll's sign-in box unless the person asked: the name they choose is
what the other participants see.

## Workflow

`H=<this skill's folder>/scripts; PY=python3` (Python 3.9 or newer; `expand_recurring.py` needs
`python-dateutil`).

### 1. Find the poll and read its grid

The link usually comes by email. Then:

```bash
$PY $H/when2meet.py inspect "<url>"     # days, hours (in the person's time zone), participants so far
open "<url>"                             # viewing is harmless; it posts nothing
```

The helper shows times in the person's zone: the `POLL_TZ` environment variable, else `"tz"` in
`~/.config/office-skills/calendar-poll.json`, else this computer's zone. **Check the grid's hours
in that zone.** Someone abroad builds the grid in their own zone, so much of it may fall overnight
for the person. Note where the other participants are: it decides which free blocks are actually
useful, and is worth one line in the answer.

### 2. Get the person's busy times: ask for a screenshot first

**A screenshot of their Calendar week view is the fastest and most reliable input.** Ask for one
per poll week if the poll spans more than one. It shows repeating events, holidays, tentative holds
and all-day items in one image, where the scripted route is slow and needs several passes.

The scripted fallback, and what it gets wrong:

- Calendar.app's AppleScript is **slow** (minutes per calendar; run it in the background), and its
  `whose start date …` query **returns one-off events only. Repeating events are missed**: weekly
  meetings, one-on-ones and classes all vanish.
- Recover them by dumping the repeating series and expanding the rules:

  ```applescript
  -- per calendar; wrap each event in try: `recurrence` is missing value on most and errors
  set evs to every event of calendar cn whose start date > (date "Monday, January 1, 2024 at 00:00:00")
  repeat with e in evs
      try
          set r to recurrence of e
          if r is not missing value and r is not "" then ¬
              set out to out & cn & "|" & (start date of e as «class isot» as string) & "|" & ¬
              (end date of e as «class isot» as string) & "|" & r & "|" & (summary of e) & linefeed
      end try
  end repeat
  ```
  then `$PY $H/expand_recurring.py dump.txt <YYYY-MM-DD from> <YYYY-MM-DD to, exclusive>`.
- **Scan every calendar that holds work commitments.** List them with
  `osascript -e 'tell application "Calendar" to get name of every calendar'`, and ask, or take the
  list from the addendum. A teaching or project calendar missed in the scan is a missed class.
- EventKit through `swift` often has no calendar permission from a terminal (it prints NO
  ACCESS). If it does not work at once, do not retry it.
- Also read the person's email for meetings **not yet on the calendar**: one just confirmed, or a
  recurring meeting announced by email.

### 3. Build the plan and show it

- **Working window:** the hours the person keeps for meetings, from them or the addendum. Ignore
  overnight slots.
- **Public holidays: leave empty.** Check a holiday calendar in Calendar.app; never guess holiday
  dates from memory. All-day personal items (a visitor, an appointment) are not blockers, but are
  worth a mention.
- **Tentative holds count as busy.** Say which ones, so the person can release them.
- **when2meet slots are 15 minutes.** Round an end of 10:50 up to 11:00.
- Write the plan as `blocks.json`, for example
  `{"2026-09-28": [["07:00","09:30"],["12:00","13:00"]]}`. Show it to the person as a day-by-day
  table, and wait for their go-ahead.

### 4. Mark the poll (live: it saves immediately)

Two prerequisites, both the person's to do:
- They are **signed in** in the Chrome tab. `$PY $H/when2meet.py probe "<url>"` shows their user
  id and 0 marked slots.
- Chrome: **View > Developer > Allow JavaScript from Apple Events**. The error when it is off:
  *"Executing JavaScript through AppleScript is turned off."* Changing a browser security setting
  is the person's call, so ask and do not script it.

```bash
$PY $H/when2meet.py fill "<url>" blocks.json
```

How it works, because both obvious approaches fail:
- AppleScript's `execute javascript` runs in an **isolated world**: page globals such as `UserID`,
  `TimeOfSlot` and `AvailableAtSlot` read as undefined. The helper injects a `<script>` element so
  the code runs in the page, and reads the result back from a `data-` attribute on `<body>`.
- It then drives the page's **own** selection code: one rectangle per block (`FromCol/ToCol/FromRow/
  ToRow`, `ChangeToAvailable=true`, `SelectStop()`), so the site builds and posts the availability
  itself. No hand-built requests to the site's save endpoint.

### 5. Verify against the server

```bash
$PY $H/when2meet.py verify "<url>" blocks.json "<their name in the poll>"
```

This reloads the poll fresh and compares the saved slots for their name with the plan: `match
True`, nothing extra, nothing missing. The count the page reports is not proof; the server's copy
is.

### 6. Report

Say plainly that it is **live and visible to the others**, give the table, tell them a click
toggles a slot (each click saves), and remind them they can switch the Chrome Apple Events setting
back off.

## Other poll sites

Doodle, Microsoft FindTime and Google polls differ. Some have a submit button, and there "leave it
for review" can be done: fill it in and do not press submit. Steps 2, 3 and 5 carry over unchanged,
and step 4 needs the site's own interface. Check for a submit step before assuming either way.

## This setup's own rules

If this setup has an addendum for this skill, read it now: the file `calendar-poll.md` in the folder
`addenda` names in `~/.config/session-dashboard/where.json`, or, without that file, in
`~/.config/office-skills/addenda/`. Where it differs from the text above, it wins.
