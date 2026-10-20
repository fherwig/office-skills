---
name: email-compose
description: Open a new email compose window in the macOS Mail app with the subject and body pre-filled and the recipient fields left empty, for the person to address and send themselves. Use when the person asks to write or draft an email. This skill never sends.
---

# Compose an email in the macOS Mail app

**Read this file to the end before running anything.** The two rules broken most often, the empty
recipient fields and the AppleScript quoting trap, sit below the first example, and acting on a
partial read is how this skill gets used wrong.

**For macOS Mail.app via AppleScript, for now.** Without a Mac, write the draft to a file instead
(a subject line, a blank line, then the body, in the same plain text as below) and tell the person
where it is, so they paste it into their own mail program.

## What it does, and what it never does

It opens a Mail compose window with the subject and body filled in. The person addresses it,
reviews it and sends it.

**This skill never sends email, and neither does anything else.** Do not call Mail's `send`, and do
not reach for `mail`, `sendmail`, SMTP or any other way of sending. "Send it" from the person means
"get it ready for me to send". A sent message cannot be recalled, and it goes out under their name,
so the send stays theirs. Where the setup has a guard that refuses send commands, it exists because
the rule is absolute.

## Recipients: always leave To and CC empty

**Never put an address in the message.** Do not search Contacts, do not look through mail history,
do not read it off a file, do not guess, and do not ask for it. The person fills in the recipients
themselves, in the compose window.

This holds even when the address is obvious, even when you saw it earlier in the session, and even
when the request names the person: **"email Alex about X" is an instruction to write the message,
not to find Alex's address.** There is no exception and no "if available" case. A compose window
with an empty To field is the finished product.

## Method: an AppleScript heredoc with plain text

**Always use a heredoc** (`osascript <<'APPLESCRIPT'`) and **plain-text `content`**, never
`html content`, which is unreliable and may produce an empty body. Mail turns plain-text URLs into
links by itself.

```bash
osascript <<'APPLESCRIPT'
tell application "Mail"
    activate
    set bodyText to "Dear colleagues,

This is the email body. Plain text with blank lines for paragraphs.

A URL like https://example.com will be auto-linked by Mail.

Best,
Alex"
    set newMessage to make new outgoing message with properties {subject:"Subject here", content:bodyText, sender:"you@example.org"}
    set visible of newMessage to true
end tell
APPLESCRIPT
```

`sender` is the person's own address for the account the mail should go from. That is their
choice, never a recipient's.

## The quoting trap

The body is an AppleScript string delimited by `"`, so **a straight double quote inside the body
ends the string and the script dies** with `syntax error: A identifier can't go after this """`.
Escape every one as `\"`:

```applescript
set bodyText to "He wrote \"almost due\" in the reminder."
```

Apostrophes are safe, and so is everything else, because the heredoc is quoted (`<<'APPLESCRIPT'`).
This bites precisely when following the plain-text rule below, which replaces curly quotes with
straight ones.

## Body text: strictly plain ASCII

These rules govern the **email body**, not this file and not what you write in chat.

- **No markdown.** No `**bold**`, no `#` headers, no `---` rules, no `|` tables, no `-` bullet
  lists.
- **No Unicode.** Basic ASCII only, because some mail clients mangle the rest. No em dashes (write
  `--`), no curly quotes (write `"` and `'`, then escape the double quotes as above), no ellipsis
  character (write `...`).
- **No HTML.** Never the `html content` property.
- **No leading whitespace.** Some clients read an indented line as quoted text, so keep every line
  flush left.
- **Emphasis in CAPS.** Asterisks around a word arrive as literal asterisks, so use them rarely if
  at all, and never expect them to become italics.

If this setup keeps a writing style guide or a list of corrections to apply to drafted text, apply
it before opening the window.

## Lists

Write the items as plain lines, one per line, under a bracketed marker naming the list type:

```
[bullet list]
First item
Second item
Third item

[numbered list]
First item
Second item
Third item
```

The marker is scaffolding for the person, not part of the message. They select the lines beneath
it, apply Mail's own list formatting, and delete the marker line. Do not type the bullets or
numbers yourself: typed `-` and `1.` are exactly the markdown this skill forbids, and they survive
into the sent message as plain text.

## Mechanics checklist

- Always an `osascript <<'APPLESCRIPT'` heredoc, never inline `-e` strings, which break on
  multi-line bodies.
- Always plain-text `content`, never `html content`.
- Always set `sender` explicitly; do not rely on Mail's default account.
- Always `set visible of newMessage to true`, so the window actually appears.
- Never the `mailto:` URL scheme (`open "mailto:..."`), which is unreliable on macOS.

## After the window is open, it is theirs

Mail does not reliably expose an open compose window as a scriptable `outgoing message`, so you
cannot go back and edit or clear a field once it is on screen. If a draft turns out to be wrong,
say so and offer to open a corrected replacement. Do not try to script a fix to the window they
are looking at.

## This setup's own rules

If this setup has an addendum for this skill, read it now: the file `email-compose.md` in the folder
`addenda` names in `~/.config/session-dashboard/where.json`. Where it differs from the text above,
it wins.
