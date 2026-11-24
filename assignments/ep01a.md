[中文](ep01a.zh.md) · [Watch the episode](https://buildautonomy.dev/courses/pydantic-ai/ep01a)

*EPISODE 1a · ASSIGNMENT*

# Give Reply two rules

In the video the model answered by calling a function built from your class, and the arguments were checked against that class. Now you decide what the check accepts. You add two rules to Reply, and the tests tell you whether they work.

No API key is needed. A stand-in model replaces Gemini in the tests, so they cost nothing.

## Before you start

From the course folder, run the tests once. You should see 4 pass and 5 fail: the failing ones are your assignment.

```sh
cd assistant
uv run pytest tests/test_ep01a.py
```

## Part 1: due must be in the future

This is the rule from the end of the video. Add it to Reply in bot.py. A reminder for yesterday makes no sense, so a past due should fail the check.

- Predict first: when the stand-in sends yesterday's date, how many requests will the run make?
- Two tests cover this part: one checks the class on its own, the other checks that the agent really asks the model again.

## Part 2: text must say something, briefly

The video did not show this one. The reply text goes to a chat app, so an empty reply or a wall of text is a bug. Make Reply reject a text that is empty or only spaces, and a text longer than 280 characters.

- Exactly 280 characters must still be accepted.
- Look up how Pydantic limits a string's length; you do not need a hand-written check for that half.

## Done when

**All 9 tests pass.** Then run the real bot once and read its output: the rules now apply to Gemini's answers too.

```sh
uv run pytest tests/test_ep01a.py
uv run python bot.py        # needs GOOGLE_API_KEY
```

Stuck? Run the staged retry from the video and read the message that goes back to the model:

```sh
uv run python ../episodes/ep01a-typed-result/data/record_future_rule.py
```
