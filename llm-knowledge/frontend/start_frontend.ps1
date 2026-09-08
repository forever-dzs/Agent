Set-Location $PSScriptRoot
Write-Host "启动前端服务：http://localhost:5173"
npm run dev -- --host 0.0.0.0 --port 5173
