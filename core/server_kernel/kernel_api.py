from core.downloader.base_downloader import BaseDownloader
from common.exceptions import NetworkFetchError
from common.logger import logger


class KernelAPIClient:
    def __init__(self):
        self.downloader = BaseDownloader()

    def fetch_version_list(self, kernel_type: str):
        """拉取内核版本列表，【API地址占位】"""
        try:
            # api_url = constants内{{SOURCE_URL}}拼接地址
            api_url = ""
            # resp = requests.get(api_url)
            # return 解析后的版本列表
            return []
        except Exception as e:
            logger.error(f"内核版本列表拉取失败 {kernel_type}:{e}")
            raise NetworkFetchError()

    def get_download_url(self, kernel_type: str, game_version: str, build: str):
        """获取指定内核版本jar下载链接，占位"""
        return ""