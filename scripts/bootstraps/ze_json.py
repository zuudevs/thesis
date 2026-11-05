from os import getenv, path
import os
import subprocess
import tarfile
from zipfile import ZipFile
from urllib3 import PoolManager
from pathlib import Path
from dotenv import load_dotenv
import shutil

TOOLCHAINS_DIR = Path(getenv('TOOLCHAINS_DIR', '.toolchains')).resolve()
TEMP_DIR = Path(getenv('TEMP_DIR', '.temp')).resolve()

http = PoolManager()
load_dotenv()

def extract_archive(archive_path: Path, destination_path: Path):
    if archive_path.suffix == '.zip':
        with ZipFile(archive_path, 'r') as tar:
            tar.extractall(destination_path)
    elif archive_path.suffix in ['.xz', '.gz', '.bz2', '.zst']:
        with tarfile.open(archive_path, 'r:*') as tar:
            tar.extractall(destination_path)
    else:
        print(f"[-] Unsupported archive format: {archive_path.name}")

def install_from_github(repo: str, tag: str, package: str = None, force: bool = False, as_source: bool = False) -> Path | None:
    if package != None:
        download_path = TEMP_DIR / package
    elif as_source == True:
        download_path = TEMP_DIR / f"{repo.split('/')[-1]}-{tag}.zip"
    else:
        return
    
    if package:
        url = f"https://github.com/{repo}/releases/download/{tag}/{package}"
    elif as_source:
        url = f"https://github.com/{repo}/archive/refs/tags/{tag}.zip"
    else:
        return
        
    print(f"[+] Downloading from {url}")
            
    res = http.request('GET', url, preload_content=False)
        
    if res.status == 200:
        print(f"[+] Connection success! Saving to {download_path}")
        
        with open(download_path, 'wb') as w:
            shutil.copyfileobj(res, w)
        
        res.release_conn()
        
        print("[+] Download complete. Extracting archive...")
        
        extract_archive(download_path, TOOLCHAINS_DIR)
        
        print(f"[+] Extracted successfully to {TOOLCHAINS_DIR}")
        print(f"[+] Cleaning {TOOLCHAINS_DIR} archive!")
        
        os.remove(download_path)
        
        return TOOLCHAINS_DIR / download_path.name.replace('.' + package.split('.')[-1] if package else '.zip', '')
    else:
        print(f"[-] Failed! HTTP Status: {res.status}")
        res.release_conn()
        
def install_msvc_build_tools():
    url = "https://aka.ms/vs/17/release/vs_buildtools.exe"
    package = "vs_buildtools.exe"
    download_path = TEMP_DIR / package
    
    print(f"[+] Downloading MSVC Build Tools from {url}")
    res = http.request('GET', url, preload_content=False)
    
    if res.status == 200:
        with open(download_path, 'wb') as w:
            shutil.copyfileobj(res, w)
        res.release_conn()
        
        msvc_install_path = TOOLCHAINS_DIR / "MSVC"
        print(f"[+] Download complete. Running silent installer targeting {msvc_install_path}...")
        print("[!] This may take several minutes depending on network speed.")

        cmd = [
            str(download_path),
            "--quiet", "--wait", "--norestart", "--nocache",
            "--installPath", str(msvc_install_path),
            "--add", "Microsoft.VisualStudio.Workload.VCTools",
            "--add", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "--add", "Microsoft.VisualStudio.Component.Windows11SDK.22621"
        ]

        try:
            subprocess.run(cmd, check=True)
            print(f"[+] MSVC Build Tools installed successfully to {msvc_install_path}")
        except subprocess.CalledProcessError as e:
            print(f"[-] MSVC installation failed with return code {e.returncode}")
    else:
        print(f"[-] Failed to download MSVC installer! HTTP Status: {res.status}")
        res.release_conn()

def main():
    if not TOOLCHAINS_DIR.exists():
        TOOLCHAINS_DIR.mkdir(parents=True, exist_ok=True)
    if not TEMP_DIR.exists():
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    install_from_github(
        repo = r'llvm/llvm-project',
        tag = r'llvmorg-23.1.5',
        package = r'clang+llvm-23.1.5-x86_64-pc-windows-msvc.tar.xz'
    )
    
    install_from_github(
        repo = r'Kitware/CMake',
        tag = r'v4.4.5',
        package = r'cmake-4.4.5-windows-x86_64.zip'
    )
    
    install_from_github(
        repo = r'ninja-build/ninja',
        tag = r'v1.13.2',
        package = r'ninja-win.zip'
    )

    res = install_from_github(
        repo = r'microsoft/vcpkg',
        tag = r'2026.10.16',
        as_source = True
    )
    
    if res:
        vcpkg_bootstrap = res / 'bootstrap-vcpkg.bat'
        if vcpkg_bootstrap.exists():
            print(f"[+] Bootstrapping vcpkg from {vcpkg_bootstrap}")
            subprocess.run([str(vcpkg_bootstrap)], check=True)
    
    install_msvc_build_tools()

if __name__ == '__main__':
    main()