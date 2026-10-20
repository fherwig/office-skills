---
name: office-setup
description: Install, set up, check or remove the office-skills (email-read, email-compose, email-sweep, email-archive, calendar, calendar-poll) for a person. It links the skills they choose, asks only what it cannot find out itself, writes their settings and starter add-ons, gets macOS's permission prompts out of the way, and tests each skill without changing anything. Run by whoever looks after the person's sessions, which in a session dashboard is the steward. Use for "install office-skills", "set up office-skills", "set up the office skills", "check office-skills", "remove office-skills".
---

# office-setup: install the office skills for a person

The person says one sentence to whoever looks after their sessions: "install office-skills".

- **If the person's setup has an agent that looks after their sessions,** a steward or a hub,
  that agent runs this skill. If the setup offers office-skills as one of its own optional
  pieces, install them through it, so that the setup's own checks know what was linked and can
  remove exactly that. Then continue at step 4 below: the setup links, and this skill sets up.
- **Otherwise any agent session can run it.** The person gives it the repository's address.

## Rules for the whole setup

- **One step at a time, each after the person's yes.** Say what the step will do before doing it.
- **Write only in two places:** links in the agent's skills folder, and files in
  `~/.config/office-skills/`. Change nothing in Mail, Calendar, Thunderbird or the browser.
- **Send nothing, and look up no addresses.** The test of email-compose opens a draft only if the
  person agrees, and leaves its recipients empty.
- **Read as little mail as possible.** The tests count messages and show one subject line. They
  open no message bodies.
- **Never overwrite.** If a skill folder, link or settings file of the same name already exists,
  stop and ask.

## Step 1: check the machine

These checks prompt nothing:

```bash
sw_vers -productVersion                      # macOS
ls -d /System/Applications/Mail.app /System/Applications/Calendar.app
python3 --version                            # 3.9 or newer, for email-archive and calendar-poll
sqlite3 --version                            # 3.43 or newer, for the email-archive search index
ls -d /Applications/Thunderbird.app          # only for email-archive
ls -d "/Applications/Google Chrome.app"      # only for calendar-poll
```

If something is missing, name it and offer to leave out the skills that need it. On a computer
that is not a Mac, say that these skills drive Mac apps and stop. email-compose's own text says
what to do there: write the draft to a file for the person to paste.

## Step 2: get the repository

If it is not on the computer yet, clone it to a place the person chooses, by default
`~/src/office-skills`:

```bash
git clone <the repository's address> ~/src/office-skills
```

A later `git pull` there updates every linked skill at once.

## Step 3: choose and link

Show the person the six skills and what each needs, and link only the ones they choose:

| Skill | Needs |
|---|---|
| email-read | Mail |
| email-compose | Mail |
| email-sweep | Mail, and a todo list to file into |
| email-archive | Thunderbird, a separate archive profile, and old mail exported to mbox |
| calendar | Calendar |
| calendar-poll | Calendar and Chrome |

Link each chosen folder into the agent's skills folder: for Claude Code that is `~/.claude/skills/`,
or the `skills` folder of the configuration directory the person uses. Link, never copy:

```bash
ln -s ~/src/office-skills/skills/<skill> ~/.claude/skills/<skill>
```

email-archive also needs its command on the PATH:
`ln -s ~/src/office-skills/skills/email-archive/email_archive.py ~/.local/bin/email-archive`.

## Step 4: get macOS's permission prompts out of the way

The first time an agent drives Mail or Calendar, macOS asks whether the terminal may control the
app. Trigger the prompts now, with reads that change nothing, and tell the person to answer
**Allow**:

```bash
osascript -e 'tell application "Mail" to count of accounts'
osascript -e 'tell application "Calendar" to count of calendars'
```

If one was refused earlier, it is switched on again in System Settings, Privacy & Security,
Automation, under the terminal app.

## Step 5: ask only what cannot be found

Find first, then ask, and offer what you found as the default.

- **Where things are.** If the optional file `~/.config/session-dashboard/where.json` exists, it already names the
  todo list (`todo`), the register of work (`register`), a capture file (`inbox`), the hub
  (`hub`) and the add-ons folder (`addenda`). Use those and do not ask about them.
- **email-read and email-compose:** which account is the person's main one. List them with
  `osascript -e 'tell application "Mail" to return name of every account'`. For drafts, the
  sender address: offer the main account's address as Mail shows it, and look up no one else's.
  Also ask whether the person keeps a writing style guide that drafts should follow, and where.
- **email-sweep:** which account and inbox to sweep. If there is no `where.json`, also ask where
  the todo list is (offer to create one, for example `~/office/todo.md`), and optionally a notes
  file and a file listing projects. Senders that are never actionable can be added later.
- **email-archive:** whether there is an archive, which Thunderbird profile holds it, and which
  folder the exported mailboxes are in.
- **calendar:** which calendar new events go to, from
  `osascript -e 'tell application "Calendar" to return name of every calendar'`. Also ask whether
  a holiday calendar is subscribed, since calendar-poll uses it.
- **calendar-poll:** the time zone is this computer's. Ask only if the person travels with the
  laptop and wants a fixed home zone.

## Step 6: write the settings and the starter add-ons

Show each file before writing it.

- **The archive command.** Whenever email-archive is linked and `email-archive` is not on the PATH,
  link it: `ln -s <the email-archive skill folder>/email_archive.py ~/.local/bin/email-archive`. A
  setup that linked the skills itself skipped step 3, where this link is otherwise made.
- **Settings,** only for the skills that read them:
  - `~/.config/office-skills/email-sweep.json`, with the keys listed in email-sweep's own text:
    `todo`, `register`, `notes`, `inbox`, `account`, `inbox_mailbox`, and others as needed;
  - `~/.config/office-skills/email-archive.json`, with `profile` and optionally `volume_hint`. Then
    run `email-archive point <archive folder>` with Thunderbird closed;
  - `~/.config/office-skills/calendar-poll.json`, with `tz`, only if a home zone was asked for.
- **A starter add-on for each chosen skill,** in the add-ons folder: the one `where.json` names, or
  `~/.config/office-skills/addenda/`. File name `<skill>.md`. It holds the person's answers as plain
  sentences, so the skill reads them as this setup's own rules. Examples: "The main account is
  Work." "New events go to the calendar Home, with an alert 15 minutes before." "Drafts follow
  the style guide in ~/Documents/style.md." Leave room under a heading "My own rules" for
  corrections the person adds later.

## Step 7: test each chosen skill, read-only

- **email-read:** count the main inbox's messages from the last day, and show the subject of the
  newest one.
- **email-compose:** only with the person's yes, open one draft with the subject "office-skills
  test", no recipient and a one-line body. They close it without sending.
- **email-sweep:** run it over the last day, approve nothing so that nothing is filed, and keep
  its watermark where it was.
- **email-archive:** `email-archive where`, and with the person's yes `email-archive open`.
- **calendar:** list today's events.
- **calendar-poll:** check that Chrome runs and that the scripts parse
  (`python3 -m py_compile` on each script). No poll is touched.

Report each result in one line. A failure gets its likely cause and the step to repeat.

## Step 8: finish

Tell the person what they can now say, one line per skill. Examples: "find the mail from the
department about the budget", "draft a reply to that", "sweep my email", "search the mail archive
for the 2023 contract", "add lunch with Sam on Friday at noon", "fill in the when2meet in my
browser". Then say where the answers are kept (`~/.config/office-skills/` and the add-ons), and
that "check office-skills" or "remove office-skills" runs this skill again.

## Check

Run steps 1, 4 and 7 again without changing anything, and report what works and what does not.

## Remove

With the person's yes:
- remove the links this setup made, and only links that point into the office-skills repository;
- remove the `email-archive` link from `~/.local/bin`;
- ask before removing `~/.config/office-skills/`, because it holds the person's own add-ons;
- if the setup installed them as its own optional pieces, remove them the same way. That removes
  the links only, so say that the settings and add-ons stay unless the person asks to remove them.

Leave Mail, Calendar, Thunderbird and the repository itself as they are, and say that macOS's
Automation permission can be switched off in System Settings.

## This setup's own rules

If this setup has an addendum for this skill, read it now: the file `office-setup.md` in the folder
`addenda` names in `~/.config/session-dashboard/where.json`, or, without that file, in
`~/.config/office-skills/addenda/`. Where it differs from the text above, it wins.
