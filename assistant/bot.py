"""The assistant after episode 2b, with the solutions of the 1a, 1b and 2a assignments."""

import asyncio
import email
import email.policy
import imaplib
import os
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Annotated, Any, Literal

import httpx
import icalendar
import recurring_ical_events
from pydantic import BaseModel, StringConstraints, field_validator
from pydantic_ai import Agent, ModelRetry, RunContext


class Reply(BaseModel):
    """What the assistant does with one incoming message."""

    kind: Literal['chat', 'task', 'reminder']
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=280)]
    due: datetime | None = None

    @field_validator('due')
    @classmethod
    def due_in_future(cls, due: datetime | None) -> datetime | None:
        if due is not None and due <= datetime.now(due.tzinfo):
            raise ValueError('due must be in the future')
        return due


class Email(BaseModel):
    """One email, without its body."""

    uid: int
    sender: str
    subject: str
    received: datetime
    unread: bool


def to_email(meta: bytes, header: bytes) -> Email:
    """One FETCH answer: its UID and FLAGS, then the header lines that were asked for."""
    message = email.message_from_bytes(header, policy=email.policy.default)
    return Email(
        uid=int(re.search(rb'UID (\d+)', meta)[1]),
        sender=str(message['From']),
        subject=str(message['Subject'] or ''),
        received=message['Date'].datetime.astimezone(),
        unread=b'\\Seen' not in imaplib.ParseFlags(meta),
    )


@dataclass
class Mailbox:
    """One folder of an IMAP mailbox, such as a Gmail label. The bot only ever opens it read-only."""

    host: str
    user: str
    password: str = field(repr=False)
    folder: str
    connect: Callable[..., imaplib.IMAP4] = imaplib.IMAP4_SSL  # tests hand in a fake server

    @contextmanager
    def opened(self) -> Iterator[imaplib.IMAP4]:
        """Log in and open the folder with EXAMINE: read-only, nothing in it can change."""
        with self.connect(self.host, timeout=20) as imap:
            imap.login(self.user, self.password)
            status, _ = imap.select(f'"{self.folder}"', readonly=True)
            if status != 'OK':
                raise LookupError(f'there is no folder named {self.folder!r}')
            yield imap

    def search(self, text: str, since: date) -> list[Email]:
        """The emails from `since` on that contain `text`, newest first, at most 20."""
        criteria = ['SINCE', f'{since:%d-%b-%Y}']
        with self.opened() as imap:
            if text:  # Gmail refuses an empty TEXT ("infeasible query"): leave it out and list everything
                imap.literal = text.encode()  # sent after TEXT as raw bytes: any language, any quote marks
                criteria.append('TEXT')
            status, found = imap.uid('SEARCH', 'CHARSET', 'UTF-8', *criteria)
            if status != 'OK':  # a refusal's text is not a list of UIDs
                raise LookupError(f'the server refused the search: {found[0].decode()}')
            uids = found[0].split()[-20:]
            if not uids:
                return []
            _, data = imap.uid('FETCH', b','.join(uids), '(FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])')
        emails = [to_email(meta, header) for meta, header in (part for part in data if isinstance(part, tuple))]
        return sorted(emails, key=lambda found: found.received, reverse=True)


@dataclass
class Deps:
    """What the tools need from outside the run. main() makes it once; every run is handed it."""

    http: httpx.AsyncClient
    calendar_url: str
    mailbox: Mailbox


agent = Agent(
    'google:gemini-3.8-flash',
    deps_type=Deps,
    output_type=Reply,
    instructions='You are a personal assistant. Decide what the message is, and write a short reply.',
)


@agent.instructions
def now() -> str:
    return f'The current time is {datetime.now().astimezone():%A %Y-%m-%d %H:%M %z}.'


class Event(BaseModel):
    """One event on the calendar. An all-day event has dates instead of times."""

    title: str
    start: datetime | date
    end: datetime | date


def to_local(value: datetime | date) -> datetime | date:
    """A time moves to the owner's time zone; an all-day date stays as it is."""
    return value.astimezone() if isinstance(value, datetime) else value


async def fetch_calendar(deps: Deps) -> bytes:
    """Download the calendar file from its secret iCal address."""
    response = await deps.http.get(deps.calendar_url)
    response.raise_for_status()
    return response.content


