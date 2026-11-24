"""Assignment for episode 1b: a bot that only answers you, and that one bad message cannot stop.

Run from the assistant folder:   uv run pytest tests/test_ep01b.py

No Telegram token and no API key are needed: `fake_telegram.py` stands in for Telegram's servers
and a stand-in model replaces Gemini. The first five tests pass as soon as you have the code from
the video. Parts 1 and 2 fail until you change `poll_once` in bot.py.
"""

import asyncio

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

import bot
from fake_telegram import OWNER, STRANGER, FakeTelegram


class StandIn:
    """Answers 'echo: <the message>'. A message containing 'bad' always gets a `due` that is not a
    date, and a message containing 'down' makes the model fail like an outage would."""

    def __init__(self) -> None:
        self.history_sizes: list[int] = []  # how many messages each request carried

    def __call__(self, messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        self.history_sizes.append(len(messages))
        prompt = next(p.content for p in messages[0].parts if isinstance(p, UserPromptPart))
        assert isinstance(prompt, str)
        if 'down' in prompt:
            raise RuntimeError('the model provider is not answering')
        args = {'kind': 'chat', 'text': f'echo: {prompt}'}
        if 'bad' in prompt:
            args['due'] = 'tomorrow at 3pm'
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])

    @property
    def requests(self) -> int:
        return len(self.history_sizes)


def poll(telegram: FakeTelegram, model: StandIn, offset: int = 0) -> int:
    """Run bot.poll_once once against the stand-ins and return the offset it hands back."""

    async def go() -> int:
        async with telegram.client() as client:
            with bot.agent.override(model=FunctionModel(model)):
                return await bot.poll_once(client, offset)

    return asyncio.run(go())


@pytest.fixture(autouse=True)
def no_owner(monkeypatch: pytest.MonkeyPatch):
    """Every test starts with no owner set; the tests of part 1 set one."""
    monkeypatch.setattr(bot, 'OWNER_ID', None, raising=False)


# ---------- already true after the video ----------


def test_a_text_message_gets_one_reply():
    telegram, model = FakeTelegram(), StandIn()
    update_id = telegram.user_sends('hello')

    offset = poll(telegram, model)

    assert telegram.sent == [{'chat_id': OWNER, 'text': 'echo: hello'}]
    assert model.requests == 1
    assert offset == update_id + 1


def test_the_next_call_confirms_the_update():
    telegram, model = FakeTelegram(), StandIn()
    update_id = telegram.user_sends('hello')

    offset = poll(telegram, model)
    assert len(telegram.queue) == 1, 'answered, but Telegram still holds the update'
    poll(telegram, model, offset)

    assert telegram.offsets == [0, update_id + 1]
    assert telegram.queue == []
    assert len(telegram.sent) == 1, 'the same message was answered twice'


def test_a_sticker_is_skipped_but_the_offset_moves():
    telegram, model = FakeTelegram(), StandIn()
    update_id = telegram.user_sends_sticker()

    offset = poll(telegram, model)

    assert telegram.sent == [] and model.requests == 0
    assert offset == update_id + 1


def test_two_messages_are_answered_in_order():
    telegram, model = FakeTelegram(), StandIn()
    telegram.user_sends('first')
    last = telegram.user_sends('second')

    offset = poll(telegram, model)

    assert [m['text'] for m in telegram.sent] == ['echo: first', 'echo: second']
    assert offset == last + 1


def test_every_message_starts_a_fresh_run():
    """The second run is not handed the first one's messages: the bot has no memory yet."""
    telegram, model = FakeTelegram(), StandIn()
    telegram.user_sends('first')
    telegram.user_sends('second')

    poll(telegram, model)

    assert model.history_sizes == [1, 1]


# ---------- part 1: only answer the owner ----------


def test_a_stranger_gets_no_answer_and_costs_nothing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(bot, 'OWNER_ID', OWNER, raising=False)
    telegram, model = FakeTelegram(), StandIn()
    update_id = telegram.user_sends('hello, free AI!', chat_id=STRANGER)

    offset = poll(telegram, model)

    assert model.requests == 0, 'a stranger made your bot call the model'
    assert telegram.sent == []
    assert offset == update_id + 1, 'the stranger message must still be confirmed, or it comes back forever'


def test_the_owner_is_still_answered(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(bot, 'OWNER_ID', OWNER, raising=False)
    telegram, model = FakeTelegram(), StandIn()
    telegram.user_sends('hello')

    poll(telegram, model)

    assert telegram.sent == [{'chat_id': OWNER, 'text': 'echo: hello'}]


def test_a_stranger_between_two_of_your_messages(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(bot, 'OWNER_ID', OWNER, raising=False)
    telegram, model = FakeTelegram(), StandIn()
    telegram.user_sends('first')
    telegram.user_sends('let me in', chat_id=STRANGER)
    telegram.user_sends('second')

    poll(telegram, model)

    assert [(m['chat_id'], m['text']) for m in telegram.sent] == [(OWNER, 'echo: first'), (OWNER, 'echo: second')]
    assert model.requests == 2


# ---------- part 2: one bad message must not stop the bot ----------


def test_a_failed_run_does_not_stop_the_bot():
    """'bad one' fails the check from episode 1a twice, so its run raises. The next message must still be answered."""
    telegram, model = FakeTelegram(), StandIn()
    telegram.user_sends('bad one')
    last = telegram.user_sends('good one')

    offset = poll(telegram, model)

    assert model.requests == 3, 'two requests for the bad message (one retry), one for the good one'
    assert len(telegram.sent) == 2, 'the sender of the failed message should be told, and the next message answered'
    assert telegram.sent[0]['chat_id'] == OWNER and telegram.sent[0]['text'].strip()
    assert not telegram.sent[0]['text'].startswith('echo:')
    assert telegram.sent[1]['text'] == 'echo: good one'
    assert offset == last + 1


def test_a_model_outage_does_not_stop_the_bot():
    telegram, model = FakeTelegram(), StandIn()
    telegram.user_sends('the model is down')
    telegram.user_sends('good one')

    poll(telegram, model)

    assert len(telegram.sent) == 2
    assert telegram.sent[1]['text'] == 'echo: good one'


def test_the_failed_message_does_not_come_back():
    telegram, model = FakeTelegram(), StandIn()
    telegram.user_sends('bad one')

    offset = poll(telegram, model)
    poll(telegram, model, offset)

    assert telegram.queue == []
    assert model.requests == 2, 'the failed message was run again on the next poll'
