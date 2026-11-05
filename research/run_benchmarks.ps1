# ============================================================================
#  run_benchmarks.ps1 - Runner benchmark SEKALI-JALAN (device pribadi & SAQ)
# ============================================================================
#  Satu perintah, tanpa konfigurasi tambahan selain env SAMPLE & RAW:
#
#    1. Preflight korpus terpadu $SAMPLE (3 grup, byte-sama lintas device):
#       a. corpus install --skip-existing  (JSON_checker + commons; jeopardy
#          via crawler bila fixture belum ada)
#       b. saq-report generate-samples.js  (fixture deterministik -> $SAMPLE/saq-report)
#       c. saq-report verify-samples.js
#       d. corpus scan + verify            (manifest sha256 = jangkar join)
#    2. ze_json: 5 export_benchmark_* (repetisi terstandar ZE_BENCH_REPETITIONS
#       -> agregat mean/median/stddev/ci95 utk P50/CI95 lintas-device),
#       termasuk corpus_benchmark yang mengukur SELURUH $SAMPLE (scanner64).
#    3. saq-report: benchmark-json.js di atas korpus terpadu yang sama
#       (JSON.parse baseline; guard json-clone 64 MB otomatis).
#    4. ze_json_js: benchmark_ze_json_js.mjs - ze_json WASM binding vs
#       JSON.parse di runtime Node yang sama (perbandingan inti skripsi;
#       butuh Node >= 24 / WASM memory64).
#    5. audit_raw.py: gerbang integritas - semua artefak HARUS KEEP.
#
#  Pemakaian:
#    powershell research/run_benchmarks.ps1                    # full (5 repetisi)
#    powershell research/run_benchmarks.ps1 -Repetitions 7     # kustom
#    powershell research/run_benchmarks.ps1 -Quick             # 3 repetisi (sanity)
#    powershell research/run_benchmarks.ps1 -SkipZeJson        # hanya saq-report
#    powershell research/run_benchmarks.ps1 -SkipSaqReport     # hanya ze_json
#    powershell research/run_benchmarks.ps1 -SkipZeJsonJs      # tanpa benchmark JS
#
#  CATATAN ENCODING: file ini sengaja ASCII-murni - Windows PowerShell 5.1
#  membaca .ps1 tanpa BOM sebagai ANSI, jadi karakter non-ASCII (em-dash dll)
#  merusak parsing string.
#
#  DURASI (5 repetisi): parser ~11 min + scanner ~26 min + session ~2,7 jam +
#  span_iso ~2 jam + corpus ~50 min + saq-report ~20 min + ze_json_js ~30-60
#  min = sekitar 7-8 jam.
#  Jalankan di device yang tidak tidur (sleep AC sudah dimatikan oleh runner).
# ============================================================================
param(
    [int]$Repetitions = 5,
    [switch]$Quick,           # mode cepat: 3 repetisi (sanity, bukan angka skripsi)
    [switch]$SkipZeJson,
    [switch]$SkipSaqReport,
    [switch]$SkipZeJsonJs,
    [switch]$SkipCorpusPreflight
)

$ErrorActionPreference = "Stop"
$workspace = Resolve-Path "$PSScriptRoot\.."
$zeRepo = Join-Path $workspace "ze_json"
$saqRepo = Join-Path $workspace "saq-report"

if ($Quick) { $Repetitions = 3 }

foreach ($var in @("SAMPLE", "RAW")) {
    if (-not (Test-Path "env:$var")) {
        throw "Environment $var belum di-set. Contoh: `$env:$var = '<path>'"
    }
}
Write-Host "SAMPLE = $env:SAMPLE" -ForegroundColor DarkGray
Write-Host "RAW    = $env:RAW" -ForegroundColor DarkGray

# Laptop tidak boleh tidur di tengah pengukuran (pernah terjadi: proses
# ter-suspend berjam-jam, timing tercemar). Matikan sleep/hibernate saat AC.
powercfg /change standby-timeout-ac 0 | Out-Null
powercfg /change hibernate-timeout-ac 0 | Out-Null
Write-Host "Sleep/hibernate (AC) dimatikan selama run." -ForegroundColor DarkGray

