"""네이버쇼핑 검색 API 로 모델별 최저가를 조회한다 (메인 데이터 소스)."""
import os
import re
import requests

from matcher import title_matches

NAVER_URL = "https://openapi.naver.com/v1/search/shop.json"


def _strip_tags(s: str) -> str:
    """네이버가 검색어를 <b>..</b> 로 감싸주므로 태그를 제거한다."""
    return re.sub(r"<[^>]+>", "", s or "")


def _catalog_id_of(it: dict) -> str:
    """검색 결과 item 의 카탈로그(가격비교) ID. 없으면 ''."""
    pid = str(it.get("productId") or "")
    m = re.search(r"/catalog/(\d+)", it.get("link") or "")
    return m.group(1) if m else pid


def naver_request(query: str, display: int = 100, sort: str = "sim") -> list:
    """네이버쇼핑 검색 API 호출해서 items 리스트를 반환 (공용)."""
    cid = (os.environ.get("NAVER_CLIENT_ID") or "").strip()
    csec = (os.environ.get("NAVER_CLIENT_SECRET") or "").strip()
    if not cid or not csec:
        raise RuntimeError("환경변수 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 가 설정되지 않았습니다.")
    headers = {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec}
    params = {"query": query, "display": display, "sort": sort}
    resp = requests.get(NAVER_URL, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("items", [])


def search_naver_lowest(model: dict) -> dict | None:
    """model 설정에 맞는 상품 중 최저가 1건을 반환. 없으면 None.

    model 에 catalog_id 가 있으면 → 그 카탈로그(정확히 그 모델)의 최저가만 추적.
    없으면 → 기존 키워드/스펙 필터 방식.
    """
    items = naver_request(model["query"])

    catalog_id = str(model.get("catalog_id") or "").strip()
    min_price = model.get("min_price", 0)
    max_price = model.get("max_price")

    # --- 카탈로그 고정 모드 (정밀 추적) ---
    if catalog_id:
        for it in items:
            if _catalog_id_of(it) != catalog_id:
                continue
            try:
                price = int(it.get("lprice") or 0)
            except (ValueError, TypeError):
                continue
            if price <= 0:
                continue
            return {
                "price": price,
                "title": _strip_tags(it.get("title", "")),
                "link": it.get("link"),
                "mall": it.get("mallName") or "네이버쇼핑",
                "source": "naver",
            }
        print(f"  [naver] 지정 카탈로그({catalog_id}) 미발견 → 다나와 시도")
        return None

    # --- 키워드/스펙 필터 모드 ---
    best = None
    sample = []  # 매칭 실패 시 진단용: 네이버가 돌려준 상위 결과
    for it in items:
        title = _strip_tags(it.get("title", ""))
        if len(sample) < 12:
            sample.append((it.get("lprice"), title, it.get("mallName")))

        if not title_matches(title, model):
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
