"""국토교통부 아파트 매매 실거래가 수집 + 단지 매칭(저평가율·연식)."""
from __future__ import annotations
import os
import re
import statistics
from collections import defaultdict
from datetime import date
from xml.etree import ElementTree as ET
import requests

# ⚠️ User-Agent 없으면 WAF가 'Request Blocked'로 차단함 (실측 확인)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
BASE = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"


def recent_yms(n=6):
    d = date.today()
    y, m, out = d.year, d.month, []
    for _ in range(n):
        out.append(f"{y}{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out


def fetch_month(lawd: str, ym: str):
    key = os.environ.get("MOLIT_SERVICE_KEY")
    if not key:
        raise RuntimeError("MOLIT_SERVICE_KEY 미설정")
    r = requests.get(BASE, params={"serviceKey": key, "LAWD_CD": lawd, "DEAL_YMD": ym,
                                    "numOfRows": 1000, "pageNo": 1}, headers=UA, timeout=20)
    items = []
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return items
    for it in root.iter("item"):
        def g(t):
            el = it.find(t)
            return el.text.strip() if el is not None and el.text else ""
        try:
            amount = int(g("dealAmount").replace(",", ""))
            area = float(g("excluUseAr") or 0)
        except ValueError:
            continue
        items.append({
            "apt": g("aptNm"), "area": area, "amount": amount,
            "build_year": int(g("buildYear") or 0),
            "date": f"{g('dealYear')}.{int(g('dealMonth') or 0):02d}.{int(g('dealDay') or 0):02d}",
            "floor": g("floor"), "dong": g("umdNm"),   # 법정동(동 기반 보조매칭용)
        })
    return items


def fetch_trades(lawd_codes, months=6):
    trades = []
    for lawd in lawd_codes:
        for ym in recent_yms(months):
            trades.extend(fetch_month(lawd, ym))
    return trades


def _norm(s: str) -> str:
    return re.sub(r"[\s()]", "", s or "")


def build_index(trades):
    idx = {}
    for t in trades:
        k = _norm(t["apt"])
        if not k:
            continue
        d = idx.setdefault(k, {"build_year": 0, "areas": {}, "dong": ""})
        d["areas"].setdefault(round(t["area"]), []).append((t["amount"], t["date"]))
        if t["build_year"]:
            d["build_year"] = t["build_year"]
        if t.get("dong"):
            d["dong"] = t["dong"]
    return idx


def build_indexes(lawd_codes, months=6):
    """시군구(LAWD)별 실거래 인덱스 {lawd: index}."""
    out = {}
    for lawd in lawd_codes:
        trades = []
        for ym in recent_yms(months):
            trades.extend(fetch_month(lawd, ym))
        out[lawd] = build_index(trades)
    return out


def match(listing, indexes):
    """매물 → {build_year, fair(중위 실거래가), recent[3]}. 같은 시군구 안에서만 매칭."""
    idx = indexes.get(listing.get("lawd")) or {}
    if not idx:
        return None
    nm = _norm(listing["complex_name"])
    if nm in idx:                       # ① 정확히 일치 우선
        key = nm
    else:                               # ② 부분일치는 짧은 이름 길이 ≥4자만(흔한 단명 오매칭 방지)
        cands = [k for k in idx if (k in nm or nm in k) and min(len(k), len(nm)) >= 4]
        key = max(cands, key=len) if cands else None
    if not key:                         # ③ 동(洞) 기반 보조매칭 — 같은 법정동 안에서만 부분일치(짧은 이름 안전)
        dong = _norm(listing.get("dong") or "")
        if dong and len(nm) >= 2:
            cands = [k for k, v in idx.items()
                     if _norm(v.get("dong", "")) == dong and (k in nm or nm in k)]
            key = max(cands, key=len) if cands else None
    if not key:
        return None
    d = idx[key]
    try:
        a2 = round(float(listing["area_excl"]))
    except (TypeError, ValueError):
        return {"build_year": d["build_year"], "fair": None, "recent": []}
    pool = [(amt, dt) for ar, lst in d["areas"].items() if abs(ar - a2) <= 3 for (amt, dt) in lst]
    fair = int(statistics.median([a for a, _ in pool])) if pool else None
    recent = sorted(pool, key=lambda x: x[1], reverse=True)[:3]
    return {"build_year": d["build_year"], "fair": fair, "recent": recent, "trend": _trend(pool)}


def _trend(pool):
    """월별 중위 실거래가 추이 (최근 6개월)."""
    by_month = defaultdict(list)
    for amt, dt in pool:
        by_month[dt[:7]].append(amt)   # 'YYYY.MM'
    months = sorted(by_month)[-6:]
    return [{"month": m, "median": int(statistics.median(by_month[m]))} for m in months]
