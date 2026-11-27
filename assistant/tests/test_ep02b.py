"""Assignment for episode 2b: read one email without marking it read, and the owner's time zone in Deps.

Run from the assistant folder:   uv run pytest tests/test_ep02b.py

No mailbox, no password, no API key and no network are needed: every test hands the bot a Deps made
of stand-ins (fake_deps.py), with a fake IMAP server holding the four emails below (fake_imap.py),
and a stand-in model plays a script of tool calls. The first seven tests pass as soon as you have
the code from the video. Parts 1 and 2 fail until you change bot.py.
"""

import asyncio
import dataclasses
import json
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fake_deps import CALENDAR_URL, context, make_deps
from fake_imap import PASSWORD, FakeEmail, FakeIMAP
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter, ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.usage import UsageLimits

import bot

DENTIST = 'Bright Smile Dental <hello@brightsmile.example>'
THIS_WEEK = date(2026, 11, 22)


def emails() -> list[FakeEmail]:
    """A fresh copy for each test: reading may change an email's flags."""
    return [
        FakeEmail(1, DENTIST, 'Your appointment is booked', datetime(2026, 11, 2, 18, 4, tzinfo=UTC),
                  'Your cleaning is booked for Friday 27 November at 3:00 pm.', seen=True),
        FakeEmail(2, 'Northwind Shop <orders@northwind.example>', 'Your order has shipped', datetime(2026, 11, 23, 16, 30, tzinfo=UTC),
                  'Your desk lamp arrives on Monday.', seen=True),
        FakeEmail(3, 'Alex Rivera <alex@example.com>', 'Lunch Friday?', datetime(2026, 11, 24, 19, 45, tzinfo=UTC),
                  'Still on for 12:30 on Friday? Alex', html='<p>Still on for <b>12:30</b> on Friday? Alex</p>', seen=True),
        FakeEmail(4, DENTIST, 'Reminder: your dental cleaning on Friday', datetime(2026, 11, 25, 17, 12, tzinfo=UTC),
                  "Hi, this is Bright Smile Dental, your dentist's office. A reminder of your cleaning on Friday at 3:00 pm."),
    ]


FINAL = ('final', {'kind': 'chat', 'text': 'Here you go.'})


