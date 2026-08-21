"""점수화: 가격(저평가·재건축·상승여력) · 통근 · 상권 · 육아 (가중합 0~100)."""
from __future__ import annotations


def _norm(v, lo, hi):
    if hi == lo:
        return 0.0
    return max(0.0, min(100.0, (v - lo) / (hi - lo) * 100))


def price_score(l):
    """가격 메리트 + 재건축 가능성 + 집값 상승세를 합산."""
    # 1) 기본: 저평가(실거래 대비 싸게 = 상승여력)
    if l.get("undervalue_pct") is not None:        # 매매: 실거래 대비 저평가
        base = _norm(l["undervalue_pct"], -5, 25)
    elif l.get("jeonse_ratio") is not None:        # 전세: 전세가율 낮을수록↑
        base = _norm(95 - l["jeonse_ratio"], 0, 35)
    else:
        base = 45.0                                 # 실거래 매칭 없음 → 중립
    # 2) 재건축 가능성: 구축일수록 가점(오래될수록 재건축 기대)
    by = l.get("build_year")
    if isinstance(by, int):
        if by <= 1990:
            base += 22                              # 재건축 유력(35년 안팎 구축)
        elif by <= 2000:
            base += 12                              # 노후 진행(재건축 여지)
    # 3) 집값 상승 모멘텀: 최근 6개월 실거래 중위 상승
    t = l.get("trend") or []
    if len(t) >= 2:
        first, last = t[0].get("median"), t[-1].get("median")
        if first and last and last > first:
            base += 12                              # 상승세
    return round(min(100.0, base), 1)


def commute_score(l):
    cm = l.get("commute_min")
    return _norm(40 - cm, 0, 35) if cm is not None else 0.0   # 5분↓=만점, 40분=0


def childcare_score(l):
    base = _norm(l.get("daycare", 0), 2, 35) * 0.5             # 어린이집/유치원 밀도(2~35)
    ns = l.get("nearest_school")
    if ns:
        d = ns["dist_m"]
        base += 50 if d <= 300 else (40 if d <= 600 else (25 if d <= 1000 else 10))  # 초등 근접
    return round(min(100.0, base), 1)


def amenity_score(l):
    return _norm(l.get("mart", 0) + l.get("hospital", 0), 3, 60)   # 마트+병원(3~60)


def score_listing(l, weights):
    parts = {
        "price": price_score(l),
        "commute": commute_score(l),
        "amenity": amenity_score(l),
        "childcare": childcare_score(l),
    }
    total = sum(parts[k] * weights[k] for k in weights) / sum(weights.values())
    return {"total": round(total, 1), "breakdown": {k: round(v) for k, v in parts.items()}}
