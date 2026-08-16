import os
import asyncio
from common.constants import SERVER_ROOT_DIR
from common.file_utils import ensure_dir
from common.logger import logger
from core.downloader.base_downloader import BaseDownloader


class DeployScheduler:
    def _match_java_version(self, mc_version: str) -> int:
        """根据MC版本匹配需要的Java主版本"""
        target_ver = 8
        if mc_version >= "1.20.5":
            target_ver = 21
        elif mc_version >= "1.17":
            target_ver = 17
        return target_ver

    async def _run_cmd(self, cmd: list[str], cwd: str) -> int:
        """
        异步执行shell/cmd命令
        :param cmd: 命令列表
        :param cwd: 工作目录
        :return: 进程退出码 0=成功
        """
        logger.info(f"执行命令: {' '.join(cmd)}  工作目录: {cwd}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            logger.info(f"命令输出:\n{stdout.decode('utf-8', errors='ignore')}")
        if stderr:
            logger.warning(f"命令错误输出:\n{stderr.decode('utf-8', errors='ignore')}")
        return proc.returncode

    async def deploy_server(self, server_name: str, mc_version: str, kernel: str, memory_gb: int):
        logger.info(f"开始部署服务端: {server_name} | {mc_version} | {kernel}")
        server_path = os.path.join(SERVER_ROOT_DIR, server_name)
        ensure_dir(server_path)

        # 内核限制：当前仅支持Forge
        if kernel.lower() != "forge":
            logger.error("当前部署器仅支持 Forge 内核！")
            return

        # =====【延迟导入】规避顶层循环导入，只在forge部署分支加载api =====
        from core.forge_version_api import get_quick_game_versions, get_recommended_forge_build

        # 读取短列表，校验版本有效性
        quick_version_list = get_quick_game_versions()
        if not quick_version_list:
            logger.error("未检测到Forge版本缓存！请先在CLI菜单执行【手动刷新Forge版本缓存】")
            return

        if mc_version not in quick_version_list:
            logger.error(f"输入MC版本 [{mc_version}] 不存在于Forge支持列表！")
            logger.info(f"可用版本：{quick_version_list}")
            return

        # 匹配所需Java版本
        need_java = self._match_java_version(mc_version)
        logger.info(f"该MC版本需要 Java {need_java}")

        # 1. 获取推荐Forge构建号
        forge_build = get_recommended_forge_build(mc_version)
        if not forge_build:
            logger.error("无法获取对应Forge构建号，终止部署！")
            return
        logger.info(f"自动选用推荐Forge构建号：{forge_build}")

        # 2. 下载 Forge Installer
        installer_path = os.path.join(server_path, "forge-installer.jar")
        download_ok = await BaseDownloader.download_forge_installer(mc_version, forge_build, installer_path)
        if not download_ok:
            logger.error("Forge安装包下载失败！")
            return

        # 3. 静默运行Forge安装程序，生成服务端文件
        logger.info("正在执行Forge静默安装......")
        install_cmd = ["java", "-jar", "forge-installer.jar", "--installServer"]
        ret_code = await self._run_cmd(install_cmd, cwd=server_path)
        if ret_code != 0:
            logger.error("Forge服务端安装失败，请检查Java环境！")
            return

        # 4. 生成Windows启动脚本start.bat
        bat_path = os.path.join(server_path, "start.bat")
        bat_content = f"""@echo off
java -Xmx{memory_gb}G -Xms{memory_gb}G -jar *.jar nogui
pause
"""
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        logger.info(f"✅部署完成！服务端目录：{server_path}")
        logger.info(f"✅启动脚本位置：{bat_path}")

    def get_all_servers(self) -> dict:
        """获取全部已部署服务端"""
        result = {}
        if not os.path.exists(SERVER_ROOT_DIR):
            return result
        for entry in os.scandir(SERVER_ROOT_DIR):
            if entry.is_dir():
                result[entry.name] = entry.path
        return result