"""Put five demo emails into your demo folder (a Gmail label), so episode 2b's questions have answers.

Usage, from the assistant folder:
    uv run python seed_demo_mail.py --dry-run   # show what would be added, change nothing
    uv run python seed_demo_mail.py

Needs IMAP_HOST, IMAP_USER, IMAP_PASSWORD and IMAP_FOLDER, as for the bot (the handout of 2b says how).
The senders are made up and use .example addresses, which can never belong to anyone. The emails
are dated over the last three weeks; the dentist's reminder is left unread.

This is a setup script, not part of the bot: it adds to the folder with IMAP APPEND, and the bot
itself only ever opens the folder read-only. It adds nothing if the folder already holds emails
(you can take the label off them in Gmail), unless you pass --anyway. It never deletes anything.
"""

from __future__ import annotations

import email.policy
import email.utils
import imaplib
import os
import sys
from datetime import datetime, time, timedelta
from email.message import EmailMessage

DENTIST = 'Bright Smile Dental <hello@brightsmile.example>'


def demo_emails(today: datetime) -> list[tuple[datetime, str, str, str, bool]]:
    """(received, sender, subject, text, read) for each demo email, dated back from `today`."""
    friday = today.date() + timedelta(days=(4 - today.weekday()) % 7 or 7)  # the next Friday
    when = f'Friday {friday.day} {friday:%B} at 3:00 pm'
    at = lambda days_ago, hour, minute: datetime.combine(today.date() - timedelta(days=days_ago), time(hour, minute), today.tzinfo)  # noqa: E731
    return [
        (at(21, 10, 4), DENTIST, 'Your appointment is booked',
         f'Hi, this is Bright Smile Dental. Your cleaning is booked for {when}.\n\nSee you then!', True),
        (at(6, 16, 20), 'Priya Shah <priya@example.com>', 'Notes from the weekly sync',
         'Three things from today:\n- the launch moves to January\n- Sam owns the new onboarding\n- next sync is on Friday\n\nPriya', True),
        (at(3, 8, 30), 'Northwind Shop <orders@northwind.example>', 'Your order has shipped',
         'Good news: your desk lamp is on its way. It should arrive on Monday.\n\nNorthwind Shop', True),
        (at(2, 11, 45), 'Alex Rivera <alex@example.com>', 'Lunch Friday?',
         'Still on for 12:30 on Friday? I booked the usual place.\n\nAlex', True),
        (at(1, 9, 12), DENTIST, 'Reminder: your dental cleaning on Friday',
         f"Hi, this is Bright Smile Dental, your dentist's office. A reminder of your cleaning on {when}.\n\n"
         'Reply to this email to reschedule.', False),
    ]


def build(owner: str, received: datetime, sender: str, subject: str, text: str, n: int) -> bytes:
    message = EmailMessage()
    message['From'] = sender
    message['To'] = owner
    message['Subject'] = subject
    message['Date'] = email.utils.format_datetime(received)
    message['Message-ID'] = f'<demo-{n}-{received:%Y%m%d}@always-on-assistant.example>'
    message.set_content(text)
    return message.as_bytes(policy=email.policy.SMTP)


def main() -> None:
    dry_run, anyway = '--dry-run' in sys.argv, '--anyway' in sys.argv
    host, user, folder = os.environ['IMAP_HOST'], os.environ['IMAP_USER'], os.environ['IMAP_FOLDER']
    emails = demo_emails(datetime.now().astimezone())
    with imaplib.IMAP4_SSL(host, timeout=20) as imap:
        try:
            imap.login(user, os.environ['IMAP_PASSWORD'])
        except imaplib.IMAP4.error:
            raise SystemExit('Login failed: check IMAP_USER and IMAP_PASSWORD (for Gmail, an app password).') from None
        status, data = imap.select(f'"{folder}"', readonly=True)
        if status != 'OK':
            raise SystemExit(f'There is no folder named {folder!r}. In Gmail, make a label with that name first.')
        held = int(data[0])
        if held and not anyway:
            note = f'{folder!r} already holds {held} emails. Take the label off them in Gmail, or run again with --anyway.'
            if not dry_run:
                raise SystemExit(note + ' Nothing was added.')
            print(note)
        for n, (received, sender, subject, text, read) in enumerate(emails, start=1):
            print(f'{"would add" if dry_run else "adding"}: {received:%a %d %b %H:%M}  {sender:48}  {subject}{"" if read else "  (unread)"}')
            if not dry_run:
                status, _ = imap.append(f'"{folder}"', '(\\Seen)' if read else None,
                                        imaplib.Time2Internaldate(received), build(user, received, sender, subject, text, n))
                if status != 'OK':
                    raise SystemExit(f'The server refused email {n}; the ones before it were added.')
    print('Nothing changed (--dry-run).' if dry_run else f'Done: {len(emails)} demo emails in {folder!r}.')


if __name__ == '__main__':
    main()
