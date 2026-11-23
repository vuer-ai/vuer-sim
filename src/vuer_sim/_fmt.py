"""Number formatting and the stored JSON form shared by every vuer-sim file."""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any


def num(v: float) -> str:
    """Shortest text that parses back to the same float (``1.0`` -> ``"1"``)."""
    v = float(v)
    if v.is_integer() and abs(v) < 1e16:
        return str(int(v))
    return repr(v)


def nums(vs: Iterable[float]) -> str:
    """Space-separated ``num`` values, as MJCF writes vectors."""
    return " ".join(num(v) for v in vs)


def parse_nums(text: str) -> tuple[float, ...]:
    return tuple(float(t) for t in str(text).split())


def dumps(obj: Any) -> str:
    """Stored form of the DreamLake bundle contract: sorted keys, 2-space indent, trailing newline."""
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
