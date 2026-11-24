"""Lesson 1b: the same agent, now answering on Telegram."""

import asyncio
import os
from datetime import datetime
from typing import Any, Literal

import httpx
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


class Chat(BaseModel):
    id: int


class Message(BaseModel):
    chat: Chat
    text: str | None = None


class Update(BaseModel):
    """One thing that happened to the bot, as Telegram reports it."""

    update_id: int
    message: Message | None = None


async def call(telegram: httpx.AsyncClient, method: str, **params: Any) -> Any:
    """Make one Telegram Bot API call and return its result."""
    response = await telegram.post(method, json=params)
    response.raise_for_status()
    return response.json()['result']


async def poll_once(telegram: httpx.AsyncClient, offset: int) -> int:
    """Ask for the updates from `offset` on, answer each text message, return the next offset."""
    for raw in await call(telegram, 'getUpdates', offset=offset, timeout=30):
        update = Update.model_validate(raw)
        offset = update.update_id + 1
        if update.message and update.message.text:
            result = await agent.run(update.message.text)
            await call(telegram, 'sendMessage', chat_id=update.message.chat.id, text=result.output.text)
    return offset


async def main() -> None:
    url = f'https://api.telegram.org/bot{os.environ["TELEGRAM_BOT_TOKEN"]}/'
    async with httpx.AsyncClient(base_url=url, timeout=40) as telegram:
        offset = 0
        while True:
            offset = await poll_once(telegram, offset)


if __name__ == '__main__':
    asyncio.run(main())
