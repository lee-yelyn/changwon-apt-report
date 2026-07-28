"""Top 10 → HTML 리포트 (Apple 디자인 풀버전: 상세·지도·리뷰·차선·누적·목록)."""
from __future__ import annotations
import glob
import html
import json
import os
import re


def fmt_price(man):
    if man is None:
        return "-"
    eok, rest = divmod(int(man), 10000)
    if eok and rest:
        return f"{eok}억 {rest:,}"
    if eok:
        return f"{eok}억"
    return f"{rest:,}만"


def _metric(l):
    uv, jr = l.get("undervalue_pct"), l.get("jeonse_ratio")
    if uv is not None:
        cls = "good" if uv >= 10 else ("mid" if uv >= 3 else "")
        return f'<span class="uv {cls}">실거래 대비 {uv:+.0f}%</span>'
    if jr is not None:
        return f'<span class="uv">전세가율 {jr:.0f}%</span>'
    return '<span class="uv mut">실거래 매칭 없음</span>'


def _badges(l):
    out = []
    bset = l.get("badges", [])
    if "신규" in bset:
        out.append('<span class="badge new">🆕 신규</span>')
    if "가격인하" in bset:
        d = l.get("price_drop")
        out.append(f'<span class="badge down">🔽 인하 {("-"+format(d,",")+"만") if d else ""}</span>')
    if (l.get("undervalue_pct") or 0) >= 10:
        out.append('<span class="badge good">🔥 저평가 上</span>')
    if any("올수리" in t or "리모델링" in t for t in l.get("tags", [])):
        out.append('<span class="badge warn">올수리</span>')
    return "".join(out)


def _bar(label, v):
    return (f'<div class="sbar"><span class="lab">{label}</span>'
            f'<span class="track"><span class="fill" style="width:{v}%"></span></span>'
            f'<span class="sv">{v}</span></div>')


def _trades_table(l):
    rows = ""
    for amt, dt in l.get("recent", [])[:3]:
        diff = round((l["price_manwon"] - amt) / amt * 100, 1) if amt else 0
        col = "var(--good)" if diff <= 0 else "#b23b3b"
        rows += f"<tr><td>{dt}</td><td>{fmt_price(amt)}</td><td style='color:{col}'>{diff:+.0f}%</td></tr>"
    if not rows:
        return ""
    return ("<h4>호가 분석 · 동일평형 최근 실거래</h4>"
            "<table class='trades'><tr><th>거래일</th><th>거래가</th><th>vs 호가</th></tr>"
            f"{rows}</table>")


def _ddimdol(l):
    d = l.get("ddimdol")
    if not d:
        return ""
    rows = (f"<div class='ddrow'>· <b>일반</b> 디딤돌 · 대출 <b>{fmt_price(d['loan'])}</b> "
            f"(LTV {d['ltv_pct']}%) · 필요현금 약 <b>{fmt_price(d['cash'])}</b></div>")
    if d.get("first_loan") is not None:
        rows += (f"<div class='ddrow'>· <b>생애최초</b>(생애 첫 주택) · 대출 <b>{fmt_price(d['first_loan'])}</b> "
                 f"(LTV {d['first_ltv_pct']}%) · 필요현금 약 <b>{fmt_price(d['first_cash'])}</b></div>")
    return (f"<div class='ddim'><b>디딤돌 대출 추정</b>{rows}"
            f"<div class='fine'>※ 가정치. 생애최초=무주택 세대의 생애 첫 주택구입(LTV·한도 우대). "
            f"실제 한도·금리·소득/주택가격·무주택 요건은 조건별 상이 → 기금e든든 등에서 별도 확인.</div></div>")


