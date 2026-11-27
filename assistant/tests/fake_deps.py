"""A Deps made of stand-ins, for tests: a calendar served from memory and a fake IMAP server.

Since episode 2b the tools get what they need from `ctx.deps`, so a test hands in a Deps of its own
instead of swapping functions inside bot.py.
"""

from __future__ import annotations

import dataclasses
from datetime import tzinfo
from zoneinfo import ZoneInfo

import httpx
from fake_imap import FOLDER, OWNER, PASSWORD, FakeIMAP
from pydantic_ai import RunContext
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage

import bot

CALENDAR_URL = 'https://calendar.fake/private-key/basic.ics'
NO_EVENTS = b'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//always-on-assistant//test//EN\r\nEND:VCALENDAR\r\n'
OWNER_TZ = ZoneInfo('America/Los_Angeles')


def make_deps(calendar: bytes = NO_EVENTS, imap: FakeIMAP | None = None, tz: tzinfo = OWNER_TZ) -> bot.Deps:
    """The calendar is only served at CALENDAR_URL. `tz` is used once Deps has a `tz` field (2b, part 2)."""

    def serve(request: httpx.Request) -> httpx.Response:
        if str(request.url) != CALENDAR_URL:
            return httpx.Response(404)
        return httpx.Response(200, content=calendar)

    http = httpx.AsyncClient(transport=httpx.MockTransport(serve))
    mailbox = bot.Mailbox('imap.fake', OWNER, PASSWORD, FOLDER, connect=(imap or FakeIMAP([])).connect)
    extra = {'tz': tz} if 'tz' in {f.name for f in dataclasses.fields(bot.Deps)} else {}
    return bot.Deps(http=http, calendar_url=CALENDAR_URL, mailbox=mailbox, **extra)


def context(deps: bot.Deps) -> RunContext[bot.Deps]:
    """What a run hands a tool, for calling the tool directly in a test."""
    return RunContext(deps=deps, model=TestModel(), usage=RunUsage())
