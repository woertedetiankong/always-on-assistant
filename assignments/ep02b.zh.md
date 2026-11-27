[English](ep02b.md) · [看这一集的视频](https://buildautonomy.dev/courses/pydantic-ai/ep02b)

*第 2b 集 · 作业*

# 读一封邮件但不标已读，以及把你的时区放进 Deps

视频里的机器人通过 deps 拿到工具需要的东西：一个 http 客户端、日历地址和一个只读的 Mailbox。search_email 按邮件头找邮件。你要加一个工具，读出一封邮件的正文，而且不把它标成已读。然后把主人的时区放进 Deps，让机器人理解的"明天"不再取决于它跑在哪台机器上。

不需要邮箱、密码、API key，也不联网。每个测试都交给机器人一个用替身做的 Deps（tests/fake_deps.py）：一个直接回答测试日历的 http 客户端，和一个假的 IMAP 服务器（tests/fake_imap.py），它回答的样子和录视频时 Gmail 的回答一样。再由一个替身模型按剧本调用工具。

## 开始之前

在课程目录里先跑一遍测试。你应该看到 7 个通过、9 个失败：失败的就是你的作业。

```sh
cd assistant
uv run pytest tests/test_ep02b.py
```

读一遍 tests/test_ep02b.py 开头的 emails()：四封邮件，最新的一封是 Bright Smile Dental 发来的未读提醒（uid 4）。Lunch Friday?（uid 3）同时有纯文本和 HTML 两个版本。再读一下 tests/fake_imap.py 开头的说明：它列出了测试检查的那几条 IMAP 规则。

## 第一部分：read_email，读完保持未读

加一个工具 read_email(ctx, uid)，返回文件夹里一封邮件的正文。它是 search_email 的后半段：search 给模型一些 uid，read_email 读出其中一封。

- 用 @agent.tool 注册，第一个参数是 ctx: RunContext[Deps]。在 docstring 的 Args: 下面写一行 uid 的说明。
- 给 Mailbox 加一个方法 read(uid)：用 self.opened() 打开文件夹（这样就是只读的），用 BODY.PEEK[] 取邮件（imap.uid('FETCH', str(uid), '(BODY.PEEK[])')）。
- 用 email.message_from_bytes(raw, policy=email.policy.default) 解析，取 message.get_body(preferencelist=('plain', 'html')).get_content()：邮件有纯文本部分时就用它。
- 文件夹里没有这个 uid 时，Gmail 的回答里没有邮件内容。这时抛出 ModelRetry，让模型换一个 search_email 给过的 uid。
- 先预测：如果你用读写方式打开文件夹、用 RFC822 取邮件，那封提醒的未读标记会怎样？假服务器和 IMAP 的规则一样。

## 第二部分：主人的时区，放进 Deps

现在机器人用的是机器的时区（datetime.now().astimezone()）。放到服务器上往往是 UTC，对住在洛杉矶的人来说，"明天"会从下午 4 点开始。给 Deps 加一个字段 tz: ZoneInfo（from zoneinfo import ZoneInfo），凡是指主人的时间的地方都用它：

- now()：@agent.instructions 函数也可以接收 ctx，用 ctx.deps.tz 告诉模型当前时间。
- list_events：用 datetime.combine(day, time.min, tz) 建日期范围，每个事件的时间都换成 tz。没有时区的时间（"浮动"时间）按主人的时区读。
- find_free_time：主人所在地的 9:00 到 18:00。
- search_email：每封邮件的接收时间，用 tz 表示。
- main()：和其他设置一起，在启动前从 TIME_ZONE=America/Los_Angeles 读出来。

测试把同一个日历分别放在东京和洛杉矶跑：12 月 2 日 UTC 23:00 的一个电话，在东京是 3 号早上，在洛杉矶是 2 号下午。等 Deps 有了这个字段，前几集的测试也会传一个 tz 进去。

## 完成的标准

**16 个测试全部通过，前几集的测试也仍然通过。** 然后把真的机器人接到你自己的邮箱上跑起来。

```sh
uv run pytest
uv run --env-file .env python bot.py
```

- 在 Gmail 里建一个标签，比如 assistant-demo（名字里不带空格最省事）。IMAP 会把每个标签显示成一个文件夹。
- 往里面放几封邮件：给你自己的几封邮件打上这个标签，或者运行 uv run --env-file .env python seed_demo_mail.py，它会加五封发件人是编出来的演示邮件。标签里已经有邮件时，它什么都不加。
- 给账号开启两步验证，然后在 myaccount.google.com/apppasswords 生成一个应用专用密码。复制那 16 个字母，去掉空格。
- 在 assistant/.env 里加五行：

```sh
IMAP_HOST=imap.gmail.com
IMAP_USER=you@gmail.com
IMAP_PASSWORD=abcdabcdabcdabcd
IMAP_FOLDER=assistant-demo
TIME_ZONE=America/Los_Angeles
```

试试问它 "Did the dentist's office email me this week?" 和 "What did Alex say about lunch?"

**应用专用密码能打开你的整个邮箱，能读也能写。** 机器人只以只读方式打开那一个文件夹，也从不打印密码；但它仍然不应该出现在你分享的任何东西里。用完了在同一个页面删掉它，它立刻失效。开启了 Google 高级保护的账号不能生成应用专用密码；别家邮箱的 IMAP 服务器用法一样，换成它自己的地址和密码即可。