def _trend(l):
    t = l.get("trend") or []
    if len(t) < 2:
        return ""
    vals = [x["median"] for x in t]
    lo, hi = min(vals), max(vals)
    bars = ""
    for x in t:
        h = 18 + (40 * (x["median"] - lo) / (hi - lo) if hi > lo else 20)
        bars += (f"<div class='tb'><div class='tbar' style='height:{h:.0f}px'></div>"
                 f"<div class='tm'>{x['month'][2:].replace('.', '/')}</div></div>")
    arrow = "▼" if vals[-1] < vals[0] else ("▲" if vals[-1] > vals[0] else "→")
    return (f"<h4 class='mt'>단지 6개월 시세 추이 {arrow}</h4>"
            f"<div class='spark'>{bars}</div>"
            f"<div class='fine'>{fmt_price(vals[0])} → {fmt_price(vals[-1])}</div>")


def _gap(l):
    if l.get("trade_type") == "전세" and l.get("gap_manwon") is not None:
        return (f"<div class='fine' style='margin-top:6px'>전세가율 {l.get('jeonse_ratio',0):.0f}% · "
                f"매매-전세 갭 약 <b>{fmt_price(l['gap_manwon'])}</b></div>")
    return ""


def _map(i, l):
    lat, lng = l.get("lat"), l.get("lng")
    markers = html.escape(json.dumps(l.get("markers", []), ensure_ascii=False))
    name = html.escape(l["complex_name"])
    klink = f"https://map.kakao.com/link/map/{name},{lat},{lng}"
    return (f"<h4 class='mt'>주변 인프라 · 지도</h4>"
            f"<div class='map' id='map{i}' data-lat='{lat}' data-lng='{lng}' data-markers=\"{markers}\">"
            f"<a class='mapfb' href='{klink}' target='_blank'>🗺️ 카카오맵에서 보기</a></div>")


def _infra(l):
    ns = l.get("nearest_school")
    school = f"{html.escape(ns['name'])} {ns['dist_m']}m" if ns else "-"
    return (f"<div class='infra'>🛒 마트 <b>{l.get('mart',0)}</b> · 🏥 병원 <b>{l.get('hospital',0)}</b> · "
            f"🏫 <b>{school}</b> · 🧸 어린이집 <b>{l.get('daycare',0)}</b></div>")


def _reviews(l, has_naver):
    revs = l.get("reviews")
    if revs is None:
        msg = ("네이버 검색 API 키 연동 시 실거주 후기가 표시돼요." if not has_naver
               else "후기 데이터 준비 중")
        return f"<h4 class='mt'>실거주자 리뷰</h4><div class='fine'>{msg}</div>"
    if not revs:
        return "<h4 class='mt'>실거주자 리뷰</h4><div class='fine'>관련 후기를 찾지 못했어요.</div>"
    items = ""
    for r in revs:
        items += (f"<div class='rev'><div class='rtop'><b>{html.escape(r['title'])[:34]}</b>"
                  f"<span class='rsrc'>{r['src']}</span></div>"
                  f"<div class='rq'>{html.escape(r['desc'])} "
                  f"<a href='{r['link']}' target='_blank'>원문</a></div></div>")
    return f"<h4 class='mt'>실거주자 리뷰 (네이버 블로그·카페)</h4>{items}"


