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
在 `main` 上测试全部通过：`main` 是做好的助理。

## 各集

| 集 | 标题 | 开始做作业 | 作业 | 测试 | 刚开始时 |
|---|---|---|---|---|---|
| 1a | 一条消息进，一个带类型的结果出 | `git checkout ep01a-start` | [assignments/ep01a.zh.md](assignments/ep01a.zh.md) | `tests/test_ep01a.py` | 4 个通过, 5 个失败 |
| 1b | 把它接到 Telegram 上 | `git checkout ep01b-start` | [assignments/ep01b.zh.md](assignments/ep01b.zh.md) | `tests/test_ep01b.py` | 6 个通过, 5 个失败 |
| 2a | 读日历：第一个工具 | `git checkout ep02a-start` | [assignments/ep02a.zh.md](assignments/ep02a.zh.md) | `tests/test_ep02a.py` | 4 个通过, 7 个失败 |

`main` 是最新一集之后的助理，已发布各集的作业都已做完：它就是产品，也是你自己做过之后对照答案的地方。
要做作业，先切到那一集的起点 tag，例如 `git checkout ep02a-start`。在那里 `assistant/bot.py`
和那一集视频结束时完全一样，那一集的测试按作业说明失败。`assistant/history/bot_epNN.py` 也保存着每一集视频结束时的代码。

## 运行真的机器人

真的机器人需要一个 `assistant/.env` 文件（已被 git 忽略，别改这一点）：

```sh
GOOGLE_API_KEY=...        # Gemini 的 API key；视频里用的是 google:gemini-3.8-flash
TELEGRAM_BOT_TOKEN=...    # 找 Telegram 里的 @BotFather 要，第 1b 集开始需要
TELEGRAM_OWNER_ID=...     # 你自己的 chat id，做完 1b 的作业之后需要
CALENDAR_ICS_URL=...      # 日历的 iCal 私密地址，第 2a 集开始需要；它和 token 一样是秘密
```

```sh
cd assistant
uv run --env-file .env python bot.py
```

agent 第一次运行时，Pydantic AI 会在机器人自己的输出上面打印一段横幅（一个小图标，加上它的可观测性工具的介绍）。
这是正常的，视频里没有展示；设置 `PYDANTIC_AI_NO_BANNER=1` 可以关掉它。

不要没看过就把机器人的报错贴到公开的地方：httpx 的报错信息会打印完整的请求地址，地址里就有你的 token。
token 万一泄露，给 @BotFather 发 `/revoke`。

## 源码

视频精读的是框架自己的源码，固定在
[pydantic/pydantic-ai v2.71.0](https://github.com/pydantic/pydantic-ai/tree/v2.71.0)，
和 `assistant/pyproject.toml` 安装的是同一个版本，所以屏幕上的每个 `文件:行号` 都和你本地的一致。
本课程与 Pydantic 无关联，也未获其背书。

## 许可

[MIT](LICENSE)
