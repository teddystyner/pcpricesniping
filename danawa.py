"""다나와 검색 결과에서 최저가를 긁는다 (보조 소스, best-effort).

다나와는 공식 API가 없어 HTML 구조에 의존하므로 언제든 깨질 수 있다.
그래서 예외는 모두 삼키고 실패 시 None 을 반환한다. (메인은 네이버)
"""
import re
import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://search.danawa.com/dsearch.php"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "").lower()


def _to_int(s: str) -> int | None:
    digits = re.sub(r"[^0-9]", "", s or "")
    return int(digits) if digits else None


def search_danawa_lowest(model: dict) -> dict | None:
    include = model.get("include_keywords", [])
    any_kw = model.get("any_keywords", [])
    exclude = model.get("exclude_keywords", [])
    min_price = model.get("min_price", 0)
    max_price = model.get("max_price")

    try:
        params = {"query": model["query"], "sort": "saveDESC"}
        resp = requests.get(SEARCH_URL, params=params,
                            headers={"User-Agent": UA}, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        best = None
        for li in soup.select("li.prod_item"):
            name_el = li.select_one(".prod_name a")
            price_el = li.select_one(".price_sect strong")
            if not name_el or not price_el:
                continue

            title = name_el.get_text(strip=True)
            ntitle = _norm(title)
            if any(_norm(k) not in ntitle for k in include):
                continue
            if any_kw and not any(_norm(k) in ntitle for k in any_kw):
                continue
            if any(_norm(k) in ntitle for k in exclude):
                continue

            price = _to_int(price_el.get_text())
            if not price or price < min_price:
                continue
            if max_price and price > max_price:
                continue

            link = name_el.get("href")
            cand = {"price": price, "title": title, "link": link,
                    "mall": "다나와", "source": "danawa"}
            if best is None or price < best["price"]:
                best = cand
        return best
    except Exception as e:  # noqa: BLE001 - 보조 소스라 조용히 실패
        print(f"  [danawa] 조회 실패(무시): {e}")
        return None
