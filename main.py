"""가격 모니터링 진입점.

동작:
  1) config.json 의 모델별로 네이버쇼핑(메인) → 실패 시 다나와(보조) 최저가 조회
  2) 직전 관측가(price_history.json) 대비 하락률 계산
  3) 하락률 >= drop_threshold(기본 10%) 이면 텔레그램 알림
  4) 관측값을 price_history.json 에 갱신 저장

로컬: `python main.py`           (한 번 실행)
      `python main.py test`      (텔레그램 연결 확인용 메시지 1건 발송)
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

# Windows 콘솔(cp949)에서도 이모지/한글 print 가 깨지지 않도록 UTF-8 로 고정
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from dotenv import load_dotenv
    load_dotenv()  # 로컬 .env 지원 (Actions 에서는 무시됨)
except ImportError:
    pass

from naver import search_naver_lowest
from danawa import search_danawa_lowest
from notifier import send_telegram
from storage import load_history, save_history

KST = timezone(timedelta(hours=9))
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def _won(n: int) -> str:
    return f"{n:,}원"


def _now_str() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")


def _fetch_lowest(model: dict) -> dict | None:
    """네이버(메인) → 다나와(보조) 순으로 최저가를 구한다."""
    try:
        best = search_naver_lowest(model)
        if best:
            return best
        print(f"  [naver] 조건에 맞는 상품 없음 → 다나와 시도")
    except Exception as e:  # noqa: BLE001
        print(f"  [naver] 조회 실패 → 다나와 시도: {e}")

    return search_danawa_lowest(model)


def _build_alert(model: dict, prev: int, cur: int, best: dict, lowest_ever: int) -> str:
    drop_pct = (prev - cur) / prev * 100
    return (
        f"🔻 <b>{model['name']}</b> 특가!\n"
        f"{_won(prev)} → <b>{_won(cur)}</b> (-{drop_pct:.1f}%)\n"
        f"🏪 {best['mall']} · 역대최저 {_won(lowest_ever)}\n"
        f"🔗 {best['link']}"
    )


def run() -> None:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)

    threshold = cfg.get("drop_threshold", 0.10)
    hist = load_history()
    now = _now_str()
    alerts = []

    for model in cfg["models"]:
        mid = model["id"]
        print(f"[{model['name']}] 조회 중...")
        best = _fetch_lowest(model)

        if not best:
            print(f"  → 최저가를 찾지 못했습니다. (스킵)")
            continue

        cur = best["price"]
        rec = hist.get(mid, {})
        prev = rec.get("last_price")
        lowest_ever = min(cur, rec.get("lowest_ever", cur))
        print(f"  → 현재 최저가 {_won(cur)} ({best['source']}/{best['mall']})"
              + (f", 직전 {_won(prev)}" if prev else ", (첫 관측)"))

        # 하락 판정: '이전 관측 대비' 10% 이상 하락 시 알림
        alerted = False
        if prev and prev > 0:
            drop = (prev - cur) / prev
            if drop >= threshold:
                alerts.append(_build_alert(model, prev, cur, best, lowest_ever))
                alerted = True
                print(f"  🔔 알림! 하락률 {drop * 100:.1f}%")

        hist[mid] = {
            "name": model["name"],
            "last_price": cur,
            "last_seen": now,
            "last_title": best["title"],
            "last_link": best["link"],
            "last_mall": best["mall"],
            "last_source": best["source"],
            "lowest_ever": lowest_ever,
            "last_alert_price": cur if alerted else rec.get("last_alert_price"),
        }

    if alerts:
        header = f"📉 <b>노트북 가격 하락 감지</b> ({now})\n\n"
        send_telegram(header + "\n\n".join(alerts))
        print(f"\n텔레그램 알림 {len(alerts)}건 발송 완료.")
    else:
        print("\n조건(10%+ 하락)을 만족하는 모델이 없어 알림을 보내지 않았습니다.")

    save_history(hist)
    print("이력 저장 완료.")


def notify_test() -> None:
    send_telegram(f"✅ 노트북 가격 모니터 연결 테스트 성공 ({_now_str()})")
    print("테스트 메시지를 발송했습니다. 텔레그램을 확인하세요.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        notify_test()
    else:
        run()
