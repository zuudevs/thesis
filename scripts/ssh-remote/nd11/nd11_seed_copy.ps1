# ND-11: copy the 6 corpus seed files into the benchmark working copy of
# saq-report (gitignored) and print sha256 per file for manifest comparison.
# Production is not touched: these files are seed provenance only - the
# benchmark children read the live MongoDB store.
$ErrorActionPreference = 'Stop'
$src = 'D:\SKRIPSI\RAFI\sources\corpus\benchmarks\saq_payload_v1'
$dst = 'D:\SKRIPSI\RAFI\sources\saq-report'
$files = 'config_asisten.json', 'config_global.json', 'courses.json',
         'lecturers.json', 'reports.json', 'schedules.json'
foreach ($f in $files) {
    Copy-Item -Force (Join-Path $src $f) (Join-Path $dst $f)
    $h = (Get-FileHash -Algorithm SHA256 (Join-Path $dst $f)).Hash.ToLower()
    "sha256=$h  file=$f"
}
"git status root+submodule (tracked):"
git -C D:\SKRIPSI\RAFI\sources status --porcelain --untracked-files=no
git -C D:\SKRIPSI\RAFI\sources\saq-report status --porcelain --untracked-files=no
"done"