class Script:
    """A stand-in model that answers each request with the next step on its list.

    A step is one call, or a list of calls the model makes in the same answer. ('final', args) calls
    the output tool, which ends the run; any other name calls that tool."""

    def __init__(self, *steps: tuple[str, dict] | list[tuple[str, dict]]) -> None:
        self.steps = list(steps)
        self.requests: list[list[ModelMessage]] = []
        self.tools = []

    def __call__(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        self.requests.append(list(messages))
        self.tools = info.function_tools
        step = self.steps[min(len(self.requests), len(self.steps)) - 1]
        calls = step if isinstance(step, list) else [step]
        parts = [
            ToolCallPart(info.output_tools[0].name if name == 'final' else name, args, tool_call_id=f'call_{len(self.requests)}_{n}')
            for n, (name, args) in enumerate(calls)
        ]
        return ModelResponse(parts=parts)


def run(script: Script, deps: bot.Deps, prompt: str = "Did the dentist's office email me this week?", request_limit: int = 10):
    with bot.agent.override(model=FunctionModel(script)):
        return bot.agent.run_sync(prompt, deps=deps, usage_limits=UsageLimits(request_limit=request_limit))


def tool(script: Script, name: str):
    found = [t for t in script.tools if t.name == name]
    assert found, f'the model was not offered a tool named {name!r}'
    return found[0]


def returned(result, name: str) -> list[str]:
    """What each call of tool `name` handed back to the model, as the model reads it."""
    return [
        p.model_response_str()
        for m in result.all_messages()
        for p in m.parts
        if isinstance(p, ToolReturnPart) and p.tool_name == name and p.outcome == 'success'
    ]


def sent_back(script: Script) -> list[ToolReturnPart]:
    """Every tool call that went back to the model to be made again (bad arguments or a ModelRetry)."""
    return [
        p
        for m in script.requests[-1]
        if isinstance(m, ModelRequest)
        for p in m.parts
        if isinstance(p, ToolReturnPart) and p.outcome == 'retried'
    ]


# ---------- already true after the video ----------


def test_search_email_is_offered_without_its_context():
    script = Script(FINAL)
    run(script, make_deps())

    found = tool(script, 'search_email')
    properties = found.parameters_json_schema['properties']
    assert set(properties) == {'text', 'since'}, 'ctx is for your code: the model must not see it'
    assert properties['since']['format'] == 'date'
    for name, field in properties.items():
        assert field.get('description'), f'parameter {name!r} has no description'


def test_the_search_finds_this_weeks_email_from_the_dentist():
    mailbox = make_deps(imap=FakeIMAP(emails())).mailbox
    found = mailbox.search('dentist', THIS_WEEK)

    assert [e.subject for e in found] == ['Reminder: your dental cleaning on Friday'], 'the email of 2 November is older than `since`'
    assert found[0].sender == DENTIST
    assert found[0].unread


def test_an_empty_text_lists_every_email_newest_first():
    found = make_deps(imap=FakeIMAP(emails())).mailbox.search('', THIS_WEEK)

    assert [e.uid for e in found] == [4, 3, 2]
    assert [e.unread for e in found] == [True, False, False]


def test_searching_changes_nothing_in_the_mailbox():
    server = FakeIMAP(emails())
    make_deps(imap=server).mailbox.search('dentist', THIS_WEEK)

    assert server.unread(4), 'searching marked the email read'
    assert not server.opened_read_write(), 'the folder was opened read-write: open it with select(..., readonly=True)'
    assert server.log[-1] == 'LOGOUT', 'log out when the search is done'


def test_the_run_hands_the_deps_to_the_tool_and_never_to_the_model():
    script = Script(('search_email', {'text': 'dentist', 'since': '2026-11-22'}), FINAL)
    result = run(script, make_deps(imap=FakeIMAP(emails())))

    assert result.usage.requests == 2
    assert 'Reminder: your dental cleaning on Friday' in returned(result, 'search_email')[0]
    seen_by_model = b''.join(ModelMessagesTypeAdapter.dump_json(r) for r in script.requests).decode() + json.dumps([t.parameters_json_schema for t in script.tools])
    assert PASSWORD not in seen_by_model and CALENDAR_URL not in seen_by_model


def test_two_tools_in_one_answer_take_one_trip():
    script = Script(
        [('search_email', {'text': 'dentist', 'since': '2026-11-22'}), ('list_events', {'start': '2026-11-27', 'end': '2026-11-27'})],
        FINAL,
    )
    result = run(script, make_deps(imap=FakeIMAP(emails())), "Did the dentist email me, and what's on my calendar Friday?")

    assert result.usage.requests == 2, 'both results go back in the same request'
    second = [p for p in script.requests[1][-1].parts if isinstance(p, ToolReturnPart)]
    assert sorted(p.tool_name for p in second) == ['list_events', 'search_email']


def test_a_missing_setting_stops_the_bot_before_it_answers_anything(monkeypatch: pytest.MonkeyPatch):
    for name in ('TELEGRAM_BOT_TOKEN', 'CALENDAR_ICS_URL', 'IMAP_HOST', 'IMAP_USER', 'IMAP_FOLDER', 'TIME_ZONE'):
        monkeypatch.setenv(name, 'UTC' if name == 'TIME_ZONE' else 'set-for-this-test')
    monkeypatch.delenv('IMAP_PASSWORD', raising=False)

    with pytest.raises(KeyError, match='IMAP_PASSWORD'):
        asyncio.run(bot.main())


# ---------- part 1: read one email, and leave it unread ----------


def test_read_email_is_offered_with_its_parameter_described():
    script = Script(FINAL)
    run(script, make_deps())

    found = tool(script, 'read_email')
    assert found.description, 'give read_email a docstring: it is all the model knows about the tool'
    properties = found.parameters_json_schema['properties']
    assert set(properties) == {'uid'}
    assert properties['uid']['type'] == 'integer'
    assert properties['uid'].get('description'), 'describe uid under Args: in the docstring'


def test_read_email_hands_back_the_text_of_the_email():
    script = Script(('read_email', {'uid': 4}), FINAL)
    result = run(script, make_deps(imap=FakeIMAP(emails())))

    text = returned(result, 'read_email')[0]
    assert "your dentist's office" in text
    assert 'Message-ID' not in text and 'Content-Type' not in text, 'hand back the text, not the raw email'


def test_an_email_sent_as_text_and_html_gives_its_text():
    script = Script(('read_email', {'uid': 3}), FINAL)
    result = run(script, make_deps(imap=FakeIMAP(emails())), 'What did Alex say?')

    text = returned(result, 'read_email')[0]
    assert 'Still on for 12:30 on Friday?' in text
    assert '<b>' not in text, 'this email has a plain text part: use it, not the HTML'


def test_reading_leaves_the_email_unread():
    server = FakeIMAP(emails())
    result = run(Script(('read_email', {'uid': 4}), FINAL), make_deps(imap=server))

    assert returned(result, 'read_email'), 'read_email did not hand back the email'
    assert server.unread(4), 'the owner has not read it: the bot reading it must not mark it read'
    assert not server.opened_read_write(), 'open the folder read-only, as search does'


def test_an_unknown_uid_is_sent_back_to_the_model():
    script = Script(('read_email', {'uid': 99}), ('read_email', {'uid': 4}), FINAL)
    result = run(script, make_deps(imap=FakeIMAP(emails())))

    assert result.usage.requests == 3, 'tell the model there is no such email (ModelRetry), so it can try again'
    assert [p.tool_name for p in sent_back(script)] == ['read_email']


# ---------- part 2: the owner's time zone, in Deps ----------

TOKYO = ZoneInfo('Asia/Tokyo')
LOS_ANGELES = ZoneInfo('America/Los_Angeles')
# 23:00 UTC on 2 December: 15:00 on the 2nd in Los Angeles, 08:00 on the 3rd in Tokyo.
CALL = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//always-on-assistant//test calendar//EN
BEGIN:VEVENT
UID:call@test
SUMMARY:Call with the Tokyo office
DTSTART:20261202T230000Z
DTEND:20261202T233000Z
END:VEVENT
END:VCALENDAR
"""


def deps_in(tz: ZoneInfo, **kwargs) -> bot.Deps:
    if 'tz' not in {f.name for f in dataclasses.fields(bot.Deps)}:
        pytest.fail('give Deps a field named tz: the time zone the owner lives in')
    deps = make_deps(tz=tz, **kwargs)
    assert deps.tz is tz
    return deps


def offset(tz: ZoneInfo, day: date) -> timedelta:
    return datetime(day.year, day.month, day.day, 12, tzinfo=tz).utcoffset()


def test_the_current_time_is_given_in_the_owners_time_zone():
    for tz, written in ((TOKYO, '+0900'), (LOS_ANGELES, '-0800')):
        script = Script(FINAL)
        run(script, deps_in(tz), 'Hi')
        instructions = script.requests[0][-1].instructions or ''
        assert written in instructions, f'with tz={tz.key} the model was told {instructions!r}'


def test_a_day_on_the_calendar_is_the_owners_day():
    tokyo = asyncio.run(bot.list_events(context(deps_in(TOKYO, calendar=CALL)), date(2026, 12, 3), date(2026, 12, 3)))
    assert [e.title for e in tokyo] == ['Call with the Tokyo office'], 'in Tokyo the call is on the morning of the 3rd'
    assert tokyo[0].start.hour == 8 and tokyo[0].start.utcoffset() == timedelta(hours=9)

    los_angeles = context(deps_in(LOS_ANGELES, calendar=CALL))
    assert asyncio.run(bot.list_events(los_angeles, date(2026, 12, 3), date(2026, 12, 3))) == [], 'in Los Angeles the 3rd is free'
    second = asyncio.run(bot.list_events(los_angeles, date(2026, 12, 2), date(2026, 12, 2)))
    assert second[0].start.hour == 15 and second[0].start.utcoffset() == timedelta(hours=-8)


def test_free_time_starts_at_nine_where_the_owner_is():
    slots = asyncio.run(bot.find_free_time(context(deps_in(TOKYO)), date(2026, 12, 5), 60))

    assert slots and slots[0].start == datetime(2026, 12, 5, 9, tzinfo=TOKYO)
    assert slots[-1].end == datetime(2026, 12, 5, 18, tzinfo=TOKYO)


def test_email_times_are_given_in_the_owners_time_zone():
    found = bot.search_email(context(deps_in(TOKYO, imap=FakeIMAP(emails()))), 'dentist', THIS_WEEK)

    assert found and found[0].received.utcoffset() == offset(TOKYO, found[0].received.date())
    assert found[0].received == datetime(2026, 11, 25, 17, 12, tzinfo=UTC), 'the same moment, only written in Tokyo time'
