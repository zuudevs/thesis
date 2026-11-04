# ============================================================================
#  run_targets_ordered.ps1 - sekali-jalan, urutan cepat-ke-lambat
# ============================================================================
#  Lanjutan run_full_ffe41cb (runner asli dimatikan saat baru mulai parser).
#  Memakai build + RUN_ID yang sudah ada (zuu-20261104164103-ffe41cb) - TIDAK
#  reconfigure lagi agar semua target satu RUN_ID.
#
#  Urutan (hitungan menit dulu, berjam-jam belakangan):
#    parser -> scanner -> corpus -> saq-report -> session -> span_iso -> audit
# ============================================================================
$ErrorActionPreference = "Stop"
$workspace = "D:\kuliah_\7_semester\skripsi\v4"
$zeRepo = "$workspace\ze_json"
$saqRepo = "$workspace\saq-report"

foreach ($var in @("SAMPLE", "RAW")) {
    if (-not (Test-Path "env:$var")) {
        throw "Environment $var belum di-set."
    }
}

function Run-Export([string]$t) {
    Write-Host "`n== [$(Get-Date -Format HH:mm:ss)] export_benchmark_$t ==" -ForegroundColor Cyan
    Push-Location $zeRepo
    try {
        cmake --build build/native-release --target "export_benchmark_$t"
        if ($LASTEXITCODE -ne 0) { throw "export_benchmark_$t gagal." }
    } finally { Pop-Location }
}

# --- cepat (menit) ---
Run-Export "parser_benchmark"
Run-Export "scanner_benchmark"
Run-Export "corpus_benchmark"

Write-Host "`n== [$(Get-Date -Format HH:mm:ss)] saq-report benchmark ==" -ForegroundColor Cyan
Push-Location $saqRepo
try {
    node benchmark/benchmark-json.js --input=$env:SAMPLE --out="$env:RAW\benchmark\saq-report"
    if ($LASTEXITCODE -ne 0) { throw "benchmark-json.js gagal." }
} finally { Pop-Location }

# --- lambat (jam) ---
Run-Export "session_benchmark"
Run-Export "span_iso_benchmark"

# --- audit ---
Write-Host "`n== [$(Get-Date -Format HH:mm:ss)] Audit artefak ==" -ForegroundColor Cyan
python "$workspace\research\audit_raw.py" --raw $env:RAW
if ($LASTEXITCODE -ne 0) {
    throw "audit_raw menemukan pelanggaran."
}

Write-Host "`nSelesai. Artefak: $env:RAW\benchmark (ze_json + saq-report)" -ForegroundColor Green
