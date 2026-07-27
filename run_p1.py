"""P1 슬라이스 실행기: 수집 → 면적필터 → 통근 → 국토부 저평가·연식 → 최종 후보."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import yaml
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from collectors.naver import collect            # noqa: E402
from collectors import molit                    # noqa: E402
from filters import apply_area_filter, tag_renovated  # noqa: E402
from enrich.commute import geocode, commute_minutes, rush_commute  # noqa: E402
from enrich import amenity                             # noqa: E402
from enrich import naver_review                        # noqa: E402
import score                                           # noqa: E402
import report                                          # noqa: E402
import notify                                          # noqa: E402
import finance                                         # noqa: E402
import history                                         # noqa: E402
import shutil                                          # noqa: E402
from datetime import date                              # noqa: E402


def main():
    cfg = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "config.yaml"), encoding="utf-8"))
    w = cfg["workplace"]
    f = cfg["filters"]
    per_min = cfg.get("rush", {}).get("per_min", 0.05)

    listings, _ = collect(cfg)
    print(f"① 네이버 수집: {len(listings)}건")

    filt = apply_area_filter(listings, cfg)
    print(f"② 전용 {f['area_exclusive_max_m2']}㎡ 이하 필터: {len(filt)}건")

    # 통근시간 (단지별 1회 지오코딩 캐시 — 지역 인식)
    def region_str(l):
        g = l.get("gu", "")
        return f"창원시 {g}" if g.endswith("구") else g
    coord_cache = {}
    enriched = []
    for l in filt:
        key = (l["complex_name"], l.get("gu"))
        if key not in coord_cache:
            q = f"{l['complex_name']} {region_str(l)} {l.get('dong', '')}".strip()
            coord_cache[key] = geocode(q)
        if not coord_cache[key]:
            continue
        l["lng"], l["lat"] = coord_cache[key]
        l["commute_min"] = rush_commute(l["lng"], l["lat"], w["lng"], w["lat"], per_min)
        enriched.append(l)
    passed = [l for l in enriched if l["commute_min"] and l["commute_min"] <= f["max_commute_min"]]
    print(f"③ 통근 ≤{f['max_commute_min']}분: {len(passed)}건")

    # 국토부 실거래 → 저평가율·연식 (시군구별 인덱스 + 매칭 신뢰 검증)
    lawds = [g["lawd"] for g in cfg["regions_gu"]]
    indexes = molit.build_indexes(lawds, months=6)
    n_idx = sum(len(v) for v in indexes.values())
    print(f"④ 국토부 실거래 인덱싱: {len(lawds)}개 시군구 · 단지 {n_idx}곳")
    for l in passed:
        m = molit.match(l, indexes)
        if not m:
            continue
        l["build_year"] = m["build_year"]
        fair = m["fair"]
        if not fair:
            continue
        if l["trade_type"] == "매매":
            uv = round((fair - l["price_manwon"]) / fair * 100, 1)
            if -35 <= uv <= 35:               # 신뢰 범위만 인정(오매칭 차단)
                l["fair"], l["undervalue_pct"] = fair, uv
                l["recent"], l["trend"] = m["recent"], m["trend"]
        else:                                  # 전세
            jr = round(l["price_manwon"] / fair * 100, 1)
            if 40 <= jr <= 110:
                l["fair"], l["jeonse_ratio"] = fair, jr
                l["gap_manwon"] = fair - l["price_manwon"]
                l["recent"], l["trend"] = m["recent"], m["trend"]

    # 연식 결정트리: 35년 초과 제외 / 25년+는 올수리 or 저평가'상'만
    final = []
    for l in passed:
        by = l.get("build_year")
        if by and by <= f["build_year_exclude_before"]:        # 35년 초과
            continue
        if by and by <= f["old_renovate_year"]:                 # 25년+
            if not tag_renovated(l):
                # 비수리 구축: 매매 & 가격메리트 매우 큼(저평가≥old_unreno_undervalue)일 때만, 전세 제외
                ok = l["trade_type"] == "매매" and (l.get("undervalue_pct") or -99) >= f["old_unreno_undervalue"]
                if not ok:
                    continue
        final.append(l)
    print(f"⑤ 연식 규칙 통과(최종 후보): {len(final)}건")

    # R1 다양성: 단지당 대표 1매물 (저평가/전세가율 우선)
    def pref(l):
        return l.get("undervalue_pct") if l.get("undervalue_pct") is not None else -(l.get("jeonse_ratio") or 100)
    reps = {}
    for l in final:
        nm = l["complex_name"]
        if nm not in reps or pref(l) > pref(reps[nm]):
            reps[nm] = l
    reps = sorted(reps.values(), key=pref, reverse=True)[:60]   # 저평가 상위 단지만 보강
    print(f"⑥ 단지 다양성(단지당 1) → 보강 대상 {len(reps)}개 단지")

    # 상권 enrich + 3축 점수화(가격·통근·상권)
    weights = cfg["scoring"]["weights"]
    for l in reps:
        l.update(amenity.enrich(l["lng"], l["lat"]))
        s = score.score_listing(l, weights)
        l["score_total"], l["score_breakdown"] = s["total"], s["breakdown"]

    top = sorted(reps, key=lambda x: -x["score_total"])[:10]
    print("⑦ Top 10 랭킹 완성\n")
    print("── 🏆 Top 10 (종합점수 순) ──")
    for i, l in enumerate(top, 1):
        b = l["score_breakdown"]
        uv, jr = l.get("undervalue_pct"), l.get("jeonse_ratio")
        metric = f"저평가{uv:+.0f}%" if uv is not None else (f"전세가율{jr:.0f}%" if jr is not None else "-")
        flag = "올수리" if tag_renovated(l) else ""
        print(f"#{i:>2} {l['score_total']:>4}점 · {l['complex_name']}({l.get('build_year','?')}) {l['gu']} · "
              f"{l['trade_type']} {l['price_manwon']}만 {metric} · 🚗{l['commute_min']}분 · "
              f"[가{b['price']}/통{b['commute']}/상{b['amenity']}] {flag}")

    today = date.today().isoformat()
    docs_dir = os.path.join(os.path.dirname(__file__), "docs")
    data_dir = os.path.join(os.path.dirname(__file__), "data")

    # ⑧ 부가 데이터: 디딤돌·실거주 후기
    for l in top:
        l["ddimdol"] = finance.estimate(l["price_manwon"], l["trade_type"])
        l["reviews"] = naver_review.fetch_reviews(l["complex_name"], l.get("gu", ""))

    # 변동 하이라이트(신규·인하) + 스냅샷 저장 + 누적 관심 매물
    n_new, n_drop = history.mark_changes(final, os.path.join(data_dir, "snapshot.json"))
    history.save_snapshot(listings, os.path.join(data_dir, "snapshot.json"))
    watchlist = history.update_watchlist(top, os.path.join(data_dir, "watchlist.json"),
                                         today, f["undervalue_high_pct"])
    print(f"⑧ 변동: 신규 {n_new} · 인하 {n_drop} | 누적 관심 {len(watchlist)}건")

    # 차선(near-miss): 충족 < 10일 때만 보수적 완화 — 평소엔 빈 리스트
    near_miss = []  # 충족 충분 시 생략(차선 정책에 따라 확장 가능)

    # ⑨ HTML 리포트 생성 (목업 풀 디자인)
    meta = {
        "date": today, "workplace": w["name"], "n_final": len(final), "n_top": len(top),
        "n_under_high": sum(1 for l in reps if (l.get("undervalue_pct") or 0) >= f["undervalue_high_pct"]),
        "n_new": n_new, "n_drop": n_drop,
        "kakao_js_key": os.environ.get("KAKAO_JS_KEY", ""),
        "has_naver": bool(os.environ.get("NAVER_CLIENT_ID")),
    }
    out = os.path.join(docs_dir, f"{today}.html")
    report.generate(top, near_miss, watchlist, meta, out)
    shutil.copy(out, os.path.join(docs_dir, "index.html"))
    print(f"📄 리포트 생성 완료: docs/{today}.html  (+ index.html)")

    # ⑩ 카카오톡 '나에게 보내기' (Top5 요약 + 1위 매물 링크)
    try:
        summary = notify.build_summary(top, meta)
        link = cfg.get("report_url") or (top[0]["url"] if top else None)
        code, _ = notify.send_to_me(summary, link_url=link, button_title="전체 리포트 보기")
        print(f"📨 카카오톡 발송: {code}")
    except Exception as e:
        print(f"⚠️ 카카오톡 발송 실패: {e}")


if __name__ == "__main__":
    main()
