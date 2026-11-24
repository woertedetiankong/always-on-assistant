[English](ep01b.md) · [看这一集的视频](https://buildautonomy.dev/courses/pydantic-ai/ep01b)

*第 1b 集 · 作业*

# 只回答你，而且一条坏消息打不死的机器人

视频里的机器人能用，但有两个漏洞。任何找到它的人都能用你的 API key 跟它聊天。只要有一次 agent 运行抛出异常，循环就结束了；重启之后同一个 update 又回来，再结束一次。你要在 poll_once 里把两个漏洞都补上，测试会告诉你补好了没有。

不需要 Telegram token，也不需要 API key。tests/fake_telegram.py 顶替 Telegram 的服务器，一个替身模型顶替 Gemini。

## 开始之前

在课程目录里先跑一遍测试。你应该看到 6 个通过、5 个失败：失败的就是你的作业。

```sh
cd assistant
uv run pytest tests/test_ep01b.py
```

先读一遍 tests/fake_telegram.py。它不到 60 行，保留了视频里 getUpdates 的两条规则：update 一直留在队列里，直到有一次调用带来了更大的 offset；一次调用返回从 offset 开始的全部 update。

## 第一部分：只回答主人

在 bot.py 里加一个模块级的名字 OWNER_ID：从环境变量 TELEGRAM_OWNER_ID 读出来的整数，没设置时是 None。OWNER_ID 有值时，来自其他聊天的消息既不触发 agent 运行，也不回复。

- 先预测：陌生人的消息被跳过了。offset 还应该移到它后面吗？如果不移，会发生什么？
- OWNER_ID 是 None 时，机器人的行为和视频里一样。第一次就靠这个找到自己的 chat id：把 update.message.chat.id 打印一次，然后设置这个变量。
- 这一部分有三个测试。它们会自己设置 bot.OWNER_ID。

## 第二部分：一条坏消息不能让机器人停下

在第 1a 集里，模型给的参数两次都没通过检查时，运行会抛出 UnexpectedModelBehavior。在视频版的 poll_once 里，这个异常会冲出函数，main 里的循环就此结束。请修改 poll_once：不管什么原因，只要一次运行抛出异常，就做到三件事：给发消息的人回一句“没处理成”，下一个 update 照常回答，失败的那个 update 不再回来。

- 先预测：替身模型对“bad one”这条消息每次都给一个坏的 due，对“good one”给正常回答。处理这两条消息的一次轮询，一共发了几次模型请求？
- 有一个测试让模型本身出故障，就像服务中断那样。你的代码不该关心运行为什么失败。

## 完成的标准

**11 个测试全部通过。** 然后把真的机器人跑起来，用手机给它发消息。

```sh
uv run pytest tests/test_ep01b.py
uv run --env-file .env python bot.py
```

真的机器人需要一个 assistant/.env 文件，里面三行。token 找 Telegram 里的 @BotFather 要（给它发 /newbot）。这个文件已被 git 忽略，别改这一点。

```sh
TELEGRAM_BOT_TOKEN=...
GOOGLE_API_KEY=...
TELEGRAM_OWNER_ID=...
```

**不要没看过就把这个机器人的报错贴到公开的地方。** httpx 的报错信息会打印完整的请求地址，地址里就有你的 token。token 万一泄露，给 @BotFather 发 /revoke。
