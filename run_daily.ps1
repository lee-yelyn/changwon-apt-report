# 창원 아파트 리포트 — 매일 실행 (Windows 작업 스케줄러가 호출)
# 분석 → HTML → 카톡 '나에게 보내기' → GitHub Pages 푸시
# 스크립트 자신의 위치를 기준으로 동작하므로 어디에 두든 동작합니다.

$ErrorActionPreference = 'Continue'
Set-Location -LiteralPath $PSScriptRoot

New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot 'logs') | Out-Null
$log = Join-Path $PSScriptRoot 'logs\daily.log'
"===== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') 시작 =====" | Out-File -FilePath $log -Append -Encoding utf8

# venv 파이썬 우선(Windows: venv\Scripts\python.exe), 없으면 시스템 python
$py = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }

& $py run_p1.py *>> $log

# GitHub Pages 갱신 (docs 커밋·푸시)
git add docs *>> $log
git commit -q -m "리포트 $(Get-Date -Format 'yyyy-MM-dd')" *>> $log
git push origin main *>> $log

"===== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') 종료 (exit $LASTEXITCODE) =====" | Out-File -FilePath $log -Append -Encoding utf8
