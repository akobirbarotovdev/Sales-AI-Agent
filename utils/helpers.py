import random
import asyncio
import json
from datetime import datetime


def human_delay(min_s: float = 1.5, max_s: float = 4.0):
    return random.uniform(min_s, max_s)


async def ahuman_delay(min_s: float = 1.5, max_s: float = 4.0):
    await asyncio.sleep(random.uniform(min_s, max_s))


def safe_json_loads(text: str, default=None):
    result = extract_json(text, expect_list=False)
    return result if result is not None else (default or {})


def extract_json(text: str, expect_list: bool = False):
    """Robustly pull a JSON object/array out of an LLM response.

    Claude often wraps JSON in ```json ... ``` fences or adds prose before/after.
    Plain json.loads() fails on those, so we strip fences and slice from the
    first opening bracket to the last matching closing bracket.
    Returns None on failure so callers can fall back deliberately.
    """
    if not text:
        return None
    import re
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", t, re.DOTALL)
    if fence:
        t = fence.group(1).strip()

    open_ch, close_ch = ("[", "]") if expect_list else ("{", "}")
    try:
        start = t.index(open_ch)
        end = t.rindex(close_ch) + 1
        return json.loads(t[start:end])
    except (ValueError, json.JSONDecodeError):
        try:
            return json.loads(t)
        except (ValueError, json.JSONDecodeError):
            return None


def truncate(text: str, max_len: int = 2000) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def now_iso() -> str:
    return datetime.utcnow().isoformat()
