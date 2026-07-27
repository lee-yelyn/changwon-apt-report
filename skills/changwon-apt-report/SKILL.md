---
name: changwon-apt-report
description: >
  창원 통근권 아파트 일일 리포트를 수집·분석·생성·발송한다. 네이버부동산 라이브 매물 →
  통근(러시아워 보정)·면적(전용≤85㎡)·연식 필터 → 국토부 실거래 저평가 + 카카오 상권 →
  3축 점수화로 Top10 → 애플 디자인 HTML(docs/) → 카카오톡 '나에게 보내기' → GitHub Pages.
  사용 시점(트리거): "창원 아파트 리포트 돌려줘", "오늘 매물 뽑아줘", "통근권 아파트 리포트",
  "부동산 리포트 생성", "아파트 추천 업데이트". English: run changwon apartment report,
  generate real-estate report, refresh apartment recommendations.
  단순 부동산 잡담에는 트리거하지 말 것 — 실제 리포트 생성/실행 요청일 때만.
---

# 창원 통근권 아파트 일일 리포트

> 한 줄 실행: 프로젝트 루트에서 `./venv/bin/python run_p1.py`
> 전체 파이프라인(수집→분석→Top10→HTML→카톡→스냅샷)이 한 번에 돈다.

## 사용 흐름 (Claude가 따를 단계)

**1. 사전 점검 (최초 1회)**
- `venv/`와 `.env`가 있는지 확인. 없으면 `bash setup.sh` 실행 후, `.env`에 키 입력 안내.
- 필요한 키(`.env`): `MOLIT_SERVICE_KEY`(국토부), `KAKAO_REST_KEY`/`KAKAO_JS_KEY`/`KAKAO_REFRESH_TOKEN`/`KAKAO_CLIENT_SECRET`(카카오), `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET`(후기, 선택). 발급법은 README 참고.

**2. 리포트 생성·발송**
```bash
cd "<플러그인 경로>"
./venv/bin/python run_p1.py
```
- 출력: `docs/{YYYY-MM-DD}.html` + `docs/index.html`, 콘솔에 Top10 요약.
- 카카오톡 '나에게 보내기'로 날짜→Top5 요약→전체 리포트 링크 발송.

**3. (선택) GitHub Pages 갱신·매일 자동화**
- 공개 발행: `run_daily.sh`가 `run_p1.py` 실행 후 `git add docs && commit && push`까지 수행.
- 매일 자동: macOS `launchd`(`~/Library/LaunchAgents/com.neureup.changwonapt.plist`, 매일 08:00) → `run_daily.sh`.
- 수동 1회: `launchctl start com.neureup.changwonapt`.

## 설정 (config.yaml — 코드 수정 없이 조정)
- `workplace`: 직장 좌표(lng/lat) — 통근 기준점.
- `filters`: 거래유형(매매)·가격상한(4억)·통근분·면적(전용≤85㎡)·연식(35년 초과 제외 / 25년+ 올수리·저평가 규칙).
- `scoring.weights`: 가격·통근·상권 가중치(각 30/20/20).
- `rush.per_min`: 러시아워 통근 보정 계수(장거리일수록 ↑).
- `regions_gu`: 통근권 시군구(cortarNo·lawd) — 동은 자동 확장 + 거리 사전필터.
- `report_url`: 카톡에 넣을 GitHub Pages 주소.

## 주의·트러블슈팅
- **국토부 API는 `User-Agent` 헤더 필수** (없으면 WAF가 'Request Blocked').
- 카카오 토큰: refresh_token으로 access_token 자동 갱신(`src/notify.py`). 토큰 60일.
- 카카오맵 임베드는 **JS SDK 도메인 등록**(앱>플랫폼키>JavaScript키)이 필요 — 미등록 시 '카카오맵 보기' 링크로 폴백.
- 카카오 무료 길찾기 API는 미래시각 예측 미지원 → 러시아워는 거리비례 보정(`rush.per_min`)으로 근사.
- 실행 시간: 통근 양방향 호출로 ~10분 내외(반경·단지 수에 비례).

## 구조
`src/collectors`(naver·molit) · `src/enrich`(commute·amenity·naver_review) · `src/filters.py` · `src/score.py` · `src/finance.py` · `src/history.py` · `src/report.py` · `run_p1.py`(오케스트레이션) · `run_daily.sh`(+Pages).
