[English](ep02a.md) · [看这一集的视频](https://buildautonomy.dev/courses/pydantic-ai/ep02a)

*第 2a 集 · 作业*

# 第二个工具，和一个会把坏日期退回去的工具

视频里的机器人靠一个工具 list_events 读你的日历。你要再加一个模型能调用的工具 find_free_time。然后让 list_events 拒绝它没法用的日期范围，让模型改正自己的调用，而不是让这次运行出错。

不需要日历地址，不需要 API key，也不联网。每个测试都把 bot.fetch_calendar 换成测试文件开头写好的一个小日历，再由一个替身模型按剧本调用工具。

## 开始之前

在课程目录里先跑一遍测试。你应该看到 4 个通过、7 个失败：失败的就是你的作业。

```sh
cd assistant
uv run pytest tests/test_ep02a.py
```

读一遍 tests/test_ep02a.py 开头的 CALENDAR。2026-12-02 星期三这天有：每周一次的 team sync，9:30 到 10:00；看牙医，15:00 到 16:00；还有全天的"妈妈生日"。和 Alex 吃午饭在第二天。这些时间没写时区，所以按你自己的时区读，测试在哪里跑结果都一样。

## 第一部分：第二个工具 find_free_time

加一个工具 find_free_time(day, minutes)，返回某一天 9:00 到 18:00 之间（按你的时区）、长度至少 minutes 分钟的空闲时间段。返回值是 Slot 的列表；Slot 是你自己写的类，有 start 和 end 两个字段，都是 datetime。

- 像 list_events 一样用 @agent.tool_plain 注册。它的 docstring 就是模型对这个工具知道的全部：第一行说它做什么，每个参数在 Args: 下面各写一行。测试读的是模型收到的工具列表，和视频第 2 站看的是同一份。
- 在你的函数里调用 list_events(day, day) 拿到当天的事件：它本身也是一个普通的 async 函数。
- 全天事件（比如那个生日）不算占用时间。
- 先预测：2026-12-02、minutes=60 时，返回几个时间段？分别是哪几段？

## 第二部分：把坏的日期范围退回给模型

让 list_events 在结束日早于开始日、或者范围超过 31 天时抛出 ModelRetry（from pydantic_ai import ModelRetry）。2026-12-01 到 2026-12-31 可以；2026-12-01 到 2027-01-01 不行。错误信息是写给模型看的：说清楚哪里不对，应该怎么传。

- 先预测：替身模型先传一个结束早于开始的范围，再传一个正确的。这次运行一共发几次模型请求？
- 在第 1a 集里，final_result 的坏参数作为一条标记为 retried 的工具结果发回给模型。你的工具抛出的 ModelRetry 也是这样发回去的，模型再调用一次。默认只重试一次：连续第二次传错，这次运行就失败，1b 作业里写的 try/except 会告诉发消息的人。

## 完成的标准

**11 个测试全部通过。** 然后把真的机器人跑起来，问问它你自己的日历。

```sh
uv run pytest tests/test_ep02a.py
uv run --env-file .env python bot.py
```

真的机器人需要在 assistant/.env 里再加一行。在 Google 日历里打开设置，左边选中那个日历，在"集成日历"下面复制"iCal 格式的私密地址"。其他日历只要能给出 iCal（.ics）地址，用法都一样。

```sh
TELEGRAM_BOT_TOKEN=...
GOOGLE_API_KEY=...
TELEGRAM_OWNER_ID=...
CALENDAR_ICS_URL=...
```

试试问它 "What's on my calendar tomorrow?" 和 "When am I free tomorrow for an hour?"

**私密地址就是你日历的钥匙。** 任何拿到它的人都能读到你的全部日程，而 httpx 的报错信息会把它完整打印出来，就像 1b 里的 token 一样。万一泄露，在同一个设置页面点它旁边的"重置"。要录屏或者共享屏幕的话，单独建一个日历，只用那个日历自己的地址。
