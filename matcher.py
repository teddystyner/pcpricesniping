"""제목이 특정 모델 조건에 맞는지 판정하는 공용 매처 (naver/danawa 공용).

config 의 모델별 조건:
  - include_keywords : 전부 포함돼야 함 (AND)
  - keyword_groups   : [[a,b], [c,d]] 형태. 각 그룹마다 최소 1개 포함 (AND of OR)
                       예) [["16gb","16g"], ["512gb","512g"]] = 16GB '그리고' 512GB
  - any_keywords     : 하위호환용. 있으면 하나의 그룹으로 취급
  - exclude_keywords : 하나라도 있으면 탈락 (256GB, 중고, 구형 등)
가격 범위(min_price/max_price)는 호출측에서 별도 검사한다.
"""
import re


def norm(s: str) -> str:
    """공백 제거 + 소문자화 (느슨한 매칭용)."""
    return re.sub(r"\s+", "", s or "").lower()


def title_matches(title: str, model: dict) -> bool:
    t = norm(title)

    for k in model.get("include_keywords", []):
        if norm(k) not in t:
            return False

    groups = list(model.get("keyword_groups", []))
    if model.get("any_keywords"):
        groups.append(model["any_keywords"])
    for grp in groups:
        if not any(norm(k) in t for k in grp):
            return False

    for k in model.get("exclude_keywords", []):
        if norm(k) in t:
            return False

    return True
