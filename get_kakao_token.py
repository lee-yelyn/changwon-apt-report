"""카카오 인가코드 → refresh_token 교환기 (1회용 도우미).

사용법:
    ./venv/Scripts/python.exe get_kakao_token.py <인가코드>

.env의 KAKAO_REST_KEY / KAKAO_CLIENT_SECRET를 읽어 토큰을 교환하고,
받은 refresh_token을 .env의 KAKAO_REFRESH_TOKEN에 자동 저장한다.
(토큰 값은 화면에 전체로 출력하지 않는다.)
"""
import os
import sys
import re
import requests
from dotenv import load_dotenv

REDIRECT_URI = "https://localhost"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def upsert_env(key, value):
    """.env에서 key 라인을 교체하거나 없으면 추가."""
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            lines = f.read().splitlines()
    pat = re.compile(rf"^\s*{re.escape(key)}\s*=")
    replaced = False
    for i, ln in enumerate(lines):
        if pat.match(ln):
            lines[i] = f"{key}={value}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{key}={value}")
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("사용법: python get_kakao_token.py <인가코드>")
        print("  (브라우저 주소창 https://localhost/?code=... 의 code= 뒤 값)")
        sys.exit(1)

    code = sys.argv[1].strip()
    load_dotenv(ENV_PATH)
    rest_key = os.environ.get("KAKAO_REST_KEY", "").strip()
    secret = os.environ.get("KAKAO_CLIENT_SECRET", "").strip()

    if not rest_key:
        print("❌ .env의 KAKAO_REST_KEY가 비어 있습니다. 먼저 REST API 키를 채워주세요.")
        sys.exit(1)

    data = {
        "grant_type": "authorization_code",
        "client_id": rest_key,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }
    if secret:
        data["client_secret"] = secret

    r = requests.post(TOKEN_URL, data=data, timeout=15)
    try:
        j = r.json()
    except Exception:
        print("❌ 응답 파싱 실패:", r.status_code, r.text[:300])
        sys.exit(1)

    refresh = j.get("refresh_token")
    if not refresh:
        print("❌ refresh_token을 받지 못했습니다. 응답:")
        print("  ", {k: v for k, v in j.items() if k != "access_token"})
        print("\n점검: ① 인가코드 만료/재사용 여부(다시 발급) ② Redirect URI가 https://localhost 인지")
        print("      ③ 동의항목 talk_message 사용 설정 ④ REST 키/Client Secret 정확한지")
        sys.exit(1)

    upsert_env("KAKAO_REFRESH_TOKEN", refresh)
    masked = refresh[:6] + "..." + refresh[-4:]
    print("✅ refresh_token 발급·저장 완료!")
    print(f"   .env의 KAKAO_REFRESH_TOKEN 에 저장됨 (값: {masked})")
    if j.get("access_token"):
        print(f"   (access_token도 정상 수신 — 만료 {j.get('expires_in','?')}초, 자동 갱신되므로 저장 안 함)")
    print("\n다음: 발송 테스트 →  ./venv/Scripts/python.exe src/notify.py")


if __name__ == "__main__":
    main()
