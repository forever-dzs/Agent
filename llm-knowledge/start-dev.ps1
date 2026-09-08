$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"

Write-Host "[1/2] 启动后端服务..."
$backendProcess = Start-Process -FilePath $venvPython -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000") -WorkingDirectory $backendDir -PassThru

Write-Host "[2/2] 启动前端服务..."
$frontendProcess = Start-Process -FilePath "npm" -ArgumentList @("run", "dev", "--", "--host", "0.0.0.0", "--port", "5173") -WorkingDirectory $frontendDir -PassThru

Write-Host "后端 PID: $($backendProcess.Id)"
Write-Host "前端 PID: $($frontendProcess.Id)"
Write-Host "访问地址："
Write-Host "- 前端: http://localhost:5173"
Write-Host "- 后端: http://localhost:8000/docs"
