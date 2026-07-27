# 창원 통근권 아파트 일일 리포트 🏠

직장 통근권 안에서 **매매 전용 85㎡ 이하(4억 이하) 아파트**를 매일 자동 분석해
**Top 10 리포트(HTML)** 를 만들고 **카카오톡으로 발송**하는 개인 자동화 도구.

> 네이버부동산 라이브 매물 + 국토부 실거래가 + 카카오(통근·상권) + 네이버 실거주 후기
> → 3축 점수화(가격·통근·상권) → 애플 디자인 리포트 → 카카오톡 '나에게 보내기' → GitHub Pages 공개.

이 저장소는 **Claude Code 플러그인**이면서 **독립 실행 패키지**입니다.

---

## ✨ 기능
- **수집**: 네이버부동산 라이브 호가(토큰 추출+curl_cffi) · 국토부 실거래가(저평가·연식·6개월 추이)
- **필터**: 매매 4억 이하 · 통근 ≤30분(러시아워 보정) · 전용≤85㎡ · 연식(35년 초과 제외, 25년+ 올수리·저평가 규칙)
- **점수화(3축)**: 가격/저평가(30) · 통근(20) · 상권(마트·병원, 20) — 가중치 조정 가능
- **리포트**: 정보 풍부형 카드(호가분석·디딤돌 추정·카카오맵·실거주 후기·시세추이) · 변동 하이라이트 · 누적 관심 비교 · 날짜별 아카이브
- **발송/배포**: 카카오톡 '나에게 보내기' · GitHub Pages 공개 · launchd 매일 자동 실행

## 🔑 사전 준비 (API 키)
| 키 | 발급처 | 용도 | 필수 |
|---|---|---|---|
| `MOLIT_SERVICE_KEY` | data.go.kr (아파트 매매/전월세 실거래가) | 실거래·저평가·연식 | ✅ |
| `KAKAO_REST_KEY` | developers.kakao.com (REST 키) | 통근·지오코딩·육아/상권 | ✅ |
| `KAKAO_JS_KEY` | 〃 (JavaScript 키) | 리포트 지도 임베드 | ✅ |
| `KAKAO_REFRESH_TOKEN` + `KAKAO_CLIENT_SECRET` | 〃 (카카오 로그인 OAuth, `talk_message`) | 카톡 발송 | 발송 시 |
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | developers.naver.com (검색 API) | 실거주 후기 | 선택 |

> 카카오: 제품설정>카카오로그인 활성화 + Redirect URI `https://localhost` + 동의항목 `talk_message` + (지도용) JavaScript SDK 도메인 등록. OAuth 인가코드→토큰 교환으로 refresh_token 획득.

## 🚀 설치 & 실행
```bash
bash setup.sh                 # venv 생성 + 의존성 설치 + .env 템플릿 복사
# .env 에 키 입력
vi config.yaml                # 직장 좌표·필터·가중치·지역 조정
./venv/bin/python run_p1.py   # 수집→분석→HTML→카톡 (한 번에)
open docs/index.html          # 결과 확인
```

## ⏰ 매일 자동 실행 (macOS launchd)
```bash
# run_daily.sh = run_p1.py + GitHub Pages 푸시
cp launchd/com.neureup.changwonapt.plist ~/Library/LaunchAgents/   # (또는 직접 작성)
launchctl load -w ~/Library/LaunchAgents/com.neureup.changwonapt.plist
launchctl start com.neureup.changwonapt   # 수동 1회 테스트
```
매일 08:00 자동 실행 (맥이 깨어 있어야 함).

## 🌐 GitHub Pages
저장소 Settings → Pages → Source: `main` `/docs` → `https://<id>.github.io/<repo>/`.
`config.yaml`의 `report_url`에 이 주소를 넣으면 카톡 '전체 리포트 보기' 버튼이 연결됩니다.
(지도 임베드를 위해 이 도메인을 카카오 JavaScript SDK 도메인에 등록.)

## 🧩 Claude Code 플러그인으로 쓰기
```
/plugin marketplace add https://github.com/NUUUUUU/changwon-apt-report
/plugin install changwon-apt-report@neureup-plugins
```
설치 후 "창원 아파트 리포트 돌려줘" 라고 하면 Claude가 실행합니다. (`skills/changwon-apt-report/SKILL.md`)

## 📁 구조
```
src/collectors/  naver.py(라이브 매물) · molit.py(국토부 실거래)
src/enrich/      commute.py(통근·러시보정) · amenity.py(육아·상권) · naver_review.py(후기)
src/             filters.py · score.py · finance.py(디딤돌) · history.py(변동·누적) · report.py(HTML)
run_p1.py        전체 오케스트레이션
run_daily.sh     run_p1 + GitHub Pages 푸시 (launchd가 호출)
config.yaml      직장·필터·가중치·지역·러시보정·report_url
docs/            생성된 리포트(HTML) — GitHub Pages 발행 폴더
```

## ⚠️ 주의·면책
- 국토부 API 호출에 `User-Agent` 헤더 필수.
- 네이버/당근 등 포털 데이터는 개인·소량 용도로만(이용약관 유의).
- 본 리포트는 공개 데이터 자동 분석 **참고자료**입니다. 호가·매물은 변동·허위 가능. **반드시 현장확인·중개사 상담 후 판단하세요.** 가격·점수·디딤돌은 추정치.

## 라이선스
MIT
