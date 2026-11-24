[English](ep01a.md) · [看这一集的视频](https://buildautonomy.dev/courses/pydantic-ai/ep01a)

*第 1a 集 · 作业*

# 给 Reply 加两条规则

视频里，模型通过调用一个由你的类生成的函数来回答，参数会按这个类检查。现在由你来决定这次检查放行什么：给 Reply 加两条规则，测试会告诉你它们是否生效。

不需要 API key。测试里用一个替身模型顶替 Gemini，不花钱。

## 开始之前

在课程目录里先跑一遍测试。你应该看到 4 个通过、5 个失败：失败的就是你的作业。

```sh
cd assistant
uv run pytest tests/test_ep01a.py
```

## 第一部分：due 必须在未来

这是视频结尾的那条规则。把它加到 bot.py 的 Reply 里。提醒昨天的事没有意义，所以过去的 due 应当通不过检查。

- 先预测：替身模型发来昨天的日期时，这次运行会发几次请求？
- 这一部分有两个测试：一个只检查这个类，另一个检查 agent 是否真的再问了一次模型。

## 第二部分：text 要有内容，而且要短

这条视频里没有演示。回复要发到聊天软件里，所以空回复或一大段文字都是 bug。让 Reply 拒绝空的或只有空格的 text，也拒绝超过 280 个字符的 text。

- 正好 280 个字符仍然要通过。
- 查一下 Pydantic 怎么限制字符串长度；这一半不需要手写检查。

## 完成的标准

**9 个测试全部通过。** 然后真的跑一次机器人，读一读输出：这些规则现在对 Gemini 的回答同样生效。

```sh
uv run pytest tests/test_ep01a.py
uv run python bot.py        # needs GOOGLE_API_KEY
```

卡住了？跑一遍视频里的摆拍重试，读一读发回给模型的那条信息：

```sh
uv run python ../episodes/ep01a-typed-result/data/record_future_rule.py
```
