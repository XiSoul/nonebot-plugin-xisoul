"""
Playwright 浏览器管理模块

自动检测 nonebot_plugin_htmlrender 是否可用：
- 如果已安装且浏览器已下载，直接复用 htmlrender 的 get_new_page
- 如果未安装或浏览器未下载，使用国内镜像源自动下载并管理独立的 Playwright 实例
"""

import os
import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Optional, AsyncIterator
from contextlib import asynccontextmanager

from nonebot import logger

# 国内 Playwright 下载镜像源（已测试可用，速度约 3MB/s）
PLAYWRIGHT_CN_MIRROR = "https://registry.npmmirror.com/-/binary/playwright"

# htmlrender 是否可用的缓存
_htmlrender_available: Optional[bool] = None
_htmlrender_get_new_page = None


def _check_htmlrender_browser_installed() -> bool:
    """检查 htmlrender 的 playwright 浏览器是否已下载"""
    try:
        # 检查常见的 playwright 浏览器缓存目录
        home = Path.home()
        possible_paths = [
            home / ".cache" / "ms-playwright",
            home / ".local" / "share" / "nonebot2",
            Path("/root/.cache/ms-playwright"),
            Path("/root/.local/share/nonebot2"),
        ]
        
        for cache_dir in possible_paths:
            if cache_dir.exists():
                # 检查是否有 chromium 相关目录
                for item in cache_dir.rglob("*chromium*"):
                    if item.is_dir():
                        # 检查目录下是否有可执行文件
                        for exe in item.rglob("chrome*"):
                            if exe.is_file() and os.access(exe, os.X_OK):
                                logger.debug(f"[XiSoul] 找到 htmlrender 浏览器: {exe}")
                                return True
        
        # 也检查 nonebot_plugin_htmlrender 的配置路径
        try:
            from nonebot_plugin_htmlrender.config import plugin_config
            if plugin_config.htmlrender_browser_executable_path:
                exe_path = Path(plugin_config.htmlrender_browser_executable_path)
                if exe_path.exists():
                    logger.debug(f"[XiSoul] 找到 htmlrender 配置的浏览器路径: {exe_path}")
                    return True
        except Exception:
            pass
            
        return False
    except Exception as e:
        logger.debug(f"[XiSoul] 检查 htmlrender 浏览器时出错: {e}")
        return False


def _try_import_htmlrender():
    """尝试导入 htmlrender 的 get_new_page"""
    global _htmlrender_available, _htmlrender_get_new_page
    
    if _htmlrender_available is not None:
        return _htmlrender_available
    
    try:
        # 尝试导入 htmlrender
        from nonebot_plugin_htmlrender import get_new_page
        
        # 检查浏览器是否已安装
        if _check_htmlrender_browser_installed():
            _htmlrender_get_new_page = get_new_page
            _htmlrender_available = True
            logger.info("[XiSoul] ✓ 检测到 nonebot_plugin_htmlrender 且浏览器已安装，将复用其 Playwright 实例")
            return True
        else:
            logger.info("[XiSoul] nonebot_plugin_htmlrender 已安装但浏览器未下载，将使用独立 Playwright")
            _htmlrender_available = False
            return False
    except ImportError:
        logger.info("[XiSoul] nonebot_plugin_htmlrender 未安装，将使用独立 Playwright")
        _htmlrender_available = False
        return False
    except Exception as e:
        logger.warning(f"[XiSoul] 检测 htmlrender 时出错: {e}，将使用独立 Playwright")
        _htmlrender_available = False
        return False


def _get_playwright_browser_dir() -> Path:
    """获取 Playwright 浏览器缓存目录"""
    # 优先使用插件自己的目录，避免与其他插件冲突
    plugin_dir = Path(__file__).parent
    browser_dir = plugin_dir / ".playwright-browsers"
    return browser_dir


def _is_playwright_browser_installed() -> bool:
    """检查独立 Playwright 浏览器是否已安装"""
    browser_dir = _get_playwright_browser_dir()
    if not browser_dir.exists():
        return False
    
    # 检查是否有 chromium 相关目录
    for item in browser_dir.rglob("*chromium*"):
        if item.is_dir():
            for exe in item.rglob("chrome*"):
                if exe.is_file() and os.access(exe, os.X_OK):
                    logger.debug(f"[XiSoul] 找到独立 Playwright 浏览器: {exe}")
                    return True
    return False


