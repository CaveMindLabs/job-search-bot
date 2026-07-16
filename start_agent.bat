@echo off
:: 1. Start Uvicorn in a brand new window
start "Uvicorn Server" cmd /k "call .venv\Scripts\activate && uvicorn main:app --reload"

:: 2. Start ngrok in the main window
call .venv\Scripts\activate
ngrok http 8000