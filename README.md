# Build an Always-On Assistant with Pydantic AI: the code

English | [中文](README.zh.md)

The bot, the tests and the assignment handouts for the video course
[Build an Always-On Assistant with Pydantic AI](https://buildautonomy.dev/courses/pydantic-ai).
The course builds one project: every episode adds a working piece to the same assistant in `assistant/`.

## Set up

Install [uv](https://docs.astral.sh/uv/), then:

```sh
cd assistant
uv run pytest
```

The first run installs Python 3.13 and the dependencies. The tests use a stand-in model and a stand-in
Telegram, so they need no API key and no token. As shipped, some tests fail: the failing ones are the assignments.

## Episodes

| Episode | Title | `bot.py` as the video ends | Assignment | Tests | Before you start |
|---|---|---|---|---|---|
| 1a | One message in, one typed result out | `history/bot_ep01a.py` | [assignments/ep01a.md](assignments/ep01a.md) | `tests/test_ep01a.py` | 4 pass, 5 fail |
| 1b | Put it on Telegram | `history/bot_ep01b.py` | [assignments/ep01b.md](assignments/ep01b.md) | `tests/test_ep01b.py` | 6 pass, 5 fail |

`assistant/bot.py` is the bot as the latest episode's video ends. To start an earlier episode from its own
video, copy that episode's file over it, for example `cp history/bot_ep01a.py bot.py`. The tests of earlier
episodes also run against the latest `bot.py`.

There are no solutions in this repository: the tests tell you when an assignment is done.

## Running the real bot

The real bot needs a file `assistant/.env` (ignored by git; keep it that way):

```sh
GOOGLE_API_KEY=...        # a Gemini API key; the videos use google:gemini-3.8-flash
TELEGRAM_BOT_TOKEN=...    # from @BotFather in Telegram, from episode 1b on
TELEGRAM_OWNER_ID=...     # your own chat id, after the 1b assignment
```

```sh
cd assistant
uv run --env-file .env python bot.py
```

Never paste a traceback from the bot in public without reading it first: an httpx error message prints the
full request address, and the address contains your token. If a token leaks, send `/revoke` to @BotFather.

## Source

The videos read the framework's own source, pinned at
[pydantic/pydantic-ai v2.71.0](https://github.com/pydantic/pydantic-ai/tree/v2.71.0), the same version
`assistant/pyproject.toml` installs, so every `file:line` on screen matches what you have.
This course is not affiliated with or endorsed by Pydantic.
