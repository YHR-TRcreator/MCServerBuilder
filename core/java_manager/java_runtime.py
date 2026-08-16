from core.downloader.base_downloader import BaseDownloader
from core.environment.sys_detector import scan_local_java, get_system_info
from common.constants import JAVA_STORAGE_DIR
from common.file_utils import ensure_dir, extract_archive
from common.exceptions import JavaNotFoundError
from common.logger import logger


class JavaManager:
    def __init__(self):
        self.downloader = BaseDownloader()
        self.sys_info = get_system_info()

    def find_usable_java(self, require_major: int):
        """查找本地满足版本需求的Java，返回路径，找不到抛出异常"""
        java_all = scan_local_java()
        for java in java_all:
            if java["major"] >= require_major:
                return java["path"]
        raise JavaNotFoundError(f"本地未找到Java{require_major}")

    def download_java_package(self, major_version: int, save_path: str):
        # 【链接占位】后续填入真实地址，当前保留空链接
        # download_url = 请求接口获取真实地址
        download_url = ""
        self.downloader.download(download_url, save_path)
        return save_path

    def install_java(self, archive_path: str, major_version: int) -> str:
        """解压安装Java，返回java.exe/java可执行文件路径"""
        ensure_dir(JAVA_STORAGE_DIR)
        target_dir = f"{JAVA_STORAGE_DIR}/java{major_version}"
        extract_archive(archive_path, target_dir)
        if self.sys_info["os"] == "windows":
            exe_path = f"{target_dir}/bin/java.exe"
        else:
            exe_path = f"{target_dir}/bin/java"
        logger.info(f"Java安装完成，路径:{exe_path}")
        return exe_path