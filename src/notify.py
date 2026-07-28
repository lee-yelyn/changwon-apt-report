"""카카오톡 '나에게 보내기' — refresh_token으로 access_token 갱신 후 메모 전송."""
from __future__ import annotations
import json
import os
from datetime import date
import requests

TOKEN_URL = "https://kauth.kakao.com/oauth/token"
MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"


def _fmt_price(man):
    if man is None:
        return "-"
    eok, rest = divmod(int(man), 10000)
    if eok and rest:
        return f"{eok}억{rest:,}"
    if eok:
        return f"{eok}억"
    return f"{rest:,}만"


def get_access_token():
    r = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "client_id": os.environ["KAKAO_REST_KEY"],
        "client_secret": os.environ.get("KAKAO_CLIENT_SECRET", ""),
        "refresh_token": os.environ["KAKAO_REFRESH_TOKEN"],
    }, timeout=15)
    return r.json().get("access_token")


def send_to_me(text, link_url=None, button_title="매물 보기"):
    token = get_access_token()
    if not token:
        raise RuntimeError("access_token 발급 실패 (refresh_token 확인)")
    fallback = link_url or "https://m.land.naver.com"
    tmpl = {
        "object_type": "text",
        "text": text[:1000],          # 카카오 텍스트 템플릿 — 200자 초과 허용됨
        "link": {"web_url": fallback, "mobile_web_url": fallback},
    }
    if link_url:
        tmpl["button_title"] = button_title
    r = requests.post(MEMO_URL, headers={"Authorization": f"Bearer {token}"},
                      data={"template_object": json.dumps(tmpl, ensure_ascii=False)}, timeout=15)
    return r.status_code, r.json()


def send_listings(top, report_url, meta, n=5):
    """리스트 템플릿 — Top n 매물을 각각 개별 네이버 링크로 발송."""
    token = get_access_token()
    if not token:
        raise RuntimeError("access_token 발급 실패 (refresh_token 확인)")
    wd = "월화수목금토일"[date.fromisoformat(meta["date"]).weekday()]
    rurl = report_url or "https://m.land.naver.com"
    contents = []
    for i, l in enumerate(top[:n], 1):
        uv, jr = l.get("undervalue_pct"), l.get("jeonse_ratio")
        m = f"저평가{uv:+.0f}%" if uv is not None else (f"전세{jr:.0f}%" if jr else "")
        desc = " · ".join(filter(None, [
            f"{l.get('gu','')}", f"🚗{l.get('commute_min','?')}분", m or None,
        ]))
        lurl = l.get("url") or rurl
        contents.append({
            "title": f"{i}. {l['complex_name']} {_fmt_price(l['price_manwon'])}",
            "description": desc,
            "link": {"web_url": lurl, "mobile_web_url": lurl},
        })
    tmpl = {
        "object_type": "list",
        "header_title": f"🏠 창원 통근권 아파트 Top{min(n, len(top))} ({meta['date'].replace('-', '.')} {wd})",
        "header_link": {"web_url": rurl, "mobile_web_url": rurl},
        "contents": contents,
        "buttons": [{"title": "전체 리포트 보기", "link": {"web_url": rurl, "mobile_web_url": rurl}}],
    }
    r = requests.post(MEMO_URL, headers={"Authorization": f"Bearer {token}"},
                      data={"template_object": json.dumps(tmpl, ensure_ascii=False)}, timeout=15)
    return r.status_code, r.json()


def build_summary(top, meta, n=5):
    """요약 + 추천매물(금액·통근·저평가) + 페이지 링크. 200자 제한 없음."""
    wd = "월화수목금토일"[date.fromisoformat(meta["date"]).weekday()]
    lines = [f"📅 {meta['date'].replace('-', '.')} ({wd}) · 창원 통근권 아파트 리포트"]

    # 요약
    summ = f"🔎 오늘 {meta.get('n_final', '?')}건 분석"
    extra = []
    if meta.get("n_under_high"):
        extra.append(f"저평가 上 {meta['n_under_high']}건")
    if meta.get("n_new"):
        extra.append(f"신규 {meta['n_new']}건")
    if meta.get("n_drop"):
        extra.append(f"인하 {meta['n_drop']}건")
    if extra:
        summ += " · " + " · ".join(extra)
    lines.append(summ)

    # 추천 매물
    lines.append(f"\n🏆 추천 Top{min(n, len(top))}")
    for i, l in enumerate(top[:n], 1):
        uv, jr = l.get("undervalue_pct"), l.get("jeonse_ratio")
        m = f"저평가{uv:+.0f}%" if uv is not None else (f"전세{jr:.0f}%" if jr else "")
        by = l.get("build_year")
        seg = [f"{l.get('trade_type', '')} {_fmt_price(l['price_manwon'])}",
               f"🚗{l['commute_min']:.0f}분"]
        if m:
            seg.append(m)
        if isinstance(by, int):
            seg.append(f"{by}년")
        lines.append(f"{i}. {l['complex_name']} ({l.get('gu', '')})")
        lines.append(f"   {' · '.join(seg)}")

    # 페이지 링크
    url = meta.get("report_url")
    if url:
        lines.append(f"\n👉 전체 리포트(상세·지도·후기): {url}")
    return "\n".join(lines)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    code, resp = send_to_me("📨 창원 아파트 리포트 — 카톡 발송 테스트 성공!\n"
                            "이제 매일 아침 이 채팅(나와의 채팅)으로 Top5를 보내드릴게요. 🏠")
    print("발송 결과:", code, resp)