# ---------------------------------------------------------------------------
# 1. Preflight korpus terpadu
# ---------------------------------------------------------------------------
if (-not $SkipCorpusPreflight) {
    Write-Host "`n=== [1/5] Preflight korpus terpadu ===" -ForegroundColor Cyan

    Write-Host "-- corpus install --skip-existing" -ForegroundColor DarkCyan
    Push-Location $zeRepo
    try {
        python scripts/corpus/main.py install --skip-existing
        if ($LASTEXITCODE -ne 0) { throw "corpus install gagal." }
    } finally { Pop-Location }

    Write-Host "-- saq-report generate-samples.js" -ForegroundColor DarkCyan
    Push-Location $saqRepo
    try {
        node benchmark/generate-samples.js
        if ($LASTEXITCODE -ne 0) { throw "generate-samples gagal." }
        node benchmark/verify-samples.js
        if ($LASTEXITCODE -ne 0) { throw "verify-samples gagal." }
    } finally { Pop-Location }

    Write-Host "-- corpus scan + verify" -ForegroundColor DarkCyan
    Push-Location $zeRepo
    try {
        python scripts/corpus/main.py scan
        if ($LASTEXITCODE -ne 0) { throw "corpus scan gagal." }
        python scripts/corpus/main.py verify
        if ($LASTEXITCODE -ne 0) { throw "corpus verify gagal: korpus tidak konsisten." }
    } finally { Pop-Location }
} else {
    Write-Host "`n=== [1/5] Preflight korpus DILEWATI (-SkipCorpusPreflight) ===" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 2. ze_json - 5 export benchmark (repetisi terstandar)
# ---------------------------------------------------------------------------
if (-not $SkipZeJson) {
    Write-Host "`n=== [2/5] ze_json benchmark (repetisi=$Repetitions) ===" -ForegroundColor Cyan
    Push-Location $zeRepo
    try {
        cmake --preset native-release "-DZE_BENCH_REPETITIONS=$Repetitions"
        if ($LASTEXITCODE -ne 0) { throw "configure gagal." }

        $targets = @(
            "parser_benchmark",
            "scanner_benchmark",
            "session_benchmark",
            "span_iso_benchmark",
            "corpus_benchmark"
        )
        foreach ($t in $targets) {
            Write-Host "-- export_benchmark_$t" -ForegroundColor DarkCyan
            cmake --build build/native-release --target "export_benchmark_$t"
            if ($LASTEXITCODE -ne 0) { throw "export_benchmark_$t gagal." }
        }
    } finally { Pop-Location }
} else {
    Write-Host "`n=== [2/5] ze_json DILEWATI (-SkipZeJson) ===" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 3. saq-report - JSON.parse baseline di korpus terpadu
# ---------------------------------------------------------------------------
if (-not $SkipSaqReport) {
    Write-Host "`n=== [3/5] saq-report benchmark (JSON.parse) ===" -ForegroundColor Cyan
    Push-Location $saqRepo
    try {
        node benchmark/benchmark-json.js --input=$env:SAMPLE --out="$env:RAW\benchmark\saq-report"
        if ($LASTEXITCODE -ne 0) { throw "benchmark-json.js gagal." }
    } finally { Pop-Location }
} else {
    Write-Host "`n=== [3/5] saq-report DILEWATI (-SkipSaqReport) ===" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 4. ze_json_js - binding WASM vs JSON.parse di runtime Node yang sama
# ---------------------------------------------------------------------------
if (-not $SkipZeJsonJs) {
    Write-Host "`n=== [4/5] ze_json_js benchmark (WASM vs JSON.parse) ===" -ForegroundColor Cyan
    node "$PSScriptRoot\benchmark_ze_json_js.mjs" --input=$env:SAMPLE --out="$env:RAW\benchmark\ze_json_js"
    if ($LASTEXITCODE -ne 0) { throw "benchmark_ze_json_js.mjs gagal (butuh Node >= 24 utk WASM memory64)." }
} else {
    Write-Host "`n=== [4/5] ze_json_js DILEWATI (-SkipZeJsonJs) ===" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 5. Audit - gerbang integritas artefak
# ---------------------------------------------------------------------------
Write-Host "`n=== [5/5] Audit artefak ===" -ForegroundColor Cyan
python "$PSScriptRoot\audit_raw.py" --raw $env:RAW
if ($LASTEXITCODE -ne 0) {
    throw "audit_raw menemukan pelanggaran - perbaiki sebelum analisa."
}

Write-Host "`nSelesai. Artefak: $env:RAW\benchmark (ze_json + saq-report + ze_json_js)" -ForegroundColor Green
Write-Host "Analisa : python research/analyze_benchmarks.py"
Write-Host "Visual  : python research/visualize.py"