def _card(i, l, meta):
    name = html.escape(l.get("complex_name", "?"))
    by = l.get("build_year")
    age = f"·{2026 - by}년차" if isinstance(by, int) else ""
    metaline = " · ".join(filter(None, [
        f"{l.get('building') or ''} {l.get('floor') or ''}".strip(),
        l.get("direction") or "",
        f"전용 {l.get('area_excl')}㎡({l.get('supply_pyeong')}평)",
        f"{by}년{age}" if by else "",
    ]))
    b = l.get("score_breakdown", {})
    ns = l.get("nearest_school")
    sline = f"🏫 {html.escape(ns['name'])} {ns['dist_m']}m" if ns else "🏫 -"
    naver = l.get("url", "#")
    region = html.escape(f"{l.get('gu','')} {l.get('dong','')}".strip())
    detail = (f"<div class='detail' id='detail{i}'>"
              f"{_trades_table(l)}{_ddimdol(l)}{_gap(l)}{_map(i, l)}{_infra(l)}"
              f"{_reviews(l, meta.get('has_naver'))}{_trend(l)}</div>")
    return f"""
    <article class="card">
      <div class="tline"><span class="rank">{i}</span><span class="cname">{name}</span>
        <span class="score">{l.get('score_total','')}점</span></div>
      <div class="badges">{_badges(l)}</div>
      <div class="region">{region}</div>
      <div class="meta">{html.escape(metaline)}</div>
      <div class="price"><span class="p">{l.get('trade_type','')} {fmt_price(l.get('price_manwon'))}</span>{_metric(l)}</div>
      <div class="ana">실거래 중위 {fmt_price(l.get('fair'))}</div>
      <div class="scores">{_bar('가격', b.get('price',0))}{_bar('통근', b.get('commute',0))}
        {_bar('상권', b.get('amenity',0))}{_bar('육아', b.get('childcare',0))}</div>
      <div class="facts">🚗 통근 <b>{l.get('commute_min','?')}분</b> · 🛒 마트 <b>{l.get('mart',0)}</b> · 🏥 병원 <b>{l.get('hospital',0)}</b> · {sline} · 🧸 어린이집 <b>{l.get('daycare',0)}</b></div>
      <div class="actions"><a class="btn btn-pri" href="{naver}" target="_blank">네이버 매물</a>
        <a class="btn btn-text" id="tgl{i}" onclick="toggle({i})">상세 ▼</a></div>
      {detail}
    </article>"""


def _board(watchlist):
    if not watchlist:
        return ""
    wl = sorted(watchlist, key=lambda x: -(x.get("score") or 0))[:8]
    lo_price = min((x["current_price"] for x in wl), default=0)
    hi_score = max((x.get("score") or 0 for x in wl), default=0)
    lo_comm = min((x.get("commute") or 99 for x in wl), default=99)
    rows = ""
    for x in wl:
        st = x.get("status", "추적중")
        stc = {"추적중": "track", "가격인하": "down"}.get(st, "track")
        drop = x["first_price"] - x["current_price"]
        chg = (f"<span class='dn'>▼{drop:,}만</span>" if drop > 0 else "")
        m1 = "best" if (x.get("score") or 0) == hi_score else ""
        m2 = "bestg" if x["current_price"] == lo_price else ""
        m3 = "best" if (x.get("commute") or 99) == lo_comm else ""
        rows += f"""
        <div class="cmprow">
          <div class="ch"><span class="cnm">{html.escape(x['complex'])}</span>
            <span class="csz">{x.get('area','')}㎡</span><span class="st {stc}">{st}·{x.get('days',1)}일째</span></div>
          <div class="cmet">
            <div class="cm {m1}"><div class="cv">{round(x.get('score') or 0)}</div><div class="cl">종합</div></div>
            <div class="cm"><div class="cv">{('+%d%%'%x['undervalue']) if x.get('undervalue') is not None else '-'}</div><div class="cl">저평가</div></div>
            <div class="cm {m3}"><div class="cv">{round(x.get('commute') or 0)}분</div><div class="cl">통근</div></div>
            <div class="cm {m2}"><div class="cv">{fmt_price(x['current_price'])}</div><div class="cl">현재가</div></div>
          </div>
          <div class="cchg">첫등장 {x['first_date'][5:]} <span class="ol">{fmt_price(x['first_price'])}</span>
            → <b>{fmt_price(x['current_price'])}</b> {chg}</div>
        </div>"""
    return (f"<div class='sec'>⭐ 누적 관심 매물 비교</div>"
            f"<div class='hint'>매일 ‘최선호’로 뽑힌 매물을 누적·추적</div>{rows}")


