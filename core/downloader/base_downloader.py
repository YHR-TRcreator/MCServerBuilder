import os
import aiohttp
from typing import Optional
from common.logger import logger

class BaseDownloader:
    @staticmethod
    async def _download_file(url: str, save_path: str) -> bool:
        """底层通用文件下载函数"""
        try:
            # 创建保存目录
            save_dir = os.path.dirname(save_path)
            os.makedirs(save_dir, exist_ok=True)

            timeout = aiohttp.ClientTimeout(total=300)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                logger.info(f"开始下载: {url}")
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning(f"链接访问失败，状态码:{resp.status}")
                        return False
                    
                    total_size = int(resp.headers.get("Content-Length", 0))
                    downloaded_size = 0
                    
                    with open(save_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            # 简易下载进度日志
                            if total_size > 0:
                                progress = round((downloaded_size / total_size) * 100, 1)
                                logger.info(f"下载进度 {progress}%")
            logger.info(f"文件下载完成，保存路径：{save_path}")
            return True
        except Exception as e:
            logger.error(f"下载异常: {str(e)}")
            return False

    @staticmethod
    async def download_forge_installer(mc_ver: str, forge_build: str, save_path: str) -> bool:
        """
        标准Maven路径下载Forge安装器
        模板：{仓库}/net/minecraftforge/forge/{mc_ver}-{forge_build}/forge-{mc_ver}-{forge_build}-installer.jar
        """
        dir_tag = f"{mc_ver}-{forge_build}"
        jar_name = f"forge-{dir_tag}-installer.jar"

        # BMCLAPI国内镜像（优先）
        mirror_url = f"https://bmclapi2.bangbang93.com/maven/net/minecraftforge/forge/{dir_tag}/{jar_name}"
        # 官方源备用
        official_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{dir_tag}/{jar_name}"

        logger.info(f"尝试国内镜像下载：{mirror_url}")
        if await BaseDownloader._download_file(mirror_url, save_path):
            return True

        logger.warning("镜像访问失败，切换官方源重试")
        logger.info(f"尝试官方源下载：{official_url}")
        return await BaseDownloader._download_file(official_url, save_path)