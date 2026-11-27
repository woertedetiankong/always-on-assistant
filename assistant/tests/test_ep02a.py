"""Assignment for episode 2a: a second tool, and a first tool that sends bad dates back.

Run from the assistant folder:   uv run pytest tests/test_ep02a.py

No calendar address, no API key and no network are needed: every test reads the small calendar
below, and a stand-in model plays a script of tool calls. The first four tests pass as soon as you
have the code from the video. Parts 1 and 2 fail until you change bot.py.

Since episode 2b the tools take what they need from `ctx.deps`, so these tests hand the bot a Deps
whose http client serves CALENDAR (fake_deps.py). Until 2b they swapped `bot.fetch_calendar` instead.
"""

import asyncio
from datetime import date, datetime, time

import pytest
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from fake_deps import context, make_deps
from pydantic_ai.usage import UsageLimits

import bot

# Times without a time zone are read in your own time zone, so the tests give the same answer anywhere.
# 2026-12-02 is a Wednesday: the weekly team sync (started 2026-11-04) falls on it.
CALENDAR = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//always-on-assistant//test calendar//EN
BEGIN:VEVENT
UID:sync@test
SUMMARY:Team sync
DTSTART:20261104T093000
DTEND:20261104T100000
RRULE:FREQ=WEEKLY
END:VEVENT
BEGIN:VEVENT
UID:dentist@test
SUMMARY:Dentist
DTSTART:20261202T150000
DTEND:20261202T160000
END:VEVENT
BEGIN:VEVENT
UID:birthday@test
SUMMARY:Mom's birthday
DTSTART;VALUE=DATE:20261202
DTEND;VALUE=DATE:20261203
END:VEVENT
BEGIN:VEVENT
UID:lunch@test
SUMMARY:Lunch with Alex
DTSTART:20261203T120000
DTEND:20261203T130000
END:VEVENT
END:VCALENDAR
"""
DAY = date(2026, 12, 2)
FINAL = ('final', {'kind': 'chat', 'text': 'Here is your day.'})
DEPS = make_deps(calendar=CALENDAR)


class Script:
    """A stand-in model that answers each request with the next call on its list.

    ('final', args) calls the output tool, which ends the run; any other name calls that tool."""

    def __init__(self, *calls: tuple[str, dict]) -> None:
        self.calls = list(calls)
        self.requests: list[list[ModelMessage]] = []
        self.tools = []

    def __call__(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        self.requests.append(list(messages))
        self.tools = info.function_tools
        name, args = self.calls[min(len(self.requests), len(self.calls)) - 1]
        if name == 'final':
            name = info.output_tools[0].name
        return ModelResponse(parts=[ToolCallPart(name, args, tool_call_id=f'call_{len(self.requests)}')])


def run(script: Script, prompt: str = "What's on my calendar tomorrow?", request_limit: int = 10):
    with bot.agent.override(model=FunctionModel(script)):
        return bot.agent.run_sync(prompt, deps=DEPS, usage_limits=UsageLimits(request_limit=request_limit))


def tool(script: Script, name: str):
    found = [t for t in script.tools if t.name == name]
    assert found, f'the model was not offered a tool named {name!r}'
    return found[0]


def sent_back(script: Script) -> list[ToolReturnPart]:
    """Every tool call that went back to the model to be made again, in order.

    For an ordinary tool, bad arguments and a ModelRetry both come back as a tool return marked 'retried'."""
    return [
        p
        for m in script.requests[-1]
        if isinstance(m, ModelRequest)
        for p in m.parts
        if isinstance(p, ToolReturnPart) and p.outcome == 'retried'
    ]


# ---------- already true after the video ----------


def test_the_model_is_offered_list_events():
    script = Script(FINAL)
    run(script)

    schema = tool(script, 'list_events').parameters_json_schema
    assert set(schema['properties']) == {'start', 'end'}
    assert schema['properties']['start']['format'] == 'date'


def test_one_day_of_events_sorted_all_day_first():
    events = asyncio.run(bot.list_events(context(DEPS), DAY, DAY))

    assert [e.title for e in events] == ["Mom's birthday", 'Team sync', 'Dentist']
    assert events[0].start == DAY, 'an all-day event keeps a date, not a time'
    assert events[1].start.time() == time(9, 30), 'the weekly meeting was not repeated onto this day'


def test_a_calendar_question_takes_two_requests():
    script = Script(('list_events', {'start': '2026-12-02', 'end': '2026-12-02'}), FINAL)
    result = run(script)

    assert result.usage.requests == 2
    assert len(result.all_messages()) == 5
    returned = [p for m in result.all_messages() for p in m.parts if isinstance(p, ToolReturnPart) and p.tool_name == 'list_events']
    assert 'Dentist' in returned[0].model_response_str()


def test_a_31_day_range_is_fine():
    script = Script(('list_events', {'start': '2026-12-01', 'end': '2026-12-31'}), FINAL)
    result = run(script)

    assert result.usage.requests == 2
    assert sent_back(script) == []


# ---------- part 1: a second tool, find_free_time ----------


def test_find_free_time_is_offered_with_every_parameter_described():
    script = Script(FINAL)
    run(script)

    found = tool(script, 'find_free_time')
    assert found.description, 'give find_free_time a docstring: it is all the model knows about the tool'
    properties = found.parameters_json_schema['properties']
    assert set(properties) == {'day', 'minutes'}
    for name, field in properties.items():
        assert field.get('description'), f'parameter {name!r} has no description'


def spans(slots) -> list[tuple[time, time]]:
    return [(slot.start.time(), slot.end.time()) for slot in slots]


def test_free_time_of_at_least_an_hour():
    slots = asyncio.run(bot.find_free_time(context(DEPS), DAY, 60))

    assert spans(slots) == [(time(10), time(15)), (time(16), time(18))]
    assert all(isinstance(slot.start, datetime) and slot.start.date() == DAY for slot in slots)


def test_free_time_of_half_an_hour_and_an_empty_day():
    """An all-day event (the birthday) does not make you busy; a day with nothing on is free from 9 to 18."""
    assert spans(asyncio.run(bot.find_free_time(context(DEPS), DAY, 30))) == [(time(9), time(9, 30)), (time(10), time(15)), (time(16), time(18))]
    assert spans(asyncio.run(bot.find_free_time(context(DEPS), date(2026, 12, 5), 30))) == [(time(9), time(18))]


def test_the_model_can_call_find_free_time():
    script = Script(('find_free_time', {'day': '2026-12-02', 'minutes': 60}), FINAL)
    result = run(script, 'When am I free tomorrow for an hour?')

    assert result.usage.requests == 2
    returned = [p for m in result.all_messages() for p in m.parts if isinstance(p, ToolReturnPart) and p.tool_name == 'find_free_time']
    answer = returned[0].model_response_str()
    assert 'T10:00' in answer and 'T15:00' in answer, f'the model got back {answer[:80]!r}, not the free slots'


# ---------- part 2: send a bad range back to the model ----------


def test_an_end_before_the_start_is_sent_back():
    script = Script(
        ('list_events', {'start': '2026-12-03', 'end': '2026-12-02'}),
        ('list_events', {'start': '2026-12-02', 'end': '2026-12-03'}),
        FINAL,
    )
    result = run(script)

    assert result.usage.requests == 3, 'the bad range should cost one extra request: the model is told, then tries again'
    assert [p.tool_name for p in sent_back(script)] == ['list_events']


def test_more_than_31_days_is_sent_back():
    script = Script(
        ('list_events', {'start': '2026-12-01', 'end': '2027-01-01'}),
        ('list_events', {'start': '2026-12-01', 'end': '2026-12-31'}),
        FINAL,
    )
    result = run(script)

    assert result.usage.requests == 3
    assert [p.tool_name for p in sent_back(script)] == ['list_events']


def test_two_bad_ranges_in_a_row_end_the_run():
    """One retry is the default. A second bad range fails the run, and 1b's try/except tells the sender."""
    script = Script(('list_events', {'start': '2026-12-03', 'end': '2026-12-02'}))

    with pytest.raises(UnexpectedModelBehavior):
        try:
            run(script, request_limit=4)
        except UsageLimitExceeded:
            pytest.fail('the model sent the same bad range four times and was never told it was wrong')
    assert len(script.requests) == 2
