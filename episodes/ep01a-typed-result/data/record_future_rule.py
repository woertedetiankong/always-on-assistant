"""STAGED run for "your turn": Reply gets a rule (due must be in the future); a stand-in model
sends yesterday first, then tomorrow. No API call, no key.

Usage (from the course root):
    cd assistant && uv run python ../episodes/ep01a-typed-result/data/record_future_rule.py

Writes data/future_rule.json.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import field_validator
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

os.environ.setdefault('GOOGLE_API_KEY', 'placeholder-staged-run-makes-no-request')
models.ALLOW_MODEL_REQUESTS = False

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'assistant'))
import bot  # noqa: E402


class FutureReply(bot.Reply):
    """Reply plus the rule the learner is asked to add."""

    @field_validator('due')
    @classmethod
    def due_in_future(cls, due: datetime | None) -> datetime | None:
        if due is not None and due <= datetime.now(due.tzinfo):
            raise ValueError('due must be in the future')
        return due


NOW = datetime.now().astimezone().replace(microsecond=0)
YESTERDAY = (NOW - timedelta(days=1)).isoformat()
TOMORROW = (NOW + timedelta(days=1)).isoformat()
PROMPT = 'Remind me to call the dentist tomorrow at 3pm.'
calls = 0


def stand_in(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    global calls
    calls += 1
    due = YESTERDAY if calls == 1 else TOMORROW
    args = {'kind': 'reminder', 'text': 'I will remind you.', 'due': due}
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args, tool_call_id=f'call_{calls}')])


async def main() -> None:
    nodes: list[str] = []
    async with bot.agent.iter(PROMPT, output_type=FutureReply, model=FunctionModel(stand_in)) as run:
        async for node in run:
            nodes.append(type(node).__name__)
    result = run.result
    assert result is not None
    out = {
        'staged': True,
        'nodes': nodes,
        'requests': result.usage.requests,
        'output_type': type(result.output).__name__,
        'messages': json.loads(ModelMessagesTypeAdapter.dump_json(result.all_messages())),
    }
    path = Path(__file__).parent / 'future_rule.json'
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    print(f'wrote {path}')
    print('nodes:', ' -> '.join(nodes))
    retried = out['messages'][2]['parts'][0]
    print('retry message:', retried['outcome'], '|', retried['content'][0]['msg'])


if __name__ == '__main__':
    asyncio.run(main())
