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
| **office-setup** | Installs, sets up, checks or removes the skills above for you: links the ones you choose, asks the few questions, writes your settings, and tests each skill without changing anything |

## What these skills will not do

- **Send mail.** Every message is left for you to send. "Send it" means "get it ready".
- **Look up addresses.** The recipient fields stay empty, and you fill them in.
- **Act before you agree.** Filing, moving mail, marking a poll and creating events are each
  shown to you first.

## Install

**Say one sentence** to whoever looks after your agent sessions: "install office-skills from
<this repository's address>".

- **If your setup has an agent that looks after your sessions,** a steward or a hub, ask it. If
  your setup offers office-skills as one of its optional pieces, it installs them that way, so its
  own checks see them and can remove them exactly.
- **Otherwise,** any agent session will do.

Either way the agent follows the **office-setup** skill in this repository:
1. It checks the computer.
2. It links only the skills you choose.
3. It gets macOS's permission prompts out of the way, so you can answer Allow.
4. It asks only what it cannot find out: your main mail account, your default calendar, where
   your todo list is, whether you have a mail archive.
5. It writes your settings to `~/.config/office-skills/`, and tests each skill without sending or
   changing anything.

"remove office-skills" undoes it.

**By hand,** if you prefer:
1. Clone this repository.
2. Link each skill folder you want into your agent's skills folder, for Claude Code
   `~/.claude/skills/`, for example
   `ln -s "$(pwd)/skills/email-read" ~/.claude/skills/email-read`. Link rather than copy, so
   `git pull` updates them.
3. The first time a skill drives Mail or Calendar, macOS asks whether your terminal may control
   that app. Allow it, or later in System Settings, Privacy & Security, Automation.
4. Each skill's own text says what it needs set up once.

## Your own rules: addenda

Each skill ends by reading an optional addendum: a file named after the skill, holding your own
rules where they differ from the shared text, in `~/.config/office-skills/addenda/`. office-setup writes a starter one for each skill you choose. Examples are your accounts, mailbox names, default
calendar, or a style guide for drafts. The shared text stays the same for everyone, and your
specifics stay with you. If the optional file `~/.config/session-dashboard/where.json` exists and
names `addenda`, that folder is used instead.

## Licence

MIT. See `LICENSE`.
