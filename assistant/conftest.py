"""Test setup for the course assignments: no API key, and no request may reach a real model."""

import os

# bot.py names a Google model, which looks for a key when the agent is created.
# The tests replace the model with a stand-in, so a placeholder is enough.
os.environ.setdefault('GOOGLE_API_KEY', 'placeholder-tests-make-no-request')

from pydantic_ai import models  # noqa: E402

models.ALLOW_MODEL_REQUESTS = False
