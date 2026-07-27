"""하드 필터 — 면적(전용 상한), 가격, 연식(태그 기반 1차)."""
from __future__ import annotations

PYEONG = 3.305785  # 1평 = 3.305785㎡


def m2_to_pyeong(m2: float) -> float:
    return m2 / PYEONG if m2 else 0.0


def apply_area_filter(listings, config):
    """전용 ≤ 상한(85㎡)."""
    f = config["filters"]
    out = []
    for l in listings:
        try:
            a2 = float(l.get("area_excl"))      # 전용
        except (TypeError, ValueError):
            continue
        if a2 <= f["area_exclusive_max_m2"]:
            a1 = l.get("area_supply")
            try:
                l["supply_pyeong"] = round(m2_to_pyeong(float(a1)), 1)
            except (TypeError, ValueError):
                l["supply_pyeong"] = round(m2_to_pyeong(a2), 1)  # 공급 정보 없으면 전용 기준
            out.append(l)
    return out


def tag_renovated(listing) -> bool:
    return any("올수리" in t or "리모델링" in t for t in listing.get("tags", []))


def tag_over_25y(listing) -> bool:
    return any("25년이상" in t for t in listing.get("tags", []))
