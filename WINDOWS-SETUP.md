# Windows 매일 자동 실행 가이드

원본은 macOS(launchd) 기준이라, Windows에서는 아래 순서로 준비하면 **매일 같은 시간에 카톡 리포트**를 받을 수 있습니다.

> 이 저장소 경로 예시: `C:\Users\shins\OneDrive\Desktop\claude\sales\changwon-apt-report`
> (아래 명령의 경로를 본인 경로로 바꾸세요.)

---

## 0. 선행조건 (이게 없으면 자동 발송이 동작하지 않습니다)

### (1) Python 설치 — 필수
현재 이 PC의 `python`은 Microsoft Store 스텁이라 실제로 실행되지 않습니다.
[python.org](https://www.python.org/downloads/windows/)에서 **Python 3.11+** 를 받아 설치하세요.
설치 시 **"Add python.exe to PATH"** 체크. 확인:
```powershell
python --version
```

### (2) 의존성 설치 (venv)
저장소 폴더에서:
```powershell
cd "C:\Users\shins\OneDrive\Desktop\claude\sales\changwon-apt-report"
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### (3) API 키 입력 — 필수 (직접 채우셔야 합니다)
`.env.example`를 복사해 `.env`로 만들고 값을 채웁니다:
```powershell
Copy-Item .env.example .env
notepad .env
```
채워야 하는 키(발급처는 [README](README.md) 참고):
- `MOLIT_SERVICE_KEY` — 국토부 실거래가 (data.go.kr) **필수**
- `KAKAO_REST_KEY`, `KAKAO_JS_KEY` — 카카오 (developers.kakao.com) **필수**
- `KAKAO_REFRESH_TOKEN`, `KAKAO_CLIENT_SECRET` — 카톡 '나에게 보내기' 발송용 **필수**
- `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` — 실거주 후기 (선택)

> ⚠️ 키·토큰은 보안 정보라 대신 입력해 드릴 수 없습니다. 직접 넣어주세요.

---

## 1. 수동 테스트 (스케줄 걸기 전에 1회 실행 확인)
```powershell
cd "C:\Users\shins\OneDrive\Desktop\claude\sales\changwon-apt-report"
powershell -ExecutionPolicy Bypass -File .\run_daily.ps1
Get-Content .\logs\daily.log -Tail 30
```
카톡이 오고 `docs\index.html`이 갱신되면 성공.

---

## 2. 매일 같은 시간 자동 실행 (작업 스케줄러 등록)
아래는 **매일 08:00** 예시입니다. 원하는 시간으로 `At '08:00'`만 바꾸세요.
PowerShell을 **관리자 권한**으로 열고 실행:

```powershell
$repo = "C:\Users\shins\OneDrive\Desktop\claude\sales\changwon-apt-report"
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$repo\run_daily.ps1`""
$trigger = New-ScheduledTaskTrigger -Daily -At '08:00'
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun `
  -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName "ChangwonAptReport" `
  -Action $action -Trigger $trigger -Settings $settings `
  -Description "창원 아파트 일일 리포트 (매일 08:00)" -RunLevel Limited
```

등록 확인 / 즉시 1회 실행 / 삭제:
```powershell
Get-ScheduledTask -TaskName "ChangwonAptReport"
Start-ScheduledTask -TaskName "ChangwonAptReport"      # 지금 바로 테스트
Unregister-ScheduledTask -TaskName "ChangwonAptReport" -Confirm:$false   # 제거
```

> 📝 참고
> - PC가 **꺼져 있으면** 그 시간에 실행되지 않습니다(`-WakeToRun`은 절전/대기에서만 깨움).
> - 실패 시 `logs\daily.log`를 확인하세요.
> - `git push`가 자동으로 되려면 이 PC에 GitHub 인증(현재 `lee-yelyn`)이 유지돼 있어야 합니다.
