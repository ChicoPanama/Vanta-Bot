from __future__ import annotations

import json
import os

ABI_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "config",
    "abis",
)
TRADING_ABI_PATH = os.path.join(ABI_DIR, "Trading.json")


def inspect_trading_events() -> dict[str, list[str]]:
    with open(TRADING_ABI_PATH) as f:
        obj = json.load(f)
    abi = obj.get("abi", obj) if isinstance(obj, dict) else obj
    if not isinstance(abi, list):
        raise ValueError("Trading ABI is not a list")
    events = {}
    for item in abi:
        if item.get("type") == "event":
            events[item["name"]] = [
                inp.get("name", "") for inp in item.get("inputs", [])
            ]
    return events


if __name__ == "__main__":
    evs = inspect_trading_events()
    for name, fields in evs.items():
        print(f"{name}: {fields}")
