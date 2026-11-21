"""
The performance assistant.

The model never queries the database. ``tools.py`` exposes a fixed set of
read-only functions over the analytics, cache, rate-limit, AI-usage, and
documentation services; ``engine.py`` picks the relevant ones for a
question, runs them, and hands the model the RESULTS as numbered facts.
The answer must cite those facts, and the raw facts are returned to the
caller next to the narrative so the dashboard can show measured numbers
separately from the model's interpretation.
"""
