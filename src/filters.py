"""하드 필터 — 면적(공급 평수 범위), 가격, 연식(태그 기반 1차)."""
from __future__ import annotations

PYEONG = 3.305785  # 1평 = 3.305785㎡


def m2_to_pyeong(m2: float) -> float:
    return m2 / PYEONG if m2 else 0.0


def apply_area_filter(listings, config):
    """공급 평수 범위 필터 (기본 25~38평)."""
    f = config["filters"]
    pmin = f["supply_pyeong_min"]
    pmax = f["supply_pyeong_max"]
    out = []
    for l in listings:
        try:
            a1 = float(l.get("area_supply"))    # 공급(㎡)
        except (TypeError, ValueError):
            continue
        supply_py = m2_to_pyeong(a1)
        if pmin <= supply_py < pmax + 1:        # 25 ≤ 공급평 < 39 (25~38평대)
            l["supply_pyeong"] = round(supply_py, 1)
            try:
                l["excl_pyeong"] = round(m2_to_pyeong(float(l.get("area_excl"))), 1)
            except (TypeError, ValueError):
                l["excl_pyeong"] = None
            out.append(l)
    return out


def tag_renovated(listing) -> bool:
    return any("올수리" in t or "리모델링" in t for t in listing.get("tags", []))


def tag_over_25y(listing) -> bool:
    return any("25년이상" in t for t in listing.get("tags", []))
