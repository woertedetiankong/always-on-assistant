"""A stand-in for an IMAP server such as Gmail's, for tests: no password, no network.

It answers the few commands the bot sends the way Gmail answered them when the course recorded
episode 2b (the same shapes `imaplib` hands back), and it keeps the rules the bot depends on:

- a folder opened with EXAMINE (`select(..., readonly=True)`) cannot change;
- in a folder opened read-write, fetching BODY[...] or RFC822 marks the email read (\\Seen);
  BODY.PEEK[...] never does.
"""

from __future__ import annotations

import email.policy
import email.utils
import imaplib
import re
from dataclasses import dataclass, field
from datetime import datetime
from email.message import EmailMessage

OWNER = 'you@example.com'
PASSWORD = 'abcdabcdabcdabcd'
FOLDER = 'assistant-demo'


@dataclass
class FakeEmail:
    uid: int
    sender: str
    subject: str
    received: datetime  # with a time zone
    text: str
    html: str | None = None  # also sent as HTML: the email becomes multipart/alternative
    seen: bool = False

    def raw(self) -> bytes:
        message = EmailMessage()
        message['From'] = self.sender
        message['To'] = OWNER
        message['Subject'] = self.subject
        message['Date'] = email.utils.format_datetime(self.received)
        message['Message-ID'] = f'<{self.uid}@fake.imap>'
        message.set_content(self.text)
        if self.html is not None:
            message.add_alternative(self.html, subtype='html')
        return message.as_bytes(policy=email.policy.SMTP)


@dataclass
class FakeIMAP:
    """The server. `connect` is what the bot's Mailbox calls in place of imaplib.IMAP4_SSL."""

    emails: list[FakeEmail]
    folder: str = FOLDER
    log: list[str] = field(default_factory=list)  # every command, in order, without the password

    def connect(self, host: str, port: int = 993, timeout: float | None = None) -> Connection:
        self.log.append(f'CONNECT {host}')
        return Connection(self)

    def unread(self, uid: int) -> bool:
        return not next(e for e in self.emails if e.uid == uid).seen

    def opened_read_write(self) -> bool:
        return any(line.startswith('SELECT') for line in self.log)


