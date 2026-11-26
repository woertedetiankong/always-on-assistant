"""Lesson 2a: the assistant reads your calendar through its first tool."""

import asyncio
import os
from datetime import date, datetime, time, timedelta
from typing import Annotated, Any, Literal

import httpx
import icalendar
import recurring_ical_events
from pydantic import BaseModel, StringConstraints, field_validator
from pydantic_ai import Agent


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


agent = Agent(
    'google:gemini-3.8-flash',
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


async def fetch_calendar() -> bytes:
    """Download the calendar file from its secret iCal address."""
    async with httpx.AsyncClient(timeout=20) as http:
        response = await http.get(os.environ['CALENDAR_ICS_URL'])
        response.raise_for_status()
        return response.content


@agent.tool_plain
async def list_events(start: date, end: date) -> list[Event]:
    """List the events on the owner's calendar from start to end, both days included.

    Args:
        start: The first day.
        end: The last day.
    """
    calendar = icalendar.Calendar.from_ical(await fetch_calendar())
    since = datetime.combine(start, time.min).astimezone()
    until = datetime.combine(end + timedelta(days=1), time.min).astimezone()
    events = [
        Event(title=str(found.get('SUMMARY', '')), start=to_local(found.start), end=to_local(found.end))
        for found in recurring_ical_events.of(calendar).between(since, until)
    ]
    return sorted(events, key=lambda event: (isinstance(event.start, datetime), event.start))


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


async def poll_once(telegram: httpx.AsyncClient, offset: int) -> int:
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
            result = await agent.run(message.text)
            text = result.output.text
        except Exception as error:
            # Only the type: an error's text can hold a request address, and so a token.
            print(f'run failed: {type(error).__name__}')
            text = 'Sorry, that one failed. Please send it again.'
        await call(telegram, 'sendMessage', chat_id=message.chat.id, text=text)
    return offset


async def main() -> None:
    url = f'https://api.telegram.org/bot{os.environ["TELEGRAM_BOT_TOKEN"]}/'
    async with httpx.AsyncClient(base_url=url, timeout=40) as telegram:
        offset = 0
        while True:
            offset = await poll_once(telegram, offset)


if __name__ == '__main__':
    asyncio.run(main())