@agent.tool
async def list_events(ctx: RunContext[Deps], start: date, end: date) -> list[Event]:
    """List the events on the owner's calendar from start to end, both days included.

    Args:
        start: The first day.
        end: The last day.
    """
    if end < start:
        raise ModelRetry('end comes before start. end is the last day, included: for one day, give the same date twice.')
    if (end - start).days >= 31:
        raise ModelRetry('That is more than 31 days. Ask for 31 days or fewer at a time.')
    calendar = icalendar.Calendar.from_ical(await fetch_calendar(ctx.deps))
    since = datetime.combine(start, time.min).astimezone()
    until = datetime.combine(end + timedelta(days=1), time.min).astimezone()
    events = [
        Event(title=str(found.get('SUMMARY', '')), start=to_local(found.start), end=to_local(found.end))
        for found in recurring_ical_events.of(calendar).between(since, until)
    ]
    return sorted(events, key=lambda event: (isinstance(event.start, datetime), event.start))


class Slot(BaseModel):
    """A stretch of free time."""

    start: datetime
    end: datetime


@agent.tool
async def find_free_time(ctx: RunContext[Deps], day: date, minutes: int) -> list[Slot]:
    """Find free time on one day, between 9:00 and 18:00 in the owner's time zone.

    Args:
        day: The day to look at.
        minutes: The shortest free time worth returning, in minutes.
    """
    opens = datetime.combine(day, time(9)).astimezone()
    closes = datetime.combine(day, time(18)).astimezone()
    long_enough = timedelta(minutes=minutes)
    free, cursor = [], opens
    for event in await list_events(ctx, day, day):
        if not isinstance(event.start, datetime):
            continue  # an all-day event, such as a birthday, does not make you busy
        if min(event.start, closes) - cursor >= long_enough:
            free.append(Slot(start=cursor, end=min(event.start, closes)))
        cursor = max(cursor, event.end)
    if closes - cursor >= long_enough:
        free.append(Slot(start=cursor, end=closes))
    return free


@agent.tool
def search_email(ctx: RunContext[Deps], text: str, since: date) -> list[Email]:
    """Search the owner's email for messages that contain some text, newest first.

    Args:
        text: Words to look for in the sender, the subject and the body. Empty lists every email.
        since: The first day to look at.
    """
    return ctx.deps.mailbox.search(text, since)


class Chat(BaseModel):
    id: int


class Message(BaseModel):
    chat: Chat
    text: str | None = None


class Update(BaseModel):
    """One thing that happened to the bot, as Telegram reports it."""

    update_id: int
    message: Message | None = None


async def call(telegram: httpx.AsyncClient, method: str, **params: Any) -> Any:
    """Make one Telegram Bot API call and return its result."""
    response = await telegram.post(method, json=params)
    response.raise_for_status()
    return response.json()['result']


OWNER_ID = int(os.environ['TELEGRAM_OWNER_ID']) if os.environ.get('TELEGRAM_OWNER_ID') else None
"""The one chat the bot answers. None answers everyone: use it once to find your own chat id."""


async def poll_once(telegram: httpx.AsyncClient, offset: int, deps: Deps) -> int:
    """Ask for the updates from `offset` on, answer each text message, return the next offset."""
    for raw in await call(telegram, 'getUpdates', offset=offset, timeout=30):
        update = Update.model_validate(raw)
        offset = update.update_id + 1
        message = update.message
        if not (message and message.text):
            continue
        if OWNER_ID is not None and message.chat.id != OWNER_ID:
            continue
        try:
            result = await agent.run(message.text, deps=deps)
            text = result.output.text
        except Exception as error:
            # Only the type: an error's text can hold a request address, and so a token.
            print(f'run failed: {type(error).__name__}')
            text = 'Sorry, that one failed. Please send it again.'
        await call(telegram, 'sendMessage', chat_id=message.chat.id, text=text)
    return offset


async def main() -> None:
    url = f'https://api.telegram.org/bot{os.environ["TELEGRAM_BOT_TOKEN"]}/'
    calendar_url = os.environ['CALENDAR_ICS_URL']
    mailbox = Mailbox(os.environ['IMAP_HOST'], os.environ['IMAP_USER'], os.environ['IMAP_PASSWORD'], os.environ['IMAP_FOLDER'])
    async with httpx.AsyncClient(base_url=url, timeout=40) as telegram, httpx.AsyncClient(timeout=20) as http:
        deps = Deps(http=http, calendar_url=calendar_url, mailbox=mailbox)
        offset = 0
        while True:
            offset = await poll_once(telegram, offset, deps)


if __name__ == '__main__':
    asyncio.run(main())
