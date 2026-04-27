@echo off
title NidBuyer Launcher
echo [1/3] Verification des dependances...
pip install -r requirements.txt

echo [2/3] Lancement du Backend (FastAPI)...
start cmd /k "title NidBuyer BACKEND && cd /d %~dp0 && python -m uvicorn backend.main:app --reload"

timeout /t 5

echo [3/3] Lancement du Frontend (Streamlit)...
start cmd /k "title NidBuyer FRONTEND && cd /d %~dp0 && python -m streamlit run frontend/app.py"

echo.
echo ======================================================
echo NidBuyer est en cours de lancement !
echo Backend : http://127.0.0.1:8000/docs
echo Frontend : http://127.0.0.1:8501
echo ======================================================
pause