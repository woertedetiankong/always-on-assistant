[中文](ep02b.zh.md) · [Watch the episode](https://buildautonomy.dev/courses/pydantic-ai/ep02b)

*EPISODE 2b · ASSIGNMENT*

# Read one email without marking it read, and your time zone in Deps

The bot from the video gets what its tools need through deps: an http client, the calendar address and a read-only Mailbox. search_email finds emails by their headers. You add a tool that reads one email's text, without marking it read. Then you move the owner's time zone into Deps, so the bot's idea of “tomorrow” no longer depends on the machine it runs on.

No mailbox, no password, no API key and no network are needed. Every test hands the bot a Deps made of stand-ins (tests/fake_deps.py): an http client that serves a test calendar, and a fake IMAP server (tests/fake_imap.py) that answers the way Gmail answered when the video was recorded. A stand-in model plays a script of tool calls.

## Before you start

From the course folder, run the tests once. You should see 7 pass and 9 fail: the failing ones are your assignment.

```sh
cd assistant
uv run pytest tests/test_ep02b.py
```

Read emails() at the top of tests/test_ep02b.py: four emails, the newest an unread reminder from Bright Smile Dental (uid 4). Lunch Friday? (uid 3) was sent as text and HTML. Then read the docstring of tests/fake_imap.py: it lists the rules of IMAP the tests check.

## Part 1: read_email, and leave it unread

Add a tool read_email(ctx, uid) that returns the text of one email in the folder. It is the second half of search_email: search hands the model uids, read_email reads one of them.

- Register it with @agent.tool, its first parameter ctx: RunContext[Deps]. Describe uid under Args: in the docstring.
- Give Mailbox a method read(uid) that uses self.opened(), so the folder is opened read-only, and fetches with BODY.PEEK[] (imap.uid('FETCH', str(uid), '(BODY.PEEK[])')).
- Parse it with email.message_from_bytes(raw, policy=email.policy.default) and take message.get_body(preferencelist=('plain', 'html')).get_content(): the plain text part when the email has one.
- When the folder has no email with that uid, Gmail's answer holds no message part. Raise ModelRetry, so the model can try a uid that search_email gave it.
- Predict first: if you open the folder read-write and fetch with RFC822, what happens to the reminder's unread dot? The fake server does what IMAP does.

## Part 2: the owner's time zone, in Deps

Right now the bot uses the machine's time zone (datetime.now().astimezone()). On a server, that is often UTC, and “tomorrow” would start at 4 pm for someone in Los Angeles. Give Deps a field tz: ZoneInfo (from zoneinfo import ZoneInfo) and use it everywhere the bot means the owner's time:

- now(): an @agent.instructions function can take ctx too, so tell the model the time in ctx.deps.tz.
- list_events: build the range with datetime.combine(day, time.min, tz), and give every event's times in tz. A time without a zone (a “floating” time) is read as the owner's.
- find_free_time: 9:00 to 18:00 where the owner is.
- search_email: each email's received time, written in tz.
- main(): read it from a setting, TIME_ZONE=America/Los_Angeles, with the others, before the bot starts.

The tests run the same calendar in Tokyo and in Los Angeles: a call at 23:00 UTC on 2 December is on the morning of the 3rd in one and the afternoon of the 2nd in the other. The earlier episodes' tests hand in a tz too, once Deps has the field.

## Done when

**All 16 tests pass, and the earlier episodes' tests still pass.** Then run the real bot on your own mail.

```sh
uv run pytest
uv run --env-file .env python bot.py
```

- In Gmail, make a label, for example assistant-demo (no spaces is simplest). IMAP shows each label as a folder.
- Put a few emails in it: label some of your own, or run uv run --env-file .env python seed_demo_mail.py, which adds five demo emails with made-up senders. It adds nothing if the label already holds emails.
- Turn on 2-Step Verification for the account, then make an app password at myaccount.google.com/apppasswords. Copy its 16 letters without the spaces.
- Add five lines to assistant/.env:

```sh
IMAP_HOST=imap.gmail.com
IMAP_USER=you@gmail.com
IMAP_PASSWORD=abcdabcdabcdabcd
IMAP_FOLDER=assistant-demo
TIME_ZONE=America/Los_Angeles
```

Try “Did the dentist's office email me this week?” and “What did Alex say about lunch?”

**An app password opens your whole mailbox, read and write.** The bot only ever opens the one folder, read-only, and never prints the password; still, keep it out of anything you share. Delete it at the same page when you are done, and it stops working at once. Accounts under Google's Advanced Protection cannot make app passwords; another provider's IMAP server works the same way with its own host and password.
