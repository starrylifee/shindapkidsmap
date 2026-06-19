@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo  우리 동네 추천 장소 지도 서버를 시작합니다
echo  브라우저에서 http://localhost:8000 접속
echo  종료하려면 이 창에서 Ctrl+C
echo ============================================
start "" http://localhost:8000
python -m http.server 8000
