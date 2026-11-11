$ProjectRoot = (Resolve-Path "$PSScriptRoot\..\..").Path

$env:PROJECT_ROOT_DIR = "$ProjectRoot"
$env:TOOLCHAINS_DIR   = "$ProjectRoot\.toolchains"
$env:CORPUS_DIR       = "$ProjectRoot\corpus"
$env:OUT_DIR          = "$ProjectRoot\out"
$env:VCPKG_VISUAL_STUDIO_PATH = "$env:TOOLCHAINS_DIR\MSVC"

# Auto-detect MSVC version folder
$MsvcToolsBase = "$env:TOOLCHAINS_DIR\MSVC\VC\Tools\MSVC"
$MsvcBinDir = ""
if (Test-Path $MsvcToolsBase) {
    $MsvcVersionFolder = Get-ChildItem -Path $MsvcToolsBase -Directory | Select-Object -First 1
    if ($MsvcVersionFolder) {
        $MsvcBinDir = "$($MsvcVersionFolder.FullName)\bin\Hostx64\x64"
    }
}

if (-not [string]::IsNullOrWhiteSpace($env:TOOLCHAINS_DIR)) {
    $env:PATH = "$env:TOOLCHAINS_DIR;$env:TOOLCHAINS_DIR\cmake\bin;$env:TOOLCHAINS_DIR\clang\bin;$env:TOOLCHAINS_DIR\vcpkg;$env:TOOLCHAINS_DIR\ninja;$MsvcBinDir;$env:PATH"
}

Write-Host "[+] Environment variables injected to current terminal session!" -ForegroundColor Green
Write-Host "    PROJECT_ROOT_DIR : $env:PROJECT_ROOT_DIR" -ForegroundColor Gray
Write-Host "    TOOLCHAINS_DIR   : $env:TOOLCHAINS_DIR" -ForegroundColor Gray
Write-Host "    CORPUS_DIR       : $env:CORPUS_DIR" -ForegroundColor Gray
Write-Host "    OUT_DIR          : $env:OUT_DIR" -ForegroundColor Gray
Write-Host "    MSVC_BIN_DIR     : $MsvcBinDir" -ForegroundColor Gray