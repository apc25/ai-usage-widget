"""Write a sample usage.json so the widget can be checked without Chrome."""
import argparse
import json
import os
import time
from pathlib import Path

USAGE_FILE = Path(os.environ["LOCALAPPDATA"]) / "AIUsageWidget" / "usage.json"
MIN, HOUR, DAY = 60_000, 3_600_000, 86_400_000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stale", action="store_true", help="mark data as 20 minutes old")
    ap.add_argument("--error", action="store_true", help="simulate ChatGPT logged out")
    args = ap.parse_args()
    now = int(time.time() * 1000)
    usage = {
        "claude": {
            "fiveHour": 42, "sevenDay": 76, "sevenDaySonnet": 93, "sevenDaySonnetLabel": "Fable",
            "resets": {"fiveHour": now + 2 * HOUR + 13 * MIN, "sevenDay": now + 3 * DAY + 4 * HOUR,
                       "sevenDaySonnet": now + 3 * DAY + 4 * HOUR},
        },
        "chatgpt": {"error": "chatgpt.com 로그인이 필요합니다"} if args.error else {
            "fiveHour": 8, "sevenDay": 55,
            "resets": {"fiveHour": now + 4 * HOUR + 30 * MIN, "sevenDay": now + 5 * DAY},
        },
        "updatedAt": now - 20 * MIN if args.stale else now,
    }
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    USAGE_FILE.write_text(json.dumps(usage, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {USAGE_FILE}")


if __name__ == "__main__":
    main()
