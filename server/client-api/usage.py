"""Tracks the time, tokens and estimated cost of every AI call (Jev and OpenAI).

Each call prints one line to the server log and is added to model-calls.jsonl, which
lives in a Docker volume so it survives restarts. See the totals with tests/11-costs.sh
(it runs: python usage.py).

Costs are ESTIMATES from the prices below, in dollars per million tokens. Prices change:
check the providers' price pages and set them in .env.
"""

import json
import os
import threading
import time
from pathlib import Path

LOG = Path(os.getenv("USAGE_LOG", "/data/model-calls.jsonl"))

PRICES = {  # (input, output) dollars per million tokens
    "jev": (float(os.getenv("JEV_PRICE_INPUT", "0.042")), float(os.getenv("JEV_PRICE_OUTPUT", "0"))),
    "openai": (float(os.getenv("OPENAI_PRICE_INPUT", "1.25")), float(os.getenv("OPENAI_PRICE_OUTPUT", "10"))),
}

_lock = threading.Lock()


def record(provider: str, model: str, purpose: str, started: float, input_tokens: int, output_tokens: int):
    """Call right after a model call. `started` is time.time() from just before the call."""
    seconds = time.time() - started
    price_in, price_out = PRICES[provider]
    cost = (input_tokens * price_in + output_tokens * price_out) / 1_000_000
    print(
        f"[ai] {purpose}: {model}, {seconds:.1f}s, "
        f"{input_tokens} in / {output_tokens} out tokens, ~${cost:.4f}",
        flush=True,
    )
    entry = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "provider": provider,
        "model": model,
        "purpose": purpose,
        "seconds": round(seconds, 2),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost": round(cost, 6),
    }
    with _lock:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as f:
            f.write(json.dumps(entry) + "\n")


def summary():
    """Print totals per provider from the log file."""
    if not LOG.exists():
        print("No AI calls recorded yet.")
        return
    totals = {}
    for line in LOG.read_text().splitlines():
        e = json.loads(line)
        t = totals.setdefault(e["provider"], {"calls": 0, "seconds": 0, "in": 0, "out": 0, "cost": 0})
        t["calls"] += 1
        t["seconds"] += e["seconds"]
        t["in"] += e["input_tokens"]
        t["out"] += e["output_tokens"]
        t["cost"] += e["cost"]

    print(f"{'':8} {'calls':>6} {'avg time':>9} {'input tokens':>13} {'output tokens':>14} {'est. cost':>10}")
    for provider, t in totals.items():
        print(
            f"{provider:8} {t['calls']:>6} {t['seconds'] / t['calls']:>8.1f}s "
            f"{t['in']:>13,} {t['out']:>14,} {'$%.4f' % t['cost']:>10}"
        )
    print(f"{'total':8} {'':>6} {'':>9} {'':>13} {'':>14} {'$%.4f' % sum(t['cost'] for t in totals.values()):>10}")
    print("\nCosts are estimates from the prices in usage.py / .env.")


if __name__ == "__main__":
    summary()