def _archive_dates(out_dir, today):
    dates = set()
    for p in glob.glob(os.path.join(out_dir, "*.html")):
        m = re.match(r"(\d{4}-\d{2}-\d{2})", os.path.basename(p))
        if m:
            dates.add(m.group(1))
    dates.add(today)
    return sorted(dates, reverse=True)


def _sheet(out_dir, meta):
    rows = ""
    for d in _archive_dates(out_dir, meta["date"]):
        today = " today" if d == meta["date"] else ""
        label = ("오늘 · " + d[5:]) if d == meta["date"] else d
        rows += (f"<a class='drow{today}' href='{d}.html'><div><b>{label}</b>"
                 f"<div class='dsm'>창원 통근권 Top{meta['n_top']} · 저평가 {meta['n_under_high']}</div></div><i>›</i></a>")
    return (f"<div id='sheetbg' class='sheetbg' onclick='closeSheet()'></div>"
            f"<div id='sheet' class='sheet'><div class='handle'></div>"
            f"<div class='sheeth'><span>날짜별 보고서</span><span class='x' onclick='closeSheet()'>닫기</span></div>"
            f"<div class='slist'>{rows}</div></div>")


CSS = """
:root{--blue:#0066cc;--ink:#1d1d1f;--mut:#7a7a7a;--mut2:#333;--hair:#e0e0e0;--div:#f0f0f0;
--canvas:#fff;--parch:#f5f5f7;--pearl:#fafafc;--tile:#272729;--good:#1d7a3e;--goodbg:#eaf5ec;--warn:#9a6b00;--warnbg:#fdf4e3;
--font:"SF Pro Text",system-ui,-apple-system,BlinkMacSystemFont,"Inter",sans-serif;}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font);background:var(--parch);color:var(--ink);font-size:17px;line-height:1.47;letter-spacing:-.011em;-webkit-font-smoothing:antialiased}
.wrap{max-width:560px;margin:0 auto;padding:0 16px 50px}
.gnav{background:#000;color:#fff;height:46px;display:flex;align-items:center;justify-content:space-between;padding:0 18px}
.gnav b{font-size:13px;font-weight:600}.gnav .listbtn{background:#222;color:#fff;border:0;border-radius:9999px;padding:7px 14px;font-size:13px;font-weight:600;font-family:var(--font);cursor:pointer}
.hero{padding:28px 2px 16px}.eyebrow{color:var(--mut);font-size:13px}
.hero h1{font-size:29px;font-weight:600;letter-spacing:-.02em;line-height:1.12;margin:5px 0 15px}
.stats{display:flex;gap:9px}.stat{flex:1;background:var(--canvas);border:1px solid var(--hair);border-radius:15px;padding:14px;text-align:center}
.stat .n{font-size:24px;font-weight:600;letter-spacing:-.02em}.stat .n.b{color:var(--blue)}.stat .n.g{color:var(--good)}.stat .l{font-size:11px;color:var(--mut);margin-top:5px}
.oneliner{background:var(--tile);color:#fff;border-radius:15px;padding:14px 16px;margin-top:11px;display:flex;gap:7px;align-items:center;flex-wrap:wrap}
.oneliner b{font-size:14px}.chip{font-size:12px;font-weight:600;border-radius:9999px;padding:4px 10px}.chip.n{background:rgba(41,151,255,.2);color:#7cc0ff}.chip.d{background:rgba(255,255,255,.15);color:#fff}
.sec{margin:24px 2px 4px;font-size:20px;font-weight:600;letter-spacing:-.015em}.hint{color:var(--mut);font-size:12px;margin:0 2px 10px}
.card{background:var(--canvas);border:1px solid var(--hair);border-radius:18px;padding:17px;margin-bottom:12px}
.card.nm{background:var(--parch);border-style:dashed}
.tline{display:flex;align-items:center;gap:9px}.rank{font-size:13px;font-weight:600;color:#fff;background:var(--ink);border-radius:9999px;min-width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center}
.cname{font-size:18px;font-weight:600;letter-spacing:-.015em}.score{margin-left:auto;font-size:14px;color:var(--blue);font-weight:600}
.badges{display:flex;gap:5px;flex-wrap:wrap;margin-top:8px}.badges:empty{display:none}
.badge{font-size:12px;font-weight:600;border-radius:9999px;padding:4px 9px}.badge.good{background:var(--goodbg);color:var(--good)}.badge.warn{background:var(--warnbg);color:var(--warn)}.badge.new{background:#e7f0fb;color:var(--blue)}.badge.down{background:var(--goodbg);color:var(--good)}
.region{font-size:12px;color:var(--blue);margin-top:8px}.meta{font-size:12.5px;color:var(--mut);margin-top:3px}
.price{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-top:11px}.price .p{font-size:22px;font-weight:600;letter-spacing:-.02em}
.uv{font-size:13px;font-weight:600;color:var(--mut2)}.uv.good{color:var(--good)}.uv.mid{color:var(--blue)}.uv.mut{color:var(--mut);font-weight:400}
.ana{font-size:12px;color:var(--mut);margin-top:3px}
.scores{display:grid;grid-template-columns:1fr 1fr;gap:7px 16px;margin-top:13px}
.sbar{display:flex;align-items:center;gap:8px}.sbar .lab{font-size:12px;color:var(--mut2);width:28px}
.track{flex:1;height:5px;background:var(--div);border-radius:9999px;overflow:hidden}.fill{height:100%;background:var(--blue)}
.sbar .sv{font-size:11px;color:var(--mut);width:20px;text-align:right}
.facts{font-size:12.5px;color:var(--mut2);margin-top:12px;border-top:1px solid var(--div);padding-top:11px}.facts b{color:var(--ink);font-weight:600}
.actions{display:flex;gap:8px;margin-top:13px}
.btn{font-size:14px;border-radius:9999px;padding:9px 16px;text-decoration:none;border:1px solid transparent;cursor:pointer;letter-spacing:-.01em;transition:transform .08s}.btn:active{transform:scale(.96)}
.btn-pri{background:var(--blue);color:#fff}.btn-text{background:transparent;color:var(--blue)}
.detail{display:none;margin-top:14px;border-top:1px solid var(--div);padding-top:14px}
.detail h4{font-size:13.5px;font-weight:600;margin:0 0 8px}.detail h4.mt{margin-top:16px}
table.trades{width:100%;border-collapse:collapse;font-size:12px}table.trades th,table.trades td{text-align:left;padding:5px 4px;border-bottom:1px solid var(--div);color:var(--mut2)}table.trades th{color:var(--mut);font-weight:600}
.ddim{background:var(--parch);border-radius:11px;padding:12px;font-size:12.5px;margin-top:9px;line-height:1.6}.ddim .fine{color:var(--mut);font-size:11px;margin-top:3px}.fine{color:var(--mut);font-size:11.5px}
.map{position:relative;height:190px;border-radius:13px;overflow:hidden;border:1px solid var(--hair);background:repeating-linear-gradient(0deg,#eef0f3 0 33px,#e7eaee 33px 34px),repeating-linear-gradient(90deg,#eef0f3 0 33px,#e7eaee 33px 34px);display:flex;align-items:center;justify-content:center}
.mapfb{font-size:13px;color:var(--blue);background:rgba(255,255,255,.9);padding:8px 14px;border-radius:9999px;text-decoration:none;border:1px solid var(--hair)}
.infra{font-size:12.5px;color:var(--mut2);margin-top:10px;line-height:1.7}.infra b{color:var(--ink);font-weight:600}
.rev{border-top:1px solid var(--div);padding:9px 0 2px}.rtop{display:flex;gap:7px;align-items:center}.rtop b{font-size:12.5px}.rsrc{font-size:11px;color:var(--mut);margin-left:auto}.rq{font-size:12px;color:var(--mut2);margin-top:3px;line-height:1.5}.rq a{color:var(--blue)}
.spark{display:flex;align-items:flex-end;gap:8px;height:62px;margin-top:4px}.tb{flex:1;text-align:center}.tbar{background:var(--blue);border-radius:3px 3px 0 0;opacity:.85}.tm{font-size:9px;color:var(--mut);margin-top:3px}
.cmprow{background:var(--canvas);border:1px solid var(--hair);border-radius:15px;padding:13px;margin-bottom:10px}
.ch{display:flex;align-items:center;gap:7px;flex-wrap:wrap}.cnm{font-size:15px;font-weight:600}.csz{font-size:11.5px;color:var(--mut)}
.st{font-size:11px;font-weight:600;border-radius:9999px;padding:3px 9px;margin-left:auto}.st.track{background:#e7f0fb;color:var(--blue)}.st.down{background:var(--goodbg);color:var(--good)}
.cmet{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:11px}
.cm{background:var(--parch);border-radius:9px;padding:8px 3px;text-align:center}.cm .cv{font-size:14px;font-weight:600}.cm .cl{font-size:9.5px;color:var(--mut);margin-top:3px}
.cm.best{background:#eaf2fc}.cm.best .cv{color:var(--blue)}.cm.bestg{background:var(--goodbg)}.cm.bestg .cv{color:var(--good)}
.cchg{display:flex;align-items:center;gap:7px;margin-top:11px;font-size:12px;color:var(--mut);border-top:1px solid var(--div);padding-top:10px;flex-wrap:wrap}.cchg b{color:var(--ink)}.cchg .ol{text-decoration:line-through}.cchg .dn{color:var(--good);font-weight:600}
.sheetbg{position:fixed;inset:0;background:rgba(0,0,0,.35);opacity:0;pointer-events:none;transition:.25s;z-index:40}.sheetbg.open{opacity:1;pointer-events:auto}
.sheet{position:fixed;left:0;right:0;bottom:0;max-width:560px;margin:0 auto;background:var(--canvas);border-radius:22px 22px 0 0;z-index:41;transform:translateY(105%);transition:transform .32s cubic-bezier(.32,.72,0,1);max-height:80%;display:flex;flex-direction:column;padding-bottom:18px}.sheet.open{transform:translateY(0)}
.handle{width:38px;height:5px;background:#d0d0d5;border-radius:9999px;margin:8px auto 2px}
.sheeth{display:flex;justify-content:space-between;padding:10px 20px 12px;font-size:18px;font-weight:600;border-bottom:1px solid var(--div)}.sheeth .x{font-size:14px;font-weight:400;color:var(--blue);cursor:pointer}
.slist{overflow-y:auto;padding:4px 12px}.drow{display:flex;align-items:center;gap:10px;padding:13px 10px;border-bottom:1px solid var(--div);text-decoration:none;color:var(--ink)}.drow b{font-size:15px;font-weight:600}.drow .dsm{font-size:11.5px;color:var(--mut);margin-top:3px}.drow i{margin-left:auto;color:#c5c5ca;font-style:normal;font-size:20px}.drow.today b{color:var(--blue)}
footer{max-width:560px;margin:24px auto 0;padding:22px 16px 50px;font-size:11.5px;color:var(--mut);line-height:1.7}footer b{color:var(--mut2)}
"""

