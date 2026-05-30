"""
依赖自动安装模块

在插件 __init__.py 最顶部调用 ensure_deps()，功能：
- 检测缺失的 Python 依赖，自动 pip install
- 检测 Playwright 浏览器是否已安装，未安装则自动下载（使用国内镜像）
- 使用 .deps_installed 标记文件避免每次启动都检查
- 使用 subprocess 调用 pip，不使用 importlib

用法（在 __init__.py 最顶部，所有其他 import 之前）：
    from .deps_installer import ensure_deps
    ensure_deps()
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# 标记文件路径（放在插件目录下）
_MARKER_FILE = Path(__file__).parent / ".deps_installed"

# 需要安装的 Python 依赖
REQUIRED_PACKAGES = [
    "nonebot2>=2.0.0",
    "nonebot-adapter-onebot>=2.3.0",
    "nonebot-plugin-apscheduler>=0.1.2",
    "httpx>=0.23.0",
]

# Playwright 国内镜像源
PLAYWRIGHT_MIRROR = "https://registry.npmmirror.com/-/binary/playwright"


def _log(msg: str):
    """统一日志输出"""
    print(f"[XiSoul-Deps] {msg}")


def _get_python_executable() -> str:
    """获取当前 Python 解释器路径"""
    return sys.executable


def _pip_install(packages: list[str]) -> bool:
    """使用 subprocess 调用 pip 安装依赖"""
    python_exe = _get_python_executable()
    _log(f"正在安装缺失依赖: {', '.join(packages)}")

    try:
        result = subprocess.run(
            [python_exe, "-m", "pip", "install", "--quiet", "--no-warn-script-location"]
            + packages,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            _log("Python 依赖安装成功")
            return True
        else:
            _log(f"pip 安装失败 (返回码 {result.returncode}): {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        _log("pip 安装超时（120秒）")
        return False
    except Exception as e:
        _log(f"pip 安装异常: {e}")
        return False


def _check_missing_packages() -> list[str]:
    """检查哪些包未安装或版本不满足要求，返回缺失列表"""
    python_exe = _get_python_executable()
    missing = []

    for pkg_spec in REQUIRED_PACKAGES:
        # 提取包名（去掉版本约束）
        pkg_name = pkg_spec.split(">=")[0].split("==")[0].split("<=")[0].split("~=")[0]
        try:
            result = subprocess.run(
                [python_exe, "-c", f"import {pkg_name.replace('-', '_')}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                missing.append(pkg_spec)
        except Exception:
            missing.append(pkg_spec)

    return missing


def _check_playwright_browser_installed() -> bool:
    """检查 Playwright Chromium 浏览器是否已安装"""
    # 检查插件目录下的独立浏览器
    plugin_dir = Path(__file__).parent
    browser_dir = plugin_dir / ".playwright-browsers"
    if browser_dir.exists():
        for item in browser_dir.rglob("*chromium*"):
            if item.is_dir():
                for exe in item.rglob("chrome*"):
                    if exe.is_file() and os.access(exe, os.X_OK):
                        return True

    # 检查系统级 playwright 浏览器缓存
    home = Path.home()
    possible_paths = [
        home / ".cache" / "ms-playwright",
        home / ".local" / "share" / "ms-playwright",
        Path("/root/.cache/ms-playwright"),
    ]
    for cache_dir in possible_paths:
        if cache_dir.exists():
            for item in cache_dir.rglob("*chromium*"):
                if item.is_dir():
                    for exe in item.rglob("chrome*"):
                        if exe.is_file() and os.access(exe, os.X_OK):
                            return True
    return False


def _install_playwright_browser() -> bool:
    """使用国内镜像下载 Playwright Chromium 浏览器"""
    python_exe = _get_python_executable()
    _log("开始下载 Playwright Chromium 浏览器（国内镜像）...")

    env = os.environ.copy()
    env["PLAYWRIGHT_DOWNLOAD_HOST"] = PLAYWRIGHT_MIRROR

    try:
        result = subprocess.run(
            [python_exe, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            env=env,
            timeout=300,  # 浏览器下载可能较慢
        )
        if result.returncode == 0:
            _log("Playwright Chromium 浏览器下载成功")
            return True
        else:
            _log(f"Playwright 浏览器下载失败 (返回码 {result.returncode}): {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        _log("Playwright 浏览器下载超时（300秒）")
        return False
    except Exception as e:
        _log(f"Playwright 浏览器下载异常: {e}")
        return False


def _load_marker() -> dict | None:
    """读取标记文件，返回已安装状态字典"""
    if not _MARKER_FILE.exists():
        return None
    try:
        return json.loads(_MARKER_FILE.read_text())
    except Exception:
        return None


def _save_marker(pip_ok: bool, playwright_ok: bool):
    """保存标记文件"""
    data = {
        "pip_deps": pip_ok,
        "playwright_browser": playwright_ok,
    }
    _MARKER_FILE.write_text(json.dumps(data, indent=2))


def ensure_deps():
    """
    确保所有依赖已安装。

    - 首次启动：检查并安装缺失的 pip 包 + Playwright 浏览器
    - 后续启动：读取标记文件，跳过已确认安装的部分
    - 可通过删除 .deps_installed 文件触发重新检查
    """
    marker = _load_marker()

    # 如果标记文件存在且全部成功，直接跳过
    if marker and marker.get("pip_deps") and marker.get("playwright_browser"):
        return

    pip_ok = marker.get("pip_deps", False) if marker else False
    playwright_ok = marker.get("playwright_browser", False) if marker else False

    # 第一步：检查并安装缺失的 Python 依赖
    if not pip_ok:
        missing = _check_missing_packages()
        if missing:
            _log(f"检测到缺失依赖: {missing}")
            pip_ok = _pip_install(missing)
        else:
            pip_ok = True

    # 第二步：检查并安装 Playwright 浏览器
    if not playwright_ok:
        # 先确保 playwright 包已安装
        try:
            subprocess.run(
                [_get_python_executable(), "-c", "import playwright"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception:
            _log("playwright 包未安装，先安装 playwright")
            pip_ok = _pip_install(["playwright"])

        if _check_playwright_browser_installed():
            playwright_ok = True
        else:
            playwright_ok = _install_playwright_browser()

    # 保存标记文件
    _save_marker(pip_ok, playwright_ok)
    _log(f"依赖检查完成: pip={pip_ok}, playwright={playwright_ok}")