class Connection:
    """One logged-in session, with the parts of imaplib.IMAP4 the bot uses."""

    def __init__(self, server: FakeIMAP) -> None:
        self.server = server
        self.state = 'NONAUTH'
        self.readonly = True
        self.literal: bytes | None = None  # like imaplib: sent after the next command

    def __enter__(self) -> Connection:
        return self

    def __exit__(self, *exc: object) -> None:
        if self.state != 'LOGOUT':
            self.logout()

    def login(self, user: str, password: str) -> tuple[str, list[bytes]]:
        self.server.log.append(f'LOGIN {user}')
        if (user, password) != (OWNER, PASSWORD):
            raise imaplib.IMAP4.error(b'[AUTHENTICATIONFAILED] Invalid credentials (Failure)')
        self.state = 'AUTH'
        return 'OK', [f'{user} authenticated (Success)'.encode()]

    def select(self, mailbox: str = 'INBOX', readonly: bool = False) -> tuple[str, list[bytes]]:
        self._need('AUTH', 'SELECTED')
        self.server.log.append(f'{"EXAMINE" if readonly else "SELECT"} {mailbox}')
        if mailbox.strip('"') != self.server.folder:
            self.state = 'AUTH'
            return 'NO', [b'[NONEXISTENT] Unknown Mailbox: ' + mailbox.encode() + b' (Failure)']
        self.state, self.readonly = 'SELECTED', readonly
        return 'OK', [str(len(self.server.emails)).encode()]

    def uid(self, command: str, *args: str | bytes) -> tuple[str, list]:
        self._need('SELECTED')
        words = [a.decode() if isinstance(a, bytes) else a for a in args if a is not None]
        literal, self.literal = self.literal, None
        self.server.log.append(f'UID {command.upper()} {" ".join(words)}' + (' {literal}' if literal is not None else ''))
        if command.upper() == 'SEARCH':
            return self._search(words, literal)
        if command.upper() == 'FETCH':
            return self._fetch(words[0], ' '.join(words[1:]))
        raise imaplib.IMAP4.error(f'UID command error: BAD [b"Unknown command {command}"]')

    def logout(self) -> tuple[str, list[bytes]]:
        self.server.log.append('LOGOUT')
        self.state = 'LOGOUT'
        return 'BYE', [b'LOGOUT Requested']

    # ---- inside the server ----

    def _need(self, *states: str) -> None:
        if self.state not in states:
            raise imaplib.IMAP4.error(f'command illegal in state {self.state}, only allowed in states {", ".join(states)}')

    def _search(self, words: list[str], literal: bytes | None) -> tuple[str, list[bytes]]:
        if literal is not None:
            if not literal:  # what Gmail answered to TEXT {0} (episode 2b, data/gmail_quirks.json)
                return 'NO', [b'[SERVERBUG] infeasible query (Failure)']
            words.append(literal.decode())
        found = list(self.server.emails)
        i = 0
        while i < len(words):
            key = words[i].upper()
            value = words[i + 1].strip('"') if i + 1 < len(words) else None
            if key == 'CHARSET':
                i += 2
                continue
            if key == 'ALL':
                i += 1
                continue
            if key in ('UNSEEN', 'SEEN'):
                found = [e for e in found if e.seen == (key == 'SEEN')]
                i += 1
                continue
            if value is None:
                raise imaplib.IMAP4.error("UID command error: BAD [b'Could not parse command']")
            if key in ('SINCE', 'BEFORE', 'ON'):
                day = datetime.strptime(value, '%d-%b-%Y').date()
                keep = {'SINCE': lambda d: d >= day, 'BEFORE': lambda d: d < day, 'ON': lambda d: d == day}[key]
                found = [e for e in found if keep(e.received.date())]
            elif key in ('TEXT', 'BODY', 'SUBJECT', 'FROM'):
                where = {'TEXT': lambda e: e.raw().decode(), 'BODY': lambda e: e.text, 'SUBJECT': lambda e: e.subject, 'FROM': lambda e: e.sender}[key]
                found = [e for e in found if value.lower() in where(e).lower()]
            else:
                raise imaplib.IMAP4.error(f"UID command error: BAD [b'Unknown search key {key}']")
            i += 2
        return 'OK', [' '.join(str(e.uid) for e in sorted(found, key=lambda e: e.uid)).encode()]

    def _fetch(self, uid_set: str, items: str) -> tuple[str, list]:
        wanted = re.findall(r'BODY(?:\.PEEK)?\[[^\]]*\](?:<\d+\.\d+>)?|RFC822(?:\.HEADER|\.TEXT|\.SIZE)?|FLAGS|UID|INTERNALDATE', items.upper())
        if not wanted:
            raise imaplib.IMAP4.error("UID command error: BAD [b'Could not parse command']")
        uids = {int(u) for u in uid_set.split(',') if u.isdigit()}
        data: list = []
        for seq, mail in enumerate(sorted(self.server.emails, key=lambda e: e.uid), start=1):
            if mail.uid not in uids:
                continue
            for item in wanted:
                reads = item.startswith('BODY[') or item in ('RFC822', 'RFC822.TEXT')
                if reads and not self.readonly:
                    mail.seen = True
            plain = [f'UID {mail.uid}']
            if 'FLAGS' in wanted:
                plain.append('FLAGS (\\Seen)' if mail.seen else 'FLAGS ()')
            if 'INTERNALDATE' in wanted:
                plain.append(f'INTERNALDATE "{mail.received:%d-%b-%Y %H:%M:%S %z}"')
            if 'RFC822.SIZE' in wanted:
                plain.append(f'RFC822.SIZE {len(mail.raw())}')
            literals = [(name, body) for item in wanted if (part := _section(mail, item)) for name, body in [part]]
            head = f'{seq} ({" ".join(plain)}'
            if not literals:
                data.append((head + ')').encode())
                continue
            for n, (name, body) in enumerate(literals):
                meta = (head + ' ' if n == 0 else ' ') + f'{name} {{{len(body)}}}'
                data.append((meta.encode(), body))
            data.append(b')')
        return 'OK', data or [None]


def _section(mail: FakeEmail, item: str) -> tuple[str, bytes] | None:
    """The name Gmail answers with and the bytes, for one BODY[...] or RFC822 item; None for the rest."""
    raw = mail.raw()
    header, _, text = raw.partition(b'\r\n\r\n')
    header += b'\r\n\r\n'
    if item in ('RFC822', 'RFC822.HEADER', 'RFC822.TEXT'):
        return item, {'RFC822': raw, 'RFC822.HEADER': header, 'RFC822.TEXT': text}[item]
    match = re.fullmatch(r'BODY(?:\.PEEK)?\[([^\]]*)\](?:<(\d+)\.(\d+)>)?', item)
    if not match:
        return None
    section, start, length = match.group(1), match.group(2), match.group(3)
    if section == '':
        body = raw
    elif section == 'HEADER':
        body = header
    elif section == 'TEXT':
        body = text
    elif section.startswith('HEADER.FIELDS'):
        names = {n.lower() for n in re.findall(r'[\w-]+', section.removeprefix('HEADER.FIELDS'))}
        fields = re.finditer(rb'^([\w-]+):.*(?:\r\n[ \t].*)*\r\n', header, flags=re.MULTILINE)  # a field and its folded lines
        body = b''.join(f.group(0) for f in fields if f.group(1).decode().lower() in names) + b'\r\n'
    elif section.isdigit():
        message = email.message_from_bytes(raw, policy=email.policy.SMTP)
        parts = list(message.iter_parts()) if message.is_multipart() else [message]
        number = int(section)
        if not 1 <= number <= len(parts):
            body = b''
        else:
            chosen = parts[number - 1]
            body = chosen.get_payload(decode=False).encode() if isinstance(chosen.get_payload(), str) else b''
    else:
        raise imaplib.IMAP4.error("UID command error: BAD [b'Could not parse command']")
    if start is not None:
        body = body[int(start) : int(start) + int(length)]
        return f'BODY[{section}]<{start}>', body
    return f'BODY[{section}]', body
