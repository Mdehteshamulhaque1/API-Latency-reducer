"""Locust workload for Phase‑5 evaluation.

Sends 100 unique prompts with a skewed distribution (some repeat often).
All requests use temperature = 0 (deterministic).
"""

from locust import HttpUser, task, between, events
import random
import json

# ----------------------------------------------------------------------
# 100 distinct prompts – 30 "popular" (high weight) and 70 "rare"
# ----------------------------------------------------------------------
POPULAR = [
    "Explain quantum computing in simple terms.",
    "Write a Python function to reverse a list.",
    "What is the capital of New Zealand?",
    "Describe the plot of Moby‑Dick.",
    "How do you bake a sourdough bread?",
    # fill up to 30
] + [f"Popular {i}" for i in range(6, 31)]

RARE = [
    "Quote the first line of Hamlet.",
    "List the planets in the solar system in order.",
    "What is the derivative of x²?",
    "Define atropism in philosophy.",
    "Translate 'hello' into Esperanto.",
    # fill up to 70
] + [f"Rare {i}" for i in range(11, 71)]

# Combine to exactly 100 prompts
PROMPTS = POPULAR + RARE[:70 - len(POPULAR)]

# Track how many times each prompt has been sent (reset per user)
prompt_counts: dict[str, int] = {p: 0 for p in PROMPTS}


def _pick_prompt() -> str:
    """Weighted choice: popular prompts 3× more likely than rare ones."""
    weights = [3 if p in POPULAR else 1 for p in PROMPTS]
    chosen = random.choices(PROMPTS, weights=weights, k=1)[0]
    prompt_counts[chosen] += 1
    # Reset counters after 100 prompts per user (the original logic)
    if sum(prompt_counts.values()) >= 100:
        for k in prompt_counts:
            prompt_counts[k] = 0


# ----------------------------------------------------------------------
# Locust user class
# ----------------------------------------------------------------------
class ChatUser(HttpUser):
    """Sends 100 chat‑completion requests with a skewed prompt distribution."""

    wait_time = between(0.05, 0.3)

    @task
    def send_chat(self):
        prompt = _pick_prompt()
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        self.client.post("/v1/chat/completions", json=payload)