[中文](ep01b.zh.md) · [Watch the episode](https://buildautonomy.dev/courses/pydantic-ai/ep01b)

*EPISODE 1b · ASSIGNMENT*

# A bot that answers only you, and that one bad message cannot stop

The bot from the video works, and it has two holes. Anyone who finds it can talk to it on your API key. And one agent run that raises ends the loop; after a restart the same update comes back and ends it again. You close both in poll_once, and the tests tell you whether they are closed.

No Telegram token and no API key are needed. tests/fake_telegram.py stands in for Telegram's servers and a stand-in model replaces Gemini.

## Before you start

From the course folder, run the tests once. You should see 6 pass and 5 fail: the failing ones are your assignment.

```sh
cd assistant
uv run pytest tests/test_ep01b.py
```

Read tests/fake_telegram.py first. It is under 60 lines, and it keeps the two rules of getUpdates from the video: an update stays queued until a call arrives with a higher offset, and a call returns everything from offset on.

## Part 1: only answer the owner

Add a module-level name OWNER_ID to bot.py: an int read from the environment variable TELEGRAM_OWNER_ID, or None when it is not set. When OWNER_ID is set, a message from any other chat gets no agent run and no reply.

- Predict first: a stranger's message is skipped. Should offset still move past it? What happens if it does not?
- When OWNER_ID is None the bot behaves as in the video. That is how you find your own chat id the first time: print update.message.chat.id once, then set the variable.
- Three tests cover this part. They set bot.OWNER_ID themselves.

## Part 2: one bad message must not stop the bot

In episode 1a a run raised UnexpectedModelBehavior when the model's arguments failed the check twice. In the video's poll_once that error leaves the function, and the loop in main ends. Change poll_once so that a run that raises, for any reason, does three things: the sender gets a short message saying it could not be handled, the next update is still answered, and the failed update does not come back.

- Predict first: the stand-in sends a bad due every time for the message 'bad one', and a good answer for 'good one'. How many model requests does one poll make for those two messages?
- One test makes the model itself fail, the way an outage would. Your code should not care why the run failed.

## Done when

**All 11 tests pass.** Then run the real bot and message it from your phone.

```sh
uv run pytest tests/test_ep01b.py
uv run --env-file .env python bot.py
```

The real bot needs a file assistant/.env with three lines. Get the token from @BotFather in Telegram (send it /newbot). The file is ignored by git; keep it that way.

```sh
TELEGRAM_BOT_TOKEN=...
GOOGLE_API_KEY=...
TELEGRAM_OWNER_ID=...
```

**Never paste a traceback from this bot in public without reading it first.** An httpx error message prints the full request address, and the address contains your token. If a token leaks, send /revoke to @BotFather.
