# 用 Pydantic AI 做一个常驻助理：代码

[English](README.md) | 中文

视频课程[《用 Pydantic AI 做一个常驻助理》](https://buildautonomy.dev/courses/pydantic-ai)的机器人、测试和作业说明。
整门课只做一个项目：每一集给 `assistant/` 里的同一个助理加一块能跑的功能。

## 准备

先安装 [uv](https://docs.astral.sh/uv/)，然后：

```sh
cd assistant
uv run pytest
```

第一次运行会安装 Python 3.13 和依赖。测试用替身模型和替身 Telegram，不需要 API key，也不需要 token。
刚拿到时有一部分测试是失败的：失败的就是作业。

## 各集

| 集 | 标题 | 视频结束时的 `bot.py` | 作业 | 测试 | 开始之前 |
|---|---|---|---|---|---|
| 1a | 一条消息进，一个带类型的结果出 | `history/bot_ep01a.py` | [assignments/ep01a.zh.md](assignments/ep01a.zh.md) | `tests/test_ep01a.py` | 4 个通过, 5 个失败 |
| 1b | 把它接到 Telegram 上 | `history/bot_ep01b.py` | [assignments/ep01b.zh.md](assignments/ep01b.zh.md) | `tests/test_ep01b.py` | 6 个通过, 5 个失败 |

`assistant/bot.py` 是最新一集视频结束时的机器人。想从更早的一集开始，把那一集的文件拷过来，
例如 `cp history/bot_ep01a.py bot.py`。早先各集的测试也能对着最新的 `bot.py` 运行。

仓库里没有答案：测试会告诉你作业做完了没有。

## 运行真的机器人

真的机器人需要一个 `assistant/.env` 文件（已被 git 忽略，别改这一点）：

```sh
GOOGLE_API_KEY=...        # Gemini 的 API key；视频里用的是 google:gemini-3.8-flash
TELEGRAM_BOT_TOKEN=...    # 找 Telegram 里的 @BotFather 要，第 1b 集开始需要
TELEGRAM_OWNER_ID=...     # 你自己的 chat id，做完 1b 的作业之后需要
```

```sh
cd assistant
uv run --env-file .env python bot.py
```

不要没看过就把机器人的报错贴到公开的地方：httpx 的报错信息会打印完整的请求地址，地址里就有你的 token。
token 万一泄露，给 @BotFather 发 `/revoke`。

## 源码

视频精读的是框架自己的源码，固定在
[pydantic/pydantic-ai v2.71.0](https://github.com/pydantic/pydantic-ai/tree/v2.71.0)，
和 `assistant/pyproject.toml` 安装的是同一个版本，所以屏幕上的每个 `文件:行号` 都和你本地的一致。
本课程与 Pydantic 无关联，也未获其背书。

## 许可

[MIT](LICENSE)
