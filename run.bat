@echo off
cd /d "%~dp0"
if not exist .venv (
  echo Creating virtual environment...
  py -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python app.py
