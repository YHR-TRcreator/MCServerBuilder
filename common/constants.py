# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# 兼容源码运行 / Pyinstaller打包EXE，自动获取程序根目录
if getattr(sys, 'frozen', False):
    # 打包exe模式：根目录 = exe所在文件夹
    APP_ROOT = Path(sys.executable).parent.resolve()
else:
    # 源码开发模式：constants.py 上级两层 = 项目根目录
    APP_ROOT = Path(__file__).parent.parent.resolve()

# 运行目录配置（全部基于绝对根路径拼接，抛弃相对路径 ./）
SERVER_ROOT_DIR = str(APP_ROOT / "runtime" / "servers")
CACHE_DIR = str(APP_ROOT / "runtime" / "cache")
LOG_DIR = str(APP_ROOT / "runtime" / "logs")
JAVA_STORAGE_DIR = str(APP_ROOT / "runtime" / "java")
# 统一为 tmp_download，和项目其余代码保持一致，不要用temp
TEMP_DOWNLOAD_DIR = str(APP_ROOT / "runtime" / "tmp_download")

# Forge下载URL模板
FORGE_MAVEN_TPL = "https://maven.minecraftforge.net/net/minecraftforge/forge/{full_ver}/forge-{full_ver}-installer.jar"
FORGE_BMCLAPI_TPL = "https://bmclapi2.bangbang93.com/maven/net/minecraftforge/forge/{full_ver}/forge-{full_ver}-installer.jar"
FORGE_VERSION_API = "https://bmclapi2.bangbang93.com/forge/list?mcversion={mc_ver}"

# 缓存文件完整绝对路径
FULL_CACHE_FILE = str(Path(CACHE_DIR) / "forge_cache.json")