async def _install_playwright_browser():
    """使用国内镜像下载 Playwright 浏览器"""
    browser_dir = _get_playwright_browser_dir()
    browser_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"[XiSoul] 开始下载 Playwright Chromium 浏览器...")
    logger.info(f"[XiSoul] 使用国内镜像源: {PLAYWRIGHT_CN_MIRROR}")
    logger.info(f"[XiSoul] 下载目录: {browser_dir}")
    
    # 设置环境变量使用国内镜像
    env = os.environ.copy()
    env["PLAYWRIGHT_DOWNLOAD_HOST"] = PLAYWRIGHT_CN_MIRROR
    
    try:
        # 使用 playwright install 命令下载 chromium
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "playwright", "install", "chromium",
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(browser_dir.parent)
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info("[XiSoul] ✓ Playwright Chromium 浏览器下载成功")
            if stdout:
                logger.debug(f"[XiSoul] 下载输出: {stdout.decode()}")
            return True
        else:
            logger.error(f"[XiSoul] ✗ Playwright 浏览器下载失败 (返回码: {process.returncode})")
            if stderr:
                logger.error(f"[XiSoul] 错误信息: {stderr.decode()}")
            return False
    except Exception as e:
        logger.error(f"[XiSoul] ✗ 下载 Playwright 浏览器时出错: {e}")
        return False


# 独立 Playwright 实例管理
_playwright_instance = None
_browser_instance = None
_playwright_lock = asyncio.Lock()


async def _get_or_create_playwright():
    """获取或创建独立的 Playwright 实例"""
    global _playwright_instance, _browser_instance
    
    if _playwright_instance is not None and _browser_instance is not None:
        if _browser_instance.is_connected():
            return _playwright_instance, _browser_instance
        else:
            # 浏览器断开连接，重新创建
            await _cleanup_playwright()
    
    async with _playwright_lock:
        # 双重检查
        if _playwright_instance is not None and _browser_instance is not None:
            if _browser_instance.is_connected():
                return _playwright_instance, _browser_instance
        
        from playwright.async_api import async_playwright
        
        # 设置环境变量指向浏览器目录
        browser_dir = _get_playwright_browser_dir()
        env_bak = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_dir)
        
        try:
            _playwright_instance = await async_playwright().start()
            _browser_instance = await _playwright_instance.chromium.launch(headless=True)
            logger.info("[XiSoul] ✓ 独立 Playwright 实例启动成功")
            return _playwright_instance, _browser_instance
        except Exception as e:
            logger.error(f"[XiSoul] ✗ 启动 Playwright 失败: {e}")
            await _cleanup_playwright()
            raise
        finally:
            # 恢复环境变量
            if env_bak is not None:
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = env_bak
            elif "PLAYWRIGHT_BROWSERS_PATH" in os.environ:
                del os.environ["PLAYWRIGHT_BROWSERS_PATH"]


async def _cleanup_playwright():
    """清理独立 Playwright 实例"""
    global _playwright_instance, _browser_instance
    
    try:
        if _browser_instance:
            await _browser_instance.close()
    except Exception:
        pass
    try:
        if _playwright_instance:
            await _playwright_instance.stop()
    except Exception:
        pass
    
    _browser_instance = None
    _playwright_instance = None


@asynccontextmanager
async def get_new_page(**kwargs):
    """
    获取浏览器页面的上下文管理器
    
    自动选择最佳方案：
    1. 优先使用 nonebot_plugin_htmlrender（如果已安装且浏览器可用）
    2. 否则使用独立 Playwright 实例（自动下载浏览器）
    
    用法:
        async with get_new_page() as page:
            await page.goto("https://example.com")
            screenshot = await page.screenshot()
    """
    # 检查是否可以使用 htmlrender
    if _try_import_htmlrender():
        # 使用 htmlrender 的 get_new_page
        async with _htmlrender_get_new_page(**kwargs) as page:
            yield page
    else:
        # 使用独立 Playwright 实例
        # 确保浏览器已安装
        if not _is_playwright_browser_installed():
            success = await _install_playwright_browser()
            if not success:
                raise RuntimeError(
                    "Playwright 浏览器下载失败，请检查网络连接或手动安装。"
                    f"镜像源: {PLAYWRIGHT_CN_MIRROR}"
                )
        
        playwright, browser = await _get_or_create_playwright()
        
        # 合并默认参数
        page_kwargs = {"device_scale_factor": 2}
        page_kwargs.update(kwargs)
        
        page = await browser.new_page(**page_kwargs)
        try:
            yield page
        finally:
            await page.close()


# 插件关闭时清理资源
async def cleanup():
    """清理所有 Playwright 资源"""
    await _cleanup_playwright()
    logger.info("[XiSoul] Playwright 资源已清理")


# 导出
__all__ = ["get_new_page", "cleanup"]
