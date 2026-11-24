"""Lesson 1a: one message in, one typed result out."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent


class Reply(BaseModel):
    """What the assistant does with one incoming message."""

    kind: Literal['chat', 'task', 'reminder']
    text: str
    due: datetime | None = None


agent = Agent(
    'google:gemini-3.8-flash',
    output_type=Reply,
    instructions='You are a personal assistant. Decide what the message is, and write a short reply.',
)


@agent.instructions
def now() -> str:
    return f'The current time is {datetime.now().astimezone():%A %Y-%m-%d %H:%M %z}.'


if __name__ == '__main__':
    result = agent.run_sync('Remind me to call the dentist tomorrow at 3pm.')
    print(repr(result.output))
