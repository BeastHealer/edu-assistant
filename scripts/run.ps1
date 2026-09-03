# Запуск ИИ-куратора EduPath (Windows PowerShell)
Set-Location $PSScriptRoot\..
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe scripts\index_knowledge.py
.\.venv\Scripts\python.exe scripts\seed_analytics.py
.\.venv\Scripts\python.exe -m streamlit run app.py
