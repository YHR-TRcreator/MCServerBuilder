# -*- coding: utf-8 -*-
"""
core/server_runtime/process_watcher.py
Minecraft服务进程监控、启停、日志捕获、指令下发核心模块
指令下发使用 RCON 协议，不依赖 stdin 管道，Windows 稳定可用
"""
import asyncio
import os
import re
import subprocess
import shlex
from typing import Optional, List, Callable
from common.logger import logger
from .rcon_client import RconClient

# 进程状态常量
STATUS_STOPPED = "stopped"
STATUS_RUNNING = "running"
STATUS_CRASHED = "crashed"


class ServerProcessWatcher:
    def __init__(
        self, server_dir: str, java_path: str = "java", jvm_args: List[str] = None,
        rcon_port: int = 25575, rcon_password: str = "mcpassword",
        log_callback: Optional[Callable[[str], None]] = None,
        status_callback: Optional[Callable[[str], None]] = None
    ):
        self.server_dir = server_dir
        self.java_path = java_path
        self.jvm_args = jvm_args or []
        self.rcon_port = rcon_port
        self.rcon_password = rcon_password
        # 日志回调
        self.log_callback = log_callback
        # 状态变更回调：running / stopped / crashed
        self.status_callback = status_callback

        self.process: Optional[asyncio.subprocess.Process] = None
        self.status = STATUS_STOPPED
        self._log_task: Optional[asyncio.Task] = None
        self._start_mode = "bat_parsed"
        self.rcon: Optional[RconClient] = None

    def _set_status(self, new_status: str):
        """统一设置状态，同时触发回调"""
        self.status = new_status
        if self.status_callback is not None:
            self.status_callback(new_status)

    def _parse_run_bat(self) -> Optional[List[str]]:
        """解析 run.bat，提取 java 启动命令"""
        bat_path = os.path.join(self.server_dir, "run.bat")
        if not os.path.exists(bat_path):
            return None
        try:
            with open(bat_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return None

        for line in lines:
            line = line.strip()
            if not line or line.startswith("@") or line.startswith("rem ") or line.lower() == "pause":
                continue
            if re.match(r'^(java|javaw|".*java\.exe")\s', line, re.IGNORECASE):
                clean_line = line.lstrip("@").strip()
                try:
                    args = shlex.split(clean_line, posix=False)
                    return args
                except Exception:
                    return clean_line.split()
        return None

    def _find_server_jar(self) -> Optional[str]:
        for filename in os.listdir(self.server_dir):
            if filename.endswith(".jar") and filename.startswith("forge-") and "installer" not in filename.lower():
                return filename
        for filename in os.listdir(self.server_dir):
            if filename.endswith(".jar") and ("server" in filename.lower() or "paper" in filename.lower()):
                return filename
        return None

    def _enable_rcon_in_properties(self):
        """自动修改 server.properties 开启 RCON"""
        prop_path = os.path.join(self.server_dir, "server.properties")
        if not os.path.exists(prop_path):
            logger.warning("未找到 server.properties，跳过 RCON 自动配置")
            return

        try:
            with open(prop_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = []
            found_enable = False
            found_port = False
            found_password = False

            for line in lines:
                if line.startswith("enable-rcon="):
                    new_lines.append(f"enable-rcon=true\n")
                    found_enable = True
                elif line.startswith("rcon.port="):
                    new_lines.append(f"rcon.port={self.rcon_port}\n")
                    found_port = True
                elif line.startswith("rcon.password="):
                    new_lines.append(f"rcon.password={self.rcon_password}\n")
                    found_password = True
                else:
                    new_lines.append(line)

            if not found_enable:
                new_lines.append(f"enable-rcon=true\n")
            if not found_port:
                new_lines.append(f"rcon.port={self.rcon_port}\n")
            if not found_password:
                new_lines.append(f"rcon.password={self.rcon_password}\n")

            with open(prop_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            logger.info("✅ 已自动开启 RCON 配置")
        except Exception as e:
            logger.warning(f"修改 server.properties 失败: {e}")

    async def start_server(self) -> bool:
        if self.status == STATUS_RUNNING:
            logger.warning("服务已经处于运行状态，禁止重复启动！")
            return False

        # 启动前自动开启 RCON
        self._enable_rcon_in_properties()

        cmd: Optional[List[str]] = None
        bat_args = self._parse_run_bat()
        if bat_args:
            self._start_mode = "bat_parsed"
            cmd = bat_args
            logger.info(f"解析 run.bat 成功，使用 java 直接启动...")
        else:
            jar_name = self._find_server_jar()
            if jar_name is None:
                logger.error("❌ 解析 run.bat 失败，且找不到服务端 jar 文件！")
                return False
            self._start_mode = "jar_fallback"
            logger.info(f"使用 jar 兜底模式启动：{jar_name}")
            cmd = [self.java_path, *self.jvm_args, "-jar", jar_name, "nogui"]

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.server_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            self._set_status(STATUS_RUNNING)
            logger.info(f"✅ 服务启动成功，目录：{self.server_dir}")

            loop = asyncio.get_running_loop()
            self._log_task = loop.create_task(self._read_log_loop())
            loop.create_task(self._connect_rcon_delayed())

            return True

        except Exception as e:
            logger.error(f"❌ 服务启动失败: {str(e)}")
            self._set_status(STATUS_CRASHED)
            return False

    async def _connect_rcon_delayed(self):
        """延迟连接 RCON（等服务启动完成）"""
        # 最多尝试 60 秒
        for i in range(60):
            await asyncio.sleep(2)
            if self.status != STATUS_RUNNING:
                return
            self.rcon = RconClient("127.0.0.1", self.rcon_port, self.rcon_password)
            if self.rcon.connect():
                return
            self.rcon = None
        logger.warning("⚠️ 60秒内未能连接 RCON，指令功能可能不可用")

    async def _read_log_loop(self):
        if not self.process or not self.process.stdout:
            return
        while self.status == STATUS_RUNNING:
            try:
                line_bytes = await self.process.stdout.readline()
                if not line_bytes:
                    break
                line_text = line_bytes.decode(encoding="utf-8", errors="replace").strip()
                if line_text:
                    # CLI模式打印控制台
                    print(f"[服务日志] {line_text}")
                    # 同步回调
                    if self.log_callback is not None:
                        self.log_callback(line_text)
            except Exception as err:
                logger.warning(f"日志读取异常: {err}")
                await asyncio.sleep(0.2)

        return_code = await self.process.wait()
        if return_code == 0:
            self._set_status(STATUS_STOPPED)
            logger.info("✅ 服务正常关闭")
        else:
            self._set_status(STATUS_CRASHED)
            logger.error(f"❌ 服务意外崩溃，退出码:{return_code}")
        # 关闭 RCON
        if self.rcon:
            self.rcon.disconnect()
            self.rcon = None

    async def send_command(self, command: str) -> str:
        """
        发送控制台指令（优先 RCON，RCON 不可用则回退 stdin）
        :return: 指令执行结果（RCON 模式有返回值，stdin 模式无）
        """
        # 优先用 RCON
        if self.rcon and self.rcon.is_connected():
            result = self.rcon.send_command(command)
            logger.info(f"已下发指令：{command}")
            if result:
                print(f"[指令返回] {result}")
            return result

        # RCON 不可用，回退 stdin（可能不工作）
        if self.status != STATUS_RUNNING or self.process is None or self.process.stdin is None or self.process.stdin.is_closing():
            logger.warning("服务未运行/管道已关闭，且 RCON 未连接，无法发送指令！")
            return ""
        try:
            cmd_full = command.strip() + "\n"
            self.process.stdin.write(cmd_full.encode("utf-8"))
            await self.process.stdin.drain()
            logger.info(f"已下发指令（stdin模式）：{command}")
            return ""
        except (ConnectionResetError, BrokenPipeError):
            logger.error("管道连接已断开，服务可能已经停止！")
            self._set_status(STATUS_CRASHED)
            return ""

    async def stop_server(self, safe: bool = True):
        if self.status != STATUS_RUNNING or self.process is None:
            logger.info("当前没有正在运行的服务")
            return

        if safe:
            logger.info("正在执行安全关闭，发送 stop 指令...")
            await self.send_command("stop")
            try:
                await asyncio.wait_for(self.process.wait(), timeout=30)
            except asyncio.TimeoutError:
                logger.warning("安全关闭超时，准备强制终止进程")
                self.process.kill()
        else:
            logger.warning("执行强制杀死进程！")
            self.process.kill()

        await self.process.wait()
        self._set_status(STATUS_STOPPED)
        if self._log_task:
            self._log_task.cancel()
            try:
                await self._log_task
            except asyncio.CancelledError:
                pass
        if self.rcon:
            self.rcon.disconnect()
            self.rcon = None
        self.process = None
