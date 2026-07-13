"""네이버쇼핑 검색 API 로 모델별 최저가를 조회한다 (메인 데이터 소스)."""
import os
import re
import requests

NAVER_URL = "https://openapi.naver.com/v1/search/shop.json"


def _norm(s: str) -> str:
    """공백 제거 + 소문자화 해서 키워드 매칭을 느슨하게 한다."""
    return re.sub(r"\s+", "", s or "").lower()


def _strip_tags(s: str) -> str:
    """네이버가 검색어를 <b>..</b> 로 감싸주므로 태그를 제거한다."""
    return re.sub(r"<[^>]+>", "", s or "")


def search_naver_lowest(model: dict) -> dict | None:
    """model 설정에 맞는 상품 중 최저가 1건을 반환. 없으면 None."""
    # GitHub Secret 붙여넣기 시 딸려오는 줄바꿈/공백 제거 (헤더 오류 방지)
    cid = (os.environ.get("NAVER_CLIENT_ID") or "").strip()
    csec = (os.environ.get("NAVER_CLIENT_SECRET") or "").strip()
    if not cid or not csec:
        raise RuntimeError("환경변수 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 가 설정되지 않았습니다.")

    headers = {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec}
    params = {"query": model["query"], "display": 100, "sort": "sim"}  # 정확도순
    resp = requests.get(NAVER_URL, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    items = resp.json().get("items", [])

    include = model.get("include_keywords", [])
    any_kw = model.get("any_keywords", [])
    exclude = model.get("exclude_keywords", [])
    min_price = model.get("min_price", 0)
    max_price = model.get("max_price")

    best = None
    sample = []  # 매칭 실패 시 진단용: 네이버가 돌려준 상위 결과
    for it in items:
        title = _strip_tags(it.get("title", ""))
        ntitle = _norm(title)
        if len(sample) < 12:
            sample.append((it.get("lprice"), title, it.get("mallName")))

        # 필수 키워드가 하나라도 빠지면 제외 (엉뚱한 모델 방지)
        if any(_norm(k) not in ntitle for k in include):
            continue
        # any_keywords: 표기가 여러 개일 때 최소 하나는 포함돼야 함 (예: slim5/슬림5)
        if any_kw and not any(_norm(k) in ntitle for k in any_kw):
            continue
        # 제외 키워드(액세서리/중고 등)가 있으면 제외
        if any(_norm(k) in ntitle for k in exclude):
            continue

        try:
            price = int(it.get("lprice") or 0)
        except (ValueError, TypeError):
            continue
        if price <= 0 or price < min_price:
            continue
        if max_price and price > max_price:
            continue

        cand = {
            "price": price,
            "title": title,
            "link": it.get("link"),
            "mall": it.get("mallName") or "네이버쇼핑",
            "source": "naver",
        }
        if best is None or price < best["price"]:
            best = cand

    if best is None:
        print(f"  [naver] 매칭 0건 (총 {len(items)}개 수신). 상위 결과 샘플:")
        for lprice, title, mall in sample:
            print(f"       - {lprice}원 | {title} | {mall}")

    return best
