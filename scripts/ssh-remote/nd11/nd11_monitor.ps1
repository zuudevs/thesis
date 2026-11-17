# ND-11 during-run production monitor (READ-ONLY) - audit runbook section 4 step 5.
# Periodic snapshot: production PID alive, CPU/WS, GET /rekap status, RAM%,
# benchmark listeners. No process is ever started/stopped/configured here.
param(
    [int]$ProdPort = 0,
    [int]$Seconds = 90,
    [int]$Interval = 5
)
$ErrorActionPreference = 'SilentlyContinue'
$prodPid = 0
if ($ProdPort -gt 0) {
    $c = Get-NetTCPConnection -State Listen -LocalPort $ProdPort -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c) { $prodPid = $c.OwningProcess }
}
"monitor: prodPort=$ProdPort prodPid=$prodPid seconds=$Seconds interval=$Interval"
$sw = [Diagnostics.Stopwatch]::StartNew()
while ($sw.Elapsed.TotalSeconds -lt $Seconds) {
    $ts = (Get-Date).ToString('HH:mm:ss')
    if ($prodPid -gt 0) {
        $p = Get-Process -Id $prodPid -ErrorAction SilentlyContinue
        if (-not $p) { "$ts PROD_PID_GONE - ABORT SIGNAL"; break }
        $cpu = [math]::Round($p.CPU, 1)
        $ws = [math]::Round($p.WorkingSet64 / 1MB)
    } else { $cpu = 'n/a'; $ws = 'n/a' }
    $os = Get-CimInstance Win32_OperatingSystem
    $ramPct = [math]::Round(100 * (1 - $os.FreePhysicalMemory / $os.TotalVisibleMemorySize), 1)
    $bench = @(Get-NetTCPConnection -State Listen -LocalPort 3100, 3101 -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty LocalPort | Sort-Object -Unique) -join ','
    $code = 'skip'
    if ($ProdPort -gt 0) {
        try {
            $r = Invoke-WebRequest -UseBasicParsing -Uri ("http://127.0.0.1:$ProdPort/rekap") -TimeoutSec 10
            $code = $r.StatusCode
        } catch { $code = -1 }
    }
    "$ts prod_pid=$prodPid cpu_s=$cpu ws_mb=$ws rekap=$code ramPct=$ramPct bench_listen=[$bench]"
    Start-Sleep -Seconds $Interval
}
"monitor: done ($([math]::Round($sw.Elapsed.TotalSeconds, 1))s)"
