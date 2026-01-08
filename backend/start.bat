@echo off
echo Starting Backend Server...
cd %~dp0
uvicorn app.main:app --reload --port 8000












