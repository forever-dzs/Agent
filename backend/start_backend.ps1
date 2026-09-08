$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path (Split-Path -Parent $root) ".venv\Scripts\python.exe"

Write-Host "启动后端服务：http://localhost:8000/docs"
& $venvPython -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
