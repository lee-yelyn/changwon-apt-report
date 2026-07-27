"""전일 스냅샷 비교(변동 하이라이트) + 누적 관심 매물(watchlist)."""
from __future__ import annotations
import json
import os


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def mark_changes(listings, snap_path):
    """오늘 매물에 신규/가격인하 배지 부여 (전일 스냅샷 대비)."""
    prev = _load(snap_path)  # {article_no: price_manwon}
    n_new = n_drop = 0
    for l in listings:
        no = str(l.get("article_no") or "")
        badges = l.setdefault("badges", [])
        if not no:
            continue
        if no not in prev:
            badges.append("신규")
            n_new += 1
        elif l["price_manwon"] < prev[no]:
            l["price_drop"] = prev[no] - l["price_manwon"]
            badges.append("가격인하")
            n_drop += 1
    return n_new, n_drop


def save_snapshot(listings, snap_path):
    snap = {str(l["article_no"]): l["price_manwon"]
            for l in listings if l.get("article_no")}
    _save(snap_path, snap)


def update_watchlist(top, wl_path, today, high_pct=10):
    """최선호(저평가 '상' 또는 상위권) 매물을 누적·추적."""
    wl = _load(wl_path)  # {complex_name: {...}}
    seen_today = set()
    for l in top:
        uv = l.get("undervalue_pct")
        # 최선호 기준: 저평가 '상'(>=high_pct) 또는 종합 상위(점수>=75)
        if not ((uv is not None and uv >= high_pct) or l.get("score_total", 0) >= 75):
            continue
        key = l["complex_name"]
        seen_today.add(key)
        price = l["price_manwon"]
        if key in wl:
            e = wl[key]
            e["current_price"] = price
            e["last_seen"] = today
            e["days"] = e.get("days", 1) + (0 if e.get("last_date") == today else 1)
            e["last_date"] = today
            e["status"] = "가격인하" if price < e["first_price"] else "추적중"
            e["score"] = max(e.get("score", 0), l.get("score_total", 0))
        else:
            wl[key] = {
                "complex": key, "first_date": today, "last_seen": today, "last_date": today,
                "first_price": price, "current_price": price, "days": 1, "status": "추적중",
                "score": l.get("score_total", 0), "undervalue": uv, "commute": l.get("commute_min"),
                "trade_type": l.get("trade_type"), "area": l.get("area_excl"),
                "url": l.get("url"),
            }
    # 오늘 Top에 없던 기존 항목: 거래완료 추정(선택) — 여기선 상태만 유지
    _save(wl_path, wl)
    return list(wl.values())
