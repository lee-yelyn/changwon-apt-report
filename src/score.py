"""3축 점수화: 가격/저평가 · 통근 · 상권 (가중합 0~100)."""
from __future__ import annotations


def _norm(v, lo, hi):
    if hi == lo:
        return 0.0
    return max(0.0, min(100.0, (v - lo) / (hi - lo) * 100))


def price_score(l):
    if l.get("undervalue_pct") is not None:        # 매매: 실거래 대비 저평가
        return _norm(l["undervalue_pct"], -5, 25)
    if l.get("jeonse_ratio") is not None:          # 전세: 전세가율 낮을수록↑
        return _norm(95 - l["jeonse_ratio"], 0, 35)
    return 45.0                                     # 실거래 매칭 없음 → 중립


def commute_score(l):
    cm = l.get("commute_min")
    return _norm(30 - cm, 0, 25) if cm is not None else 0.0   # 5분↓=만점, 30분=0


def amenity_score(l):
    return _norm(l.get("mart", 0) + l.get("hospital", 0), 3, 60)   # 마트+병원(3~60)


def score_listing(l, weights):
    parts = {
        "price": price_score(l),
        "commute": commute_score(l),
        "amenity": amenity_score(l),
    }
    total = sum(parts[k] * weights[k] for k in weights) / sum(weights.values())
    return {"total": round(total, 1), "breakdown": {k: round(v) for k, v in parts.items()}}