JS = """
function toggle(i){var d=document.getElementById('detail'+i);var o=d.style.display==='block';
d.style.display=o?'none':'block';document.getElementById('tgl'+i).textContent=o?'상세 ▼':'접기 ▲';if(!o)initMap(i);}
var _m={};function initMap(i){if(_m[i]||!window.kakao||!window.kakao.maps||!kakao.maps.Map)return;
var el=document.getElementById('map'+i);if(!el)return;var lat=parseFloat(el.dataset.lat),lng=parseFloat(el.dataset.lng);
if(isNaN(lat))return;var ctr=new kakao.maps.LatLng(lat,lng);var map=new kakao.maps.Map(el,{center:ctr,level:4});
new kakao.maps.Marker({map:map,position:ctr});
setTimeout(function(){map.relayout();map.setCenter(ctr);},60);
try{JSON.parse(el.dataset.markers||'[]').forEach(function(p){var mk=new kakao.maps.Marker({map:map,position:new kakao.maps.LatLng(p.y,p.x)});
var iw=new kakao.maps.InfoWindow({content:'<div style=\\'padding:3px 7px;font-size:11px\\'>'+p.name+'</div>'});
kakao.maps.event.addListener(mk,'mouseover',function(){iw.open(map,mk)});kakao.maps.event.addListener(mk,'mouseout',function(){iw.close()});});}catch(e){}_m[i]=map;}
function openSheet(){document.getElementById('sheet').classList.add('open');document.getElementById('sheetbg').classList.add('open');}
function closeSheet(){document.getElementById('sheet').classList.remove('open');document.getElementById('sheetbg').classList.remove('open');}
"""


