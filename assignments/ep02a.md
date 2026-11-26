[中文](ep02a.zh.md) · [Watch the episode](https://buildautonomy.dev/courses/pydantic-ai/ep02a)

*EPISODE 2a · ASSIGNMENT*

# A second tool, and a first tool that sends bad dates back

The bot from the video reads your calendar through one tool, list_events. You add a second tool the model can call, find_free_time. Then you make list_events refuse a date range it cannot use, so the model fixes its call instead of the run going wrong.

No calendar address, no API key and no network are needed. Every test swaps bot.fetch_calendar for a small calendar written at the top of the test file, and a stand-in model plays a script of tool calls.

## Before you start

From the course folder, run the tests once. You should see 4 pass and 7 fail: the failing ones are your assignment.

```sh
cd assistant
uv run pytest tests/test_ep02a.py
```

Read the CALENDAR at the top of tests/test_ep02a.py. On Wednesday 2026-12-02 it has a weekly team sync from 9:30 to 10:00, the dentist from 15:00 to 16:00, and Mom's birthday all day. Lunch with Alex is the next day. Its times have no time zone, so they are read in yours and the tests give the same answer anywhere.

## Part 1: a second tool, find_free_time

Add a tool find_free_time(day, minutes) that returns the free stretches of one day, between 9:00 and 18:00 in your time zone, that are at least minutes long. Return a list of Slot, a class you write with two fields, start and end, both datetime.

- Register it with @agent.tool_plain, like list_events. Its docstring is all the model knows about it: the first line says what it does, and every parameter gets a line under Args:. The tests read the tool list the model receives, the same list as the video's stop 2.
- Get the events by calling list_events(day, day) from your function: it is an ordinary async function too.
- An all-day event, such as the birthday, does not make you busy.
- Predict first: on 2026-12-02 with minutes=60, how many slots come back, and which?

## Part 2: send a bad range back to the model

Make list_events raise ModelRetry (from pydantic_ai import ModelRetry) when end comes before start, or when the range is longer than 31 days. 2026-12-01 to 2026-12-31 is fine; 2026-12-01 to 2027-01-01 is not. The message is written for the model: say what is wrong and what to send instead.

- Predict first: the stand-in sends an end before the start, then a good range. How many model requests does the run make?
- In episode 1a, final_result's bad arguments went back to the model as a tool result marked retried. A ModelRetry from your tool travels the same way, and the model calls again. One retry is the default: a second bad range in a row fails the run, and your try/except from 1b tells the sender.

## Done when

**All 11 tests pass.** Then run the real bot and ask it about your own calendar.

```sh
uv run pytest tests/test_ep02a.py
uv run --env-file .env python bot.py
```

The real bot needs one more line in assistant/.env. In Google Calendar, open Settings, pick the calendar on the left, and copy the Secret address in iCal format under Integrate calendar. Any calendar that gives an iCal (.ics) address works the same way.

```sh
TELEGRAM_BOT_TOKEN=...
GOOGLE_API_KEY=...
TELEGRAM_OWNER_ID=...
CALENDAR_ICS_URL=...
```

Try “What's on my calendar tomorrow?” and “When am I free tomorrow for an hour?”

**The secret address is a key to your calendar.** Anyone who has it can read every event, and an httpx error message prints it in full, like the token in 1b. If it leaks, click Reset next to it in the same settings. To record or share your screen, make a separate calendar and use only its own address.
