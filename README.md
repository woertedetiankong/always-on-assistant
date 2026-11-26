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
Telegram, so they need no API key and no token. On `main` they all pass: `main` is the finished assistant.

## Episodes

| Episode | Title | Start the assignment | Assignment | Tests | At the start |
|---|---|---|---|---|---|
| 1a | One message in, one typed result out | `git checkout ep01a-start` | [assignments/ep01a.md](assignments/ep01a.md) | `tests/test_ep01a.py` | 4 pass, 5 fail |
| 1b | Put it on Telegram | `git checkout ep01b-start` | [assignments/ep01b.md](assignments/ep01b.md) | `tests/test_ep01b.py` | 6 pass, 5 fail |
| 2a | Read the calendar: the first tool | `git checkout ep02a-start` | [assignments/ep02a.md](assignments/ep02a.md) | `tests/test_ep02a.py` | 4 pass, 7 fail |

`main` is the assistant as it stands after the latest episode, with every published assignment solved: it is
the product, and the place to read a solution once you have tried. To do an assignment, check out the episode's
start tag, for example `git checkout ep02a-start`. There `assistant/bot.py` is exactly as that video ends, and
the episode's tests fail as its handout says. `assistant/history/bot_epNN.py` keeps each video's end state too.

## Running the real bot

The real bot needs a file `assistant/.env` (ignored by git; keep it that way):

```sh
GOOGLE_API_KEY=...        # a Gemini API key; the videos use google:gemini-3.8-flash
TELEGRAM_BOT_TOKEN=...    # from @BotFather in Telegram, from episode 1b on
TELEGRAM_OWNER_ID=...     # your own chat id, after the 1b assignment
CALENDAR_ICS_URL=...      # a calendar's secret iCal address, from episode 2a on: a secret, like the token
```

```sh
cd assistant
uv run --env-file .env python bot.py
```

The first time an agent runs, Pydantic AI prints a banner (a small logo and a pointer to its observability
tool) above the bot's own output. That is normal and the videos leave it out; set `PYDANTIC_AI_NO_BANNER=1`
to hide it.

Never paste a traceback from the bot in public without reading it first: an httpx error message prints the
full request address, and the address contains your token. If a token leaks, send `/revoke` to @BotFather.

## Source

The videos read the framework's own source, pinned at
[pydantic/pydantic-ai v2.71.0](https://github.com/pydantic/pydantic-ai/tree/v2.71.0), the same version
`assistant/pyproject.toml` installs, so every `file:line` on screen matches what you have.
This course is not affiliated with or endorsed by Pydantic.

## License

[MIT](LICENSE)