def generate(top, near_miss, watchlist, meta, out_path):
    out_dir = os.path.dirname(out_path)
    cards = "".join(_card(i, l, meta) for i, l in enumerate(top, 1))
    nm_section = ""
    if near_miss:
        nmc = "".join(_card("차", l, meta) for l in near_miss)
        nm_section = f"<div class='sec'>🔶 차선 (근접) 매물</div><div class='hint'>통근만 소폭 완화 · 돈·디딤돌·연식 유지</div>{nmc}"
    board = _board(watchlist)
    sheet = _sheet(out_dir, meta)
    js_key = meta.get("kakao_js_key", "")
    sdk = (f'<script src="//dapi.kakao.com/v2/maps/sdk.js?appkey={js_key}&autoload=false"></script>'
           '<script>if(window.kakao&&kakao.maps){kakao.maps.load(function(){});}</script>') if js_key else ""
    doc = f"""<!DOCTYPE html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>창원 통근권 아파트 리포트 · {meta['date']}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<nav class="gnav"><b>창원 통근권 아파트 리포트</b><button class="listbtn" onclick="openSheet()">☰ 목록</button></nav>
<div class="wrap">
  <section class="hero">
    <div class="eyebrow">{html.escape(meta['workplace'])} 통근 30분권 · 매매 ≤4.5억 · 공급 25~38평</div>
    <h1>오늘의 추천<br>아파트 Top {meta['n_top']}</h1>
    <div class="stats">
      <div class="stat"><div class="n">{meta['n_final']}</div><div class="l">조건 통과</div></div>
      <div class="stat"><div class="n b">{meta['n_top']}</div><div class="l">Top 추천</div></div>
      <div class="stat"><div class="n g">{meta['n_under_high']}</div><div class="l">저평가 ‘상’</div></div>
    </div>
    <div class="oneliner"><b>오늘의 한 줄</b>
      <span class="chip n">🆕 신규 {meta.get('n_new',0)}</span>
      <span class="chip d">🔽 인하 {meta.get('n_drop',0)}</span></div>
  </section>
  <div class="sec">🏆 매력도 Top {meta['n_top']}</div>
  {cards}
  {nm_section}
  {board}
</div>
{sheet}
<footer><b>출처</b> · 매물: 네이버부동산 / 실거래: 국토교통부 / 통근·지도·인프라: 카카오 / 후기: 네이버 검색.<br>
<b>면책</b> · 공개 데이터 자동 분석 참고자료. 호가·매물은 변동·허위 가능. <b>반드시 현장확인·중개사 상담 후 판단하세요.</b> 가격·점수·디딤돌은 추정치.<br>
생성 {meta['date']} · 창원 통근권(성산·의창) 자동 분석.</footer>
{sdk}
<script>{JS}</script>
</body></html>"""
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    return out_path
