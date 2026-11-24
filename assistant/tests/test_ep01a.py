"""Assignment for episode 1a: give Reply two rules.

Run from the assistant folder:   uv run pytest tests/test_ep01a.py

No API key is needed: a stand-in model replaces Gemini. The first three tests pass as soon as you
have the code from the video. Parts 1 and 2 fail until you add the rules to Reply in bot.py.
"""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

import bot

NOW = datetime.now(timezone.utc)
YESTERDAY = NOW - timedelta(days=1)
TOMORROW = NOW + timedelta(days=1)
PROMPT = 'Remind me to call the dentist tomorrow at 3pm.'


# ---------- already true after the video ----------


def test_reply_keeps_its_three_fields():
    assert {'kind', 'text', 'due'} <= set(bot.Reply.model_fields)


def test_a_reply_without_due_is_fine():
    assert bot.Reply(kind='chat', text='Hello!').due is None


def test_a_future_due_is_accepted():
    assert bot.Reply(kind='reminder', text='I will remind you.', due=TOMORROW).due == TOMORROW


# ---------- part 1: the rule from the video: due must be in the future ----------


def test_a_past_due_is_rejected():
    with pytest.raises(ValidationError):
        bot.Reply(kind='reminder', text='I will remind you.', due=YESTERDAY)


def test_the_agent_asks_again_after_a_past_due():
    """The stand-in sends yesterday first, then tomorrow. Your rule should send the first one back."""
    requests: list[int] = []

    def stand_in(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        requests.append(len(messages))
        due = YESTERDAY if len(requests) == 1 else TOMORROW
        args = {'kind': 'reminder', 'text': 'I will remind you.', 'due': due.isoformat()}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args, tool_call_id=f'call_{len(requests)}')])

    result = bot.agent.run_sync(PROMPT, model=FunctionModel(stand_in))

    assert len(requests) == 2, 'the past date was accepted: the model was never asked again'
    assert result.output.due == TOMORROW
    assert result.usage.requests == 2


# ---------- part 2: a rule the video did not show: text must say something, briefly ----------


@pytest.mark.parametrize('text', ['', '   '])
def test_an_empty_text_is_rejected(text: str):
    with pytest.raises(ValidationError):
        bot.Reply(kind='chat', text=text)


def test_a_text_over_280_characters_is_rejected():
    with pytest.raises(ValidationError):
        bot.Reply(kind='chat', text='x' * 281)


def test_a_280_character_text_is_accepted():
    assert len(bot.Reply(kind='chat', text='x' * 280).text) == 280
