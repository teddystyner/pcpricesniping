"""가격 관측 이력을 data/price_history.json 에 저장/로드한다 (상태 = 이전 관측값)."""
import json
import os

HISTORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "price_history.json")


def load_history() -> dict:
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_history(hist: dict) -> None:
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)
