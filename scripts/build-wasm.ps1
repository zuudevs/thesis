# build-wasm.ps1 - deterministic optimized wasm64 build for ze_json.
#
# Why (P5 server finding): the wasm artifact shipped to the SAQ server was
# built via the CMake UI without picking the preset/options first, so the
# deployed file could be non-Release and/or without -msimd128. This script
# removes that variable: it forces the wasm64-release preset (Release +
# -msimd128 via src/CMakeLists.txt), builds, then VERIFIES the artifact
# before you copy it anywhere:
#
#   1. CMakeCache build type is Release (and the preset was used).
#   2. ABI exports present: scanner surface (v2) + parser surface (v3).
#   3. SIMD actually used: v128 instructions found in the disassembly
#      (llvm-objdump) - a non-simd build would print only scalar ops.
#   4. sha256 written next to the artifact (ze_json.wasm.sha256) so the
#      server side can record the provenance (P5 report gap).
#   5. Optional gates: JS differential test (node bindings/js/tests/*.mjs)
#      and the binding smoke test.
#
# Usage (from anywhere; it relocates itself):
#   powershell -File scripts\build-wasm.ps1                # full: build+verify+gates
#   powershell -File scripts\build-wasm.ps1 -Fresh         # also wipe build dir first
#   powershell -File scripts\build-wasm.ps1 -SkipGates     # build+verify only
# After it passes, copy bindings/js/ze_json.wasm (+ .sha256) to the target
# machine - the server runbook records the hash alongside the run_id.
param(
    [switch]$Fresh,
    [switch]$SkipGates
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

. (Join-Path $Root 'scripts\env\activate.ps1')
if (-not $env:VCPKG_VISUAL_STUDIO_PATH) {
    $env:VCPKG_VISUAL_STUDIO_PATH =
        'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools'
}

Set-Location (Join-Path $Root 'ze_json')
$BuildDir = Join-Path (Get-Location) 'build\wasm64-release'

if ($Fresh -and (Test-Path $BuildDir)) {
    Remove-Item -Recurse -Force $BuildDir
}

Write-Host '== configure (wasm64-release) ==' -ForegroundColor Cyan
cmake --preset wasm64-release
if ($LASTEXITCODE -ne 0) { throw 'configure failed' }

Write-Host '== build ==' -ForegroundColor Cyan
cmake --build $BuildDir
if ($LASTEXITCODE -ne 0) { throw 'build failed' }

$Wasm = Join-Path (Get-Location) 'bindings\js\ze_json.wasm'
if (-not (Test-Path $Wasm)) {
    throw "artifact missing: POST_BUILD copy did not produce $Wasm"
}

Write-Host '== verify ==' -ForegroundColor Cyan

# 1. build type straight from the cache the compiler actually used.
$CacheType = (Select-String -Path (Join-Path $BuildDir 'CMakeCache.txt') `
    -Pattern '^CMAKE_BUILD_TYPE:STRING=(.+)$').Matches[0].Groups[1].Value
if ($CacheType -ne 'Release') {
    throw "wrong build type '$CacheType' - the artifact is not the optimized build"
}
Write-Host "[ok] build type: $CacheType (preset wasm64-release)"

# 2. ABI exports (v2 scanner surface + v3 parser surface).
# NB: Windows PowerShell 5.1 has no Encoding::Latin1 - use code page 28591.
$Blob = [System.Text.Encoding]::GetEncoding(28591).GetString(
    [System.IO.File]::ReadAllBytes($Wasm))
$RequiredExports = @(
    'ze_abi_version', 'ze_alloc', 'ze_reset_heap',
    'ze_reference_scan', 'ze_scanner8', 'ze_structural_scan',
    'ze_parser_open', 'ze_parser_root', 'ze_parser_close'
)
foreach ($Name in $RequiredExports) {
    if ($Blob.IndexOf($Name, [System.StringComparison]::Ordinal) -lt 0) {
        throw "missing ABI export: $Name"
    }
}
Write-Host "[ok] ABI exports: $($RequiredExports.Count) required symbols present"

# 3. SIMD really used (v128.* in disassembly) - fails for a scalar-only build.
$Objdump = Join-Path $env:TOOLCHAINS_DIR 'llvm\bin\llvm-objdump.exe'
$SimdHit = & $Objdump -d $Wasm | Select-String 'v128\.' | Select-Object -First 1
if (-not $SimdHit) {
    throw 'no v128 instructions in disassembly - -msimd128 not in effect'
}
Write-Host "[ok] SIMD: v128 instructions present (e.g. $($SimdHit.Line.Trim().Split() | Select-Object -First 1))"

# 4. sha256 sidecar for provenance when copying to another machine.
# NB: Get-FileHash is unavailable in this PowerShell context - use .NET.
$Sha256 = [System.Security.Cryptography.SHA256]::Create()
$Hash = [System.BitConverter]::ToString(
    $Sha256.ComputeHash([System.IO.File]::ReadAllBytes($Wasm))).Replace('-', '').ToLower()
Set-Content -Path "$Wasm.sha256" -Value "$Hash  ze_json.wasm" -NoNewline
Write-Host "[ok] sha256: $Hash -> bindings/js/ze_json.wasm.sha256"

Write-Host ''
Write-Host ('artifact : {0} ({1:N0} bytes)' -f $Wasm, (Get-Item $Wasm).Length)
Write-Host ('sha256   : {0}' -f $Hash)

if (-not $SkipGates) {
    Write-Host '== gates ==' -ForegroundColor Cyan
    Set-Location $Root
    node ze_json\bindings\js\tests\differential.mjs
    if ($LASTEXITCODE -ne 0) { throw 'differential test failed' }
    node ze_json\bindings\js\tests\main.mjs
    if ($LASTEXITCODE -ne 0) { throw 'binding smoke failed' }
    Write-Host '[ok] differential + smoke gates passed'
}

Write-Host ''
Write-Host 'ready: copy bindings/js/ze_json.wasm (+ .sha256) to the target machine.' -ForegroundColor Green
