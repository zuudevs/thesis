@echo off

for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"

set "PROJECT_ROOT_DIR=%PROJECT_ROOT%"
set "TOOLCHAINS_DIR=%PROJECT_ROOT%\.toolchains"
set "CORPUS_DIR=%PROJECT_ROOT%\corpus"
set "OUT_DIR=%PROJECT_ROOT%\out"
set "VCPKG_VISUAL_STUDIO_PATH=%TOOLCHAINS_DIR%\MSVC"

set "MSVC_BIN_DIR="
if exist "%TOOLCHAINS_DIR%\MSVC\VC\Tools\MSVC\" (
    for /d %%V in ("%TOOLCHAINS_DIR%\MSVC\VC\Tools\MSVC\*") do (
        set "MSVC_BIN_DIR=%%V\bin\Hostx64\x64"
    )
)

if defined TOOLCHAINS_DIR (
    set "PATH=%TOOLCHAINS_DIR%;%TOOLCHAINS_DIR%\cmake-4.4.5-windows-x86_64\bin;%TOOLCHAINS_DIR%\clang+llvm-23.1.5-x86_64-pc-windows-msvc\bin;%TOOLCHAINS_DIR%\vcpkg-2026.10.16;%MSVC_BIN_DIR%;%PATH%"
)

echo [+] Environment variables injected!
echo     PROJECT_ROOT_DIR : %PROJECT_ROOT_DIR%
echo     TOOLCHAINS_DIR   : %TOOLCHAINS_DIR%
echo     CORPUS_DIR       : %CORPUS_DIR%
echo     OUT_DIR          : %OUT_DIR%
echo     MSVC_BIN_DIR     : %MSVC_BIN_DIR%