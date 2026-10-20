# office-skills

Skills that let an AI coding agent (written for Claude Code) do everyday office work with the
apps on your own computer: read and file mail, draft mail for you to send, sweep the inbox for
deadlines, search an archive of old mail, and manage your calendar and scheduling polls.

**For now everything here drives macOS apps through AppleScript:** Mail, Calendar, and your
browser for polls. Versions for other systems may join later.

| Skill | What it does |
|---|---|
| **email-read** | Find messages by sender, subject or date, read them, save attachments, and file a message into a mailbox when you ask |
| **email-compose** | Open a new message in Mail with the subject and body filled in and the recipients left empty. It never sends: you address it and press Send |
| **email-sweep** | Go through the inbox since the last sweep, show you what needs action (deadlines, requests), and file each item you approve into your todo list or a project |
| **email-archive** | Open or search an archive of old mailboxes exported to mbox, in a separate Thunderbird profile |
| **calendar** | Create, list and search events, always with an alert |
| **calendar-poll** | Answer a scheduling poll (when2meet, and similar ones such as Doodle) from your free time in Calendar, after showing you the plan |

## What these skills will not do

- **Send mail.** Every message is left for you to send. "Send it" means "get it ready".
- **Look up addresses.** The recipient fields stay empty, and you fill them in.
- **Act before you agree.** Filing, moving mail, marking a poll and creating events are each
  shown to you first.

## Install

1. Clone this repository.
2. Link each skill folder into the place your agent looks for skills. For Claude Code that is
   `~/.claude/skills/`:
   ```bash
   for s in email-read email-compose email-sweep email-archive calendar calendar-poll; do
     ln -s "$(pwd)/skills/$s" ~/.claude/skills/$s
   done
   ```
   Link rather than copy, so `git pull` updates them.
3. The first time a skill drives Mail or Calendar, macOS asks whether your terminal may control
   that app. Allow it in System Settings, Privacy & Security, Automation.

## Setup, per skill

- **email-sweep** files into places you name: your todo list, your project files, a notes file.
  It reads them from `~/.config/office-skills/email-sweep.json`; the skill lists the keys. If you
  use the session dashboard, it reads them from the dashboard's `where.json` instead.
- **email-archive** needs the archive's location and the Thunderbird profile to use, in
  `~/.config/office-skills/email-archive.json`; the skill lists the keys. Exporting mailboxes from
  Mail needs Full Disk Access for your terminal. Searching the archive needs none.
- **calendar** and **calendar-poll** find your calendars by asking Calendar. Tell your agent which
  calendar to use by default, or put it in your own addendum (below).

## Your own rules: addenda

Each skill ends by reading an optional addendum: a file named after the skill, holding your own
rules where they differ from the shared text. Examples are your accounts, mailbox names, default
calendar, or a style guide for drafts. The shared text stays the same for everyone, and your
specifics stay with you. If you use the session dashboard, its `where.json` names the folder,
under `addenda`.

## Licence

MIT. See `LICENSE`.
