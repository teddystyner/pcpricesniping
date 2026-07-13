"""각 모델의 '카탈로그(가격비교) 후보'를 뽑아 카탈로그 ID를 보여주는 헬퍼.

정밀 추적(B)을 위해, config.json 의 각 모델을 어떤 카탈로그로 고정할지 고를 때 사용.
실행: python find_catalog.py

출력의 [카탈로그ID] 중 원하는 모델의 ID를 골라, config.json 의 해당 모델에
"catalog_id": "그ID" 로 넣으면 그 모델의 최저가만 추적한다.
"""
import json
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from naver import naver_request, _strip_tags, _catalog_id_of

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def main() -> None:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)

    for model in cfg["models"]:
        print("=" * 70)
        print(f"[{model['name']}]  (검색어: {model['query']})")
        print("-" * 70)
        try:
            items = naver_request(model["query"], display=60, sort="sim")
        except Exception as e:  # noqa: BLE001
            print(f"  조회 실패: {e}")
            continue

        seen = set()
        shown = 0
        for it in items:
            cid = _catalog_id_of(it)
            # 카탈로그(가격비교)만, 중복 제거
            if not cid or cid in seen or "/catalog/" not in (it.get("link") or ""):
                continue
            seen.add(cid)
            title = _strip_tags(it.get("title", ""))
            price = it.get("lprice", "?")
            print(f"  카탈로그ID {cid:>14}  |  {int(price):>9,}원  |  {title}")
            shown += 1
            if shown >= 15:
                break

        if shown == 0:
            print("  카탈로그(가격비교) 후보가 없습니다. 검색어를 바꿔보세요.")
        print()


if __name__ == "__main__":
    main()
