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
#   2. ABI exports present: scanner surface (v2) + parser surface (v3) -
#      all 21 ze_* functions from include/ze_json/abi/cabi.hpp.
#   3. SIMD actually used: v128 instructions found in the disassembly
#      (llvm-objdump) - a non-simd build would print only scalar ops.
#   4. sha256 written next to the artifact (ze_json.wasm.sha256) so the
#      server side can record the provenance (P5 report gap).
#   5. Binding gates: differential, smoke, and the lazy layer (ND-4).
#
# Usage (from anywhere; it relocates itself):
#   powershell -File scripts\build-wasm.ps1                # full: build+verify+gates
#   powershell -File scripts\build-wasm.ps1 -Fresh         # also wipe build dir first
#   powershell -File scripts\build-wasm.ps1 -SkipGates     # build+verify only
#   powershell -File scripts\build-wasm.ps1 -VerifyOnly    # no rebuild: verify the
#                                                          # existing artifact only
# After it passes, copy bindings/js/ze_json.wasm (+ .sha256) to the target
# machine - the server runbook records the hash alongside the run_id.
param(
    [switch]$Fresh,
    [switch]$SkipGates,
    [switch]$VerifyOnly
)

if ($Fresh -and $VerifyOnly) {
    throw '-Fresh and -VerifyOnly are mutually exclusive'
}

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
$Wasm = Join-Path (Get-Location) 'bindings\js\ze_json.wasm'

if (-not $VerifyOnly) {
    if ($Fresh -and (Test-Path $BuildDir)) {
        Remove-Item -Recurse -Force $BuildDir
    }

    Write-Host '== configure (wasm64-release) ==' -ForegroundColor Cyan
    cmake --preset wasm64-release
    if ($LASTEXITCODE -ne 0) { throw 'configure failed' }

    Write-Host '== build ==' -ForegroundColor Cyan
    cmake --build $BuildDir
    if ($LASTEXITCODE -ne 0) { throw 'build failed' }

    if (-not (Test-Path $Wasm)) {
        throw "artifact missing: POST_BUILD copy did not produce $Wasm"
    }
}
elseif (-not (Test-Path $Wasm)) {
    throw "-VerifyOnly: no artifact at $Wasm - run a build (without -VerifyOnly) first"
}

Write-Host '== verify ==' -ForegroundColor Cyan

# 1. build type straight from the cache the compiler actually used
#    (only meaningful right after a build; skipped in -VerifyOnly without it).
$CacheFile = Join-Path $BuildDir 'CMakeCache.txt'
if (Test-Path $CacheFile) {
    $CacheType = (Select-String -Path $CacheFile `
        -Pattern '^CMAKE_BUILD_TYPE:STRING=(.+)$').Matches[0].Groups[1].Value
    if ($CacheType -ne 'Release') {
        throw "wrong build type '$CacheType' - the artifact is not the optimized build"
    }
    Write-Host "[ok] build type: $CacheType (preset wasm64-release)"
}
else {
    Write-Host '[warn] no CMakeCache.txt next to the artifact - build-type check skipped'
}

# 2. ABI exports: the full v3 surface from include/ze_json/abi/cabi.hpp
#    (3 core + 5 scanner + 13 parser). A v2-era artifact (9 symbols) fails
#    here by design - the parser surface is part of the deployed contract.
# NB: Windows PowerShell 5.1 has no Encoding::Latin1 - use code page 28591.
$Blob = [System.Text.Encoding]::GetEncoding(28591).GetString(
    [System.IO.File]::ReadAllBytes($Wasm))
$RequiredExports = @(
    # core (3)
    'ze_abi_version', 'ze_alloc', 'ze_reset_heap',
    # scanner surface (5)
    'ze_reference_scan', 'ze_scanner8', 'ze_scanner64', 'ze_scanner128',
    'ze_structural_scan',
    # parser surface (13)
    'ze_parser_open', 'ze_parser_root', 'ze_parser_close',
    'ze_container_begin', 'ze_array_next', 'ze_object_next', 'ze_object_field',
    'ze_value_kind', 'ze_get_string', 'ze_get_number', 'ze_get_bool',
    'ze_is_null', 'ze_count_elements'
)
foreach ($Name in $RequiredExports) {
    if ($Blob.IndexOf($Name, [System.StringComparison]::Ordinal) -lt 0) {
        throw "missing ABI export: $Name"
    }
}
Write-Host "[ok] ABI exports: $($RequiredExports.Count) required symbols present (v3)"

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
    # ND-4: the lazy layer (L1/L2) rides the unchanged v3 surface - the same
    # parity contract the deployed artifact must uphold server-side.
    node ze_json\bindings\js\tests\lazy.mjs
    if ($LASTEXITCODE -ne 0) { throw 'lazy layer gate failed' }
    Write-Host '[ok] differential + smoke + lazy gates passed'
}

Write-Host ''
Write-Host 'ready: copy bindings/js/ze_json.wasm (+ .sha256) to the target machine.' -ForegroundColor Green