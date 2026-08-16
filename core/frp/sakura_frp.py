# -*- coding: utf-8 -*-
"""
core/frp/sakura_frp.py
樱花映射（SakuraFrp）内网穿透管理模块
官方启动格式：frpc.exe -f <访问密钥>:<隧道ID>
文档：https://doc.natfrp.com/frpc/manual
"""
import asyncio
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
import aiohttp
from common.logger import logger

# 项目根目录，解决相对路径错乱
BASE_DIR = Path(__file__).parent.parent.parent.resolve()
CONFIG_PATH = BASE_DIR / "runtime" / "config" / "sakura_frp.json"
# 自动下载保存路径
FRPC_SAVE_PATH = BASE_DIR / "runtime" / "bin" / "frpc.exe"
# SakuraFrp官方下载直链 windows amd64 frpc
FRPC_DOWNLOAD_URL = "https://nya.globalslb.net/natfrp/client/frpc/0.51.0-sakura-14/frpc_windows_amd64.exe"


class SakuraFrpManager:
    def __init__(self):
        self.config: Dict = self._load_config()
        self.process: Optional[asyncio.subprocess.Process] = None
        self._log_task: Optional[asyncio.Task] = None
        self._is_running = False
        # Qt读取内存日志缓存
        self.log_cache: List[str] = []

    def _load_config(self) -> Dict:
        """读取配置，没有文件返回默认模板"""
        default_config = {
            "frpc_path": "",
            "token": "",
            "tunnel_id": ""
        }
        if not CONFIG_PATH.exists():
            return default_config
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # 兼容旧配置，补全缺失key
            for k, v in default_config.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
        except Exception as e:
            logger.warning(f"读取sakura_frp配置失败: {e}")
            return default_config

    def save_config(self):
        """保存配置到json"""
        CONFIG_PATH.parent.mkdir(exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    @property
    def is_running(self) -> bool:
        return self._is_running

    def get_cached_logs(self) -> List[str]:
        return self.log_cache

    async def auto_download_frpc(self) -> tuple[bool, str]:
        """
        自动下载Windows‑amd64 frpc客户端
        :return: (成功bool, 消息文本)
        """
        try:
            FRPC_SAVE_PATH.parent.mkdir(exist_ok=True)
            timeout = aiohttp.ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(FRPC_DOWNLOAD_URL) as resp:
                    if resp.status != 200:
                        return False, f"下载失败，HTTP状态码:{resp.status}"
                    with open(str(FRPC_SAVE_PATH), "wb") as fw:
                        while chunk := await resp.content.read(65536):
                            fw.write(chunk)
            # 下载完成回填配置
            self.config["frpc_path"] = str(FRPC_SAVE_PATH)
            self.save_config()
            return True, f"保存至：{FRPC_SAVE_PATH}"
        except aiohttp.ClientError as e:
            logger.error(f"frpc下载网络异常 {e}")
            return False, f"网络异常：{str(e)}"
        except Exception as e:
            logger.error(f"frpc自动下载异常 {e}")
            return False, f"异常：{str(e)}，杀毒软件可能拦截文件保存"

    async def start(self) -> bool:
        """
        启动frpc，官方参数 -f token:tunnel_id
        :return: True=进程已拉起，False=参数错误/启动失败
        """
        if self._is_running and self.process is not None:
            logger.warning("frpc已经在运行，无需重复启动")
            return True

        frpc_path = self.config.get("frpc_path", "").strip()
        token = self.config.get("token", "").strip()
        tunnel_id = self.config.get("tunnel_id", "").strip()

        if not frpc_path or not Path(frpc_path).exists():
            logger.error("frpc路径不存在")
            return False
        if not token or not tunnel_id:
            logger.error("访问密钥或隧道ID为空，无法启动")
            return False

        cmd = [
            frpc_path,
            "-f",
            f"{token}:{tunnel_id}"
        ]

        logger.info(f"启动SakuraFrp，命令: {' '.join(cmd)}")
        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(Path(frpc_path).parent),
            )
            self._is_running = True
            self._log_task = asyncio.create_task(self._consume_log())
            return True
        except Exception as e:
            logger.error(f"启动frpc异常: {e}")
            self._is_running = False
            return False

    async def _consume_log(self):
        """循环读取frpc控制台日志，写入内存缓存"""
        if not self.process or not self.process.stdout:
            return
        try:
            while True:
                line_bytes = await self.process.stdout.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf‑8", errors="replace").rstrip()
                logger.info(f"[SakuraFrp] {line}")
                self.log_cache.append(line)
        except asyncio.CancelledError:
            logger.info("frpc日志任务被取消")
        except Exception as e:
            warn_msg = f"frpc日志读取异常 {e}"
            logger.warning(warn_msg)
            self.log_cache.append(warn_msg)
        finally:
            self._is_running = False
            self.process = None

    async def stop(self):
        """停止frpc进程"""
        if self.process is None:
            self._is_running = False
            return
        try:
            self.process.terminate()
            await self.process.wait()
        except ProcessLookupError:
            pass
        except Exception as e:
            logger.warning(f"停止frpc异常 {e}")
        if self._log_task is not None:
            self._log_task.cancel()
            try:
                await self._log_task
            except asyncio.CancelledError:
                pass
        self.process = None
        self._log_task = None
        self._is_running = False
        logger.info("SakuraFrp已停止")
