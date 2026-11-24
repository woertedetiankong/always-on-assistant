"""A stand-in for Telegram's servers, for tests: no token, no network.

It keeps the two rules of the real `getUpdates` that the bot depends on:
an update stays in the queue until a call arrives with an `offset` above its `update_id`,
and a call returns every update from `offset` on.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

OWNER = 111
STRANGER = 999


class FakeTelegram:
    def __init__(self, first_update_id: int = 500) -> None:
        self.queue: list[dict[str, Any]] = []
        self.next_update_id = first_update_id
        self.offsets: list[int] = []  # the offset of every getUpdates call, in order
        self.sent: list[dict[str, Any]] = []  # the parameters of every sendMessage call, in order

    # ---- what a person does ----
    def user_sends(self, text: str, chat_id: int = OWNER) -> int:
        return self._add({'chat': {'id': chat_id, 'type': 'private'}, 'date': 1795000000, 'text': text})

    def user_sends_sticker(self, chat_id: int = OWNER) -> int:
        return self._add({'chat': {'id': chat_id, 'type': 'private'}, 'date': 1795000000, 'sticker': {'emoji': '👍'}})

    def _add(self, message: dict[str, Any]) -> int:
        update_id = self.next_update_id
        self.next_update_id += 1
        message = {'message_id': update_id - 400, 'from': {'id': message['chat']['id'], 'is_bot': False}, **message}
        self.queue.append({'update_id': update_id, 'message': message})
        return update_id

    # ---- what the bot sees ----
    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url='https://fake.telegram/botTOKEN/', transport=httpx.MockTransport(self._handle))

    def _handle(self, request: httpx.Request) -> httpx.Response:
        method = request.url.path.rsplit('/', 1)[-1]
        params = json.loads(request.content or b'{}')
        if method == 'getUpdates':
            offset = params.get('offset') or 0
            self.offsets.append(offset)
            self.queue = [u for u in self.queue if u['update_id'] >= offset]  # lower ids are confirmed
            return httpx.Response(200, json={'ok': True, 'result': list(self.queue)})
        if method == 'sendMessage':
            if not 1 <= len(params.get('text') or '') <= 4096:
                return httpx.Response(400, json={'ok': False, 'error_code': 400, 'description': 'Bad Request: message text is empty'})
            self.sent.append(params)
            return httpx.Response(200, json={'ok': True, 'result': {'message_id': 9000 + len(self.sent), 'chat': {'id': params['chat_id']}, 'text': params['text']}})
        return httpx.Response(404, json={'ok': False, 'error_code': 404, 'description': 'Not Found'})
