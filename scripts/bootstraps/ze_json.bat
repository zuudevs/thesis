@echo off
setlocal enabledelayedexpansion

for %%I in ("%~dp0..\..") do set "PROJECT_ROOT=%%~fI"

set "PROJECT_ROOT_DIR=%PROJECT_ROOT%"
set "TOOLCHAINS_DIR=%PROJECT_ROOT%\.toolchains"
set "TEMP_DIR=%PROJECT_ROOT%\.temp"

if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"
if not exist "%TOOLCHAINS_DIR%\llvm" mkdir "%TOOLCHAINS_DIR%\llvm"
if not exist "%TOOLCHAINS_DIR%\cmake" mkdir "%TOOLCHAINS_DIR%\cmake"
if not exist "%TOOLCHAINS_DIR%\ninja" mkdir "%TOOLCHAINS_DIR%\ninja"
if not exist "%TOOLCHAINS_DIR%\vcpkg" mkdir "%TOOLCHAINS_DIR%\vcpkg"
if not exist "%TOOLCHAINS_DIR%\MSVC" mkdir "%TOOLCHAINS_DIR%\MSVC"

echo [+] Downloading LLVM...
curl.exe -Lf -o "%TEMP_DIR%\llvm.tar.xz" https://github.com/llvm/llvm-project/releases/download/llvmorg-23.1.5/clang+llvm-23.1.5-x86_64-pc-windows-msvc.tar.xz
tar -xf "%TEMP_DIR%\llvm.tar.xz" -C "%TOOLCHAINS_DIR%\llvm" --strip-components=1

echo [+] Downloading CMake...
curl.exe -Lf -o "%TEMP_DIR%\cmake.zip" https://github.com/Kitware/CMake/releases/download/v4.4.5/cmake-4.4.5-windows-x86_64.zip
tar -xf "%TEMP_DIR%\cmake.zip" -C "%TOOLCHAINS_DIR%\cmake" --strip-components=1

echo [+] Downloading Ninja...
curl.exe -Lf -o "%TEMP_DIR%\ninja.zip" https://github.com/ninja-build/ninja/releases/download/v1.13.2/ninja-win.zip
tar -xf "%TEMP_DIR%\ninja.zip" -C "%TOOLCHAINS_DIR%\ninja"

echo [+] Downloading Vcpkg...
curl.exe -Lf -o "%TEMP_DIR%\vcpkg.zip" https://github.com/microsoft/vcpkg/archive/refs/tags/2026.10.16.zip
tar -xf "%TEMP_DIR%\vcpkg.zip" -C "%TOOLCHAINS_DIR%\vcpkg" --strip-components=1

echo [+] Downloading and Installing VS Build Tools...
curl.exe -Lf -o "%TEMP_DIR%\vs_buildtools.exe" https://aka.ms/vs/17/release/vs_buildtools.exe
"%TEMP_DIR%\vs_buildtools.exe" --quiet --wait --norestart --nocache --installPath "%TOOLCHAINS_DIR%\MSVC" --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --add Microsoft.VisualStudio.Component.Windows11SDK.22621

echo [+] Setup completed successfully!