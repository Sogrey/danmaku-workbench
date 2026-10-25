# ============================================================
# danmaku-workbench E2E 检查脚本（提交前本地 CI）
#
# 用法（项目根目录）：
#   npm run e2e                 # 全量：后端语法 + 前端类型/构建 + mock API E2E + laya 探测
#   npm run e2e -- --skip-build # 跳过 vite build（快速模式，仅类型检查）
#
# 步骤：
#   1. 后端核心文件语法检查（py_compile）
#   2. 前端 vue-tsc 类型检查 + vite build
#   3. 临时启动 mock 决策服务（端口 8314，避开运行中的 8313）
#      断言 /api/health 与 /api/decide 的 camelCase 契约
#   4. 探测 8313 决策服务（若在跑则校验 provider=laya*，不在则 SKIP 不算失败）
# 退出码：0 = 全部通过；1 = 存在失败步骤
# ============================================================
param(
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root 'backend'
$py = Join-Path $backend '.venv\Scripts\python.exe'
$mockPort = 8314
$layaPort = 8313

$script:steps = New-Object System.Collections.Generic.List[object]
$script:hasFail = $false

function Step {
    param([string]$Name, [bool]$Ok, [string]$Detail)
    $script:steps.Add([pscustomobject]@{ Name = $Name; Ok = $Ok; Detail = $Detail })
    if (-not $Ok) { $script:hasFail = $true }
    $mark = if ($Ok) { 'PASS' } else { 'FAIL' }
    Write-Host ("[{0}] {1} {2}" -f $mark, $Name, $Detail)
}

Write-Host "=== danmaku-workbench E2E 检查 ===" -ForegroundColor Cyan

# ---------- 1. 后端语法 ----------
$backendFiles = @(
    'app\main.py',
    'app\providers\__init__.py',
    'app\providers\base.py',
    'app\providers\mock.py',
    'app\providers\laya.py'
)
if (-not (Test-Path $py)) {
    Step '后端 venv' $false "未找到 $py —— 请先搭建 backend/.venv"
    Write-Host "`n=== 汇总 ===`n$($script:steps | Format-Table -AutoSize | Out-String)"
    exit 1
}
& $py -m py_compile ($backendFiles | ForEach-Object { Join-Path $backend $_ })
Step '后端语法检查' ($LASTEXITCODE -eq 0) ($backendFiles.Count.ToString() + ' 个文件 py_compile')

# ---------- 2. 前端类型 + 构建 ----------
Push-Location $root
try {
    npm run type-check 2>&1 | Out-Null
    Step '前端类型检查' ($LASTEXITCODE -eq 0) 'vue-tsc --noEmit'

    if ($SkipBuild) {
        Step '前端构建' $true 'SKIP（--skip-build）'
    }
    else {
        npm run build 2>&1 | Out-Null
        Step '前端构建' ($LASTEXITCODE -eq 0) 'vite build → dist/'
    }
}
finally {
    Pop-Location
}

# ---------- 3. mock API E2E（临时端口 8314） ----------
$mockProc = $null
try {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $py
    $psi.Arguments = '-m uvicorn app.main:app --host 127.0.0.1 --port ' + $mockPort
    $psi.WorkingDirectory = $backend
    $psi.CreateNoWindow = $true
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.EnvironmentVariables['DECISION_PROVIDER'] = 'mock'
    $mockProc = [System.Diagnostics.Process]::Start($psi)
    $mockProc.BeginOutputReadLine()
    $mockProc.BeginErrorReadLine()

    $ready = $false
    $health = $null
    foreach ($i in 1..30) {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/api/health" -f $mockPort) -TimeoutSec 2
            if ($health.ok) { $ready = $true; break }
        }
        catch { }
    }
    if (-not $ready) {
        throw 'mock 服务 15s 内未就绪'
    }

    $body = '{"message":{"id":"e2e-001","author":"E2E","time":"00:00:00","text":"pip 安装依赖一直报错，怎么解决？"}}'
    $bytes = [Text.Encoding]::UTF8.GetBytes($body)
    $r = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/api/decide" -f $mockPort) -Method Post -ContentType 'application/json' -Body $bytes -TimeoutSec 30

    $checks = @(
        @{ k = 'messageId 键';    v = ($r.messageId -eq 'e2e-001') },
        @{ k = 'provider 键';     v = ($null -ne $r.provider) },
        @{ k = 'choice.category 五类'; v = (@('technical', 'feedback', 'chat', 'spam', 'insufficient') -contains $r.choice.category) },
        @{ k = 'choice.probabilities'; v = ($null -ne $r.choice.probabilities -and $null -ne $r.choice.probabilities.technical) },
        @{ k = 'noul.probability'; v = ($r.noul.probability -ge 0 -and $r.noul.probability -le 1) },
        @{ k = 'score.levelIndex 0-3'; v = ($r.score.levelIndex -ge 0 -and $r.score.levelIndex -le 3 -and ($r.score.levelIndex % 1) -eq 0) },
        @{ k = 'score.level 文本'; v = ($null -ne $r.score.level) },
        @{ k = 'latencyMs/judgedAt'; v = ($null -ne $r.latencyMs -and $null -ne $r.judgedAt) }
    )
    $failed = $checks | Where-Object { -not $_.v }
    if ($failed) {
        $names = ($failed | ForEach-Object { $_.k }) -join ', '
        Step 'mock API 契约断言' $false ("失败项：" + $names)
    }
    else {
        Step 'mock API 契约断言' $true 'health=ok / decide 契约 8 项全过'
    }
}
catch {
    Step 'mock API E2E' $false $_.Exception.Message
}
finally {
    if ($mockProc -and -not $mockProc.HasExited) {
        Stop-Process -Id $mockProc.Id -Force -ErrorAction SilentlyContinue
    }
}

# ---------- 4. laya 决策服务探测（信息项，不跑不失败） ----------
try {
    $lh = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/api/health" -f $layaPort) -TimeoutSec 3
    $isLaya = ($lh.provider -like 'laya*')
    Step 'laya 决策服务探测(8313)' $isLaya ("provider=" + $lh.provider)
}
catch {
    Step 'laya 决策服务探测(8313)' $true 'SKIP（服务未运行，非必需项）'
}

# ---------- 汇总 ----------
Write-Host "`n=== 汇总 ===" -ForegroundColor Cyan
$script:steps | Format-Table @{ Label = '结果'; Expression = { if ($_.Ok) { 'PASS' } else { 'FAIL' } } }, Name, Detail -AutoSize | Out-Host
$failCount = @($script:steps | Where-Object { -not $_.Ok }).Count
Write-Host ("总计 {0} 步，失败 {1} 步" -f $script:steps.Count, $failCount)
if ($script:hasFail) { exit 1 } else { Write-Host 'E2E 全部通过' -ForegroundColor Green; exit 0 }
