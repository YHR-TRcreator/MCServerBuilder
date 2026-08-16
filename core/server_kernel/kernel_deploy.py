import os
import asyncio
import subprocess
from common.constants import SERVER_ROOT_DIR, CACHE_DIR
from common.file_utils import ensure_dir, wait_eula_generated, patch_eula_file
from common.logger import logger


class DeployScheduler:
    def __init__(self):
        ensure_dir(SERVER_ROOT_DIR)
        ensure_dir(CACHE_DIR)

    def _match_java_version(self, mc_version: str) -> int:
        """根据MC版本匹配需要的Java主版本"""
        if mc_version >= "1.20.5":
            return 21
        elif mc_version >= "1.17":
            return 17
        return 8

    async def _run_cmd(self, cmd: list, cwd: str):
        """异步执行shell命令"""
        logger.info(f"执行命令：{' '.join(cmd)}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if stdout:
            logger.info(stdout.decode("utf-8", errors="ignore"))
        if stderr:
            logger.warning(stderr.decode("utf-8", errors="ignore"))
        return proc.returncode

    async def deploy_server(self, server_name: str, mc_version: str, kernel: str, memory_gb: int):
        # 简单服务名校验，禁止路径特殊字符
        invalid_chars = r'\/:*?"<>|'
        for c in server_name:
            if c in invalid_chars:
                logger.error(f"服务名包含非法字符 {c}，部署终止！")
                return

        # 临时限制：本次仅允许forge
        if kernel.lower() != "forge":
            logger.error("当前版本仅支持forge内核部署！其他内核暂未开发")
            return

        logger.info(f"===== 开始部署 Forge服务端 | {server_name} MC:{mc_version} =====")
        server_path = os.path.join(SERVER_ROOT_DIR, server_name)
        ensure_dir(server_path)

        # 1. Java版本匹配校验
        need_java = self._match_java_version(mc_version)
        logger.info(f"当前MC版本需要 Java {need_java}")
        # TODO：后续接入Java环境检测，无Java直接终止

        # 2. 【预留】下载 Forge Installer.jar
        logger.warning("【待实现下载模块】请手动将 forge-installer.jar 放入服务端目录：")
        logger.warning(server_path)
        logger.warning("文件名固定为 forge-installer.jar")
        input("放置完成后，按回车继续...")
        installer_path = os.path.join(server_path, "forge-installer.jar")
        if not os.path.exists(installer_path):
            logger.error("未找到 forge-installer.jar，部署终止！")
            return

        # 3. Forge官方静默安装服务端（直接运行jar，不解压！强制服务端模式，无GUI弹窗）
        install_cmd = ["java", "-jar", "forge-installer.jar", "--installServer"]
        ret_code = await self._run_cmd(install_cmd, cwd=server_path)
        if ret_code != 0:
            logger.error("Forge安装器执行失败！确认Java环境正常，jar包版本匹配")
            return

        # 4. 修复：生成正确Windows启动脚本 start.bat
        # Forge安装完成后会生成 run.bat，我们封装一层自定义内存参数的启动脚本
        bat_path = os.path.join(server_path, "start.bat")
        bat_content = f"""@echo off
java -Xmx{memory_gb}G -Xms{memory_gb}G -jar forge-server.jar nogui
pause
"""
        try:
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)
            logger.info(f"自定义启动脚本已生成：{bat_path}")
        except PermissionError:
            logger.error(f"权限不足，无法写入 {bat_path}，部署终止")
            return

        # 5. 首次启动触发生成eula，不使用start弹出新窗口；直接java后台运行一小段时间后杀死进程，避免弹窗闪退
        logger.info("首次后台运行触发生成eula协议文件")
        trigger_cmd = ["java", f"-Xmx{memory_gb}G", f"-Xms{memory_gb}G", "-jar", "forge-server.jar", "nogui"]
        proc = await asyncio.create_subprocess_exec(
            *trigger_cmd,
            cwd=server_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        # 只等待3秒，目的只是让它生成eula.txt，不需要完整启动服务器
        try:
            await asyncio.wait_for(proc.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()

        # 6. 等待eula.txt出现
        if not wait_eula_generated(server_path):
            logger.error("eula文件生成失败，请手动双击运行一次start.bat重试！")
            return

        # 7. 自动修改eula=true
        patch_eula_file(server_path)

        logger.info(f"\n🎉 Forge服务端部署全部完成！目录：{server_path}")
        logger.info("运行 start.bat 启动服务器")

    def get_all_servers(self) -> dict:
        """获取全部已部署服务端 dict[name:path]，供上层list_all_servers调用"""
        result = {}
        if not os.path.exists(SERVER_ROOT_DIR):
            return result
        for entry in os.scandir(SERVER_ROOT_DIR):
            if entry.is_dir():
                # 简单有效性判断：目录内存在 forge‑server.jar 才认定为有效服务端
                jar_check = os.path.join(entry.path, "forge-server.jar")
                if os.path.exists(jar_check):
                    result[entry.name] = entry.path
        return result