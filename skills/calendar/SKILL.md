---
name: calendar
description: Create, list and search events in macOS Calendar.app. Use when the person asks to add an event, block time, check the schedule, see what is on a day, or find an event by keyword.
---

# Calendar: events in Calendar.app

Works on macOS with Calendar.app, through AppleScript (`osascript`), for now. Every calendar the
person has in Calendar.app (iCloud, Exchange, Google and local ones) can be read and written this
way.

## Which calendar

List the calendars first if you do not know them:

```bash
osascript -e 'tell application "Calendar" to get name of every calendar'
```

**The default calendar** comes from this setup's addendum or from the person. If neither names
one, ask once which calendar new events go to, and use only a calendar that name list shows. A
calendar that is used only when named (a second work calendar, a family calendar, a shared one)
is never picked by default.

## Always use 24-hour time in AppleScript dates

Write `13:30:00`, never `1:30 PM`. AppleScript parses "AM" and "PM" in date strings unreliably, and
a meeting set by mistake at 3 in the morning looks fine in the script's output.

Date strings take the form `"Wednesday, March 25, 2026 at 09:00:00"`. **Check that the weekday
matches the date** before you create anything. A wrong weekday is the cheapest error to catch and
the easiest to miss.

## Create an event

```bash
osascript <<'APPLESCRIPT'
tell application "Calendar"
    set targetCal to first calendar whose name is "CALENDAR_NAME"
    set startDate to date "DAYNAME, MONTH DD, YYYY at HH:MM:00"
    set endDate to date "DAYNAME, MONTH DD, YYYY at HH:MM:00"
    tell targetCal
        set newEvent to make new event with properties {summary:"EVENT_TITLE", start date:startDate, end date:endDate}
    end tell
    tell newEvent
        make new display alarm at end of display alarms with properties {trigger interval:-15}
    end tell
    return "Event created"
end tell
APPLESCRIPT
```

- **Location:** add `location:"LOCATION"` to the properties record.
- **Notes:** add `description:"NOTES"`.
- **A link** (a video-call URL, for example): add `url:"URL"`, and repeat it in `description` so it
  shows in every client. Take meeting links from the person or from this setup's addendum. Never
  guess one, and never put a meeting password into a file that others read.

### Always add an alert

An event made through AppleScript gets **no alert of its own**. At most it inherits the account's
default alert, and many accounts have none set. Without this step the event is silent.

- Every timed event gets a display alarm, **15 minutes before**, unless the person asks for another
  lead time.
- `trigger interval` is in **minutes**, and negative means before the start: `-15`, `-60`, `-1440`
  for a day, `-4320` for three days.
- The person names a different time ("remind me an hour before"): use that. They say "no alert":
  leave the `tell newEvent` block out.
- More than one alert: one `make new display alarm` line for each.
- **All-day events: no alarm unless asked.** A 15-minute offset on an all-day event fires at 23:45
  the night before.
- Say the alert in the confirmation: "added, alert 15 minutes before".

## List the events of a day

```bash
osascript <<'APPLESCRIPT'
tell application "Calendar"
    set dayStart to date "DAYNAME, MONTH DD, YYYY at 00:00:00"
    set dayEnd to date "DAYNAME, MONTH DD, YYYY at 23:59:59"
    set out to ""
    repeat with c in every calendar
        set cName to name of c
        try
            set evts to (every event of c whose start date ≥ dayStart and start date ≤ dayEnd)
            repeat with e in evts
                set out to out & cName & " | " & (summary of e) & " | " & (start date of e as string) & " – " & (end date of e as string) & linefeed
            end repeat
        end try
    end repeat
    return out
end tell
APPLESCRIPT
```

**This misses repeating events.** A `whose start date …` query returns one-off events only, so a
weekly meeting does not appear. When the answer matters (is the person free?), expand the repeating
series as the calendar-poll skill shows, or ask the person for a screenshot of the week.

Searching every calendar is slow, sometimes minutes on a large calendar. When you know which
calendars matter, name them instead of looping over all of them. Use variable names that are not
AppleScript words: `left`, `right`, `contents` and similar fail to compile.

## Search events by keyword

```bash
osascript <<'APPLESCRIPT'
tell application "Calendar"
    set searchTerm to "KEYWORD"
    set out to ""
    repeat with c in every calendar
        set cName to name of c
        try
            set evts to (every event of c whose summary contains searchTerm)
            repeat with e in evts
                set out to out & cName & " | " & (summary of e) & " | " & (start date of e as string) & linefeed
            end repeat
        end try
    end repeat
    return out
end tell
APPLESCRIPT
```

## Delete an event

```bash
osascript <<'APPLESCRIPT'
tell application "Calendar"
    set targetCal to first calendar whose name is "CALENDAR_NAME"
    set evts to (every event of targetCal whose summary is "EVENT_TITLE")
    set n to count of evts
    repeat with e in evts
        delete e
    end repeat
    return "Deleted " & n
end tell
APPLESCRIPT
```

Delete only what the person asked to remove, match it by exact title and calendar, and report how
many events went. Zero or more than one is worth saying.

## Holidays

Before suggesting a day for an appointment, a call to an office or a deadline, check for public
holidays in this week and the next. Read them from a holiday calendar in Calendar.app (the
addendum names it, or list the calendars and ask). Never guess holiday dates from memory.

## Notes

- **Recurring events:** creating one is better done by the person in Calendar.app. The scripted
  route gets the recurrence rule wrong too easily.
- **If a command hangs,** Calendar may be waiting on a permission or sync dialog. Tell the person
  rather than retrying.
- **Report what you did:** calendar, title, day and weekday, start and end in 24-hour time, and the
  alert.

## This setup's own rules

If this setup has an addendum for this skill, read it now: the file `calendar.md` in the folder
`addenda` names in `~/.config/session-dashboard/where.json`, or, without that file, in
`~/.config/office-skills/addenda/`. Where it differs from the text above, it wins.
