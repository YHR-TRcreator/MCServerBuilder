import os
import platform
import subprocess
import re
from common.logger import logger


def get_system_info() -> dict:
    """获取系统基础信息：系统类型、架构"""
    sys_type = platform.system().lower()
    arch = platform.machine().lower()
    if arch in ["amd64", "x86_64"]:
        arch = "x86_64"
    elif arch in ["arm64", "aarch64"]:
        arch = "aarch64"

    return {
        "os": sys_type,
        "arch": arch,
        "is_admin": check_admin()
    }


def check_admin() -> bool:
    try:
        if platform.system() == "Windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        else:
            return os.getuid() == 0
    except:
        return False


def scan_local_java() -> list:
    """扫描本机所有可用Java，返回 [{path, version, major}]"""
    java_list = []
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            shell=True
        )
        output = result.stderr
        match = re.search(r'"(\d+\.\d+\.\d+)|"(\d+)', output)
        if match:
            ver_str = match.group(0).strip('"')
            if ver_str.startswith("1.8"):
                major = 8
            else:
                major = int(ver_str.split(".")[0])
            # 获取java路径简化方案（后续可优化）
            java_list.append({
                "path": "java",
                "version": ver_str,
                "major": major
            })
    except Exception as e:
        logger.warning(f"全局java未检测到：{e}")
    return java_list


def get_java_requirement(mc_version: str) -> int:
    """根据MC游戏版本，返回所需Java主版本"""
    from common.constants import MC_JAVA_MATCH_RULE
    version_map = sorted([k for k in MC_JAVA_MATCH_RULE.keys() if k != "default"], reverse=True)
    for v_key in version_map:
        if mc_version.startswith(v_key):
            return MC_JAVA_MATCH_RULE[v_key]
    return MC_JAVA_MATCH_RULE["default"]