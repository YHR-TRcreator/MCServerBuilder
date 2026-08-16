# -*- coding: utf-8 -*-
"""
service/mc_server_service.py
业务服务层，CLI/GUI统一调用
单向依赖core，不导入ui/gui，消灭循环导入
懒加载：第一次调用业务才加载core，避免导入阶段执行大量逻辑
"""
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
RUNTIME_DIR = PROJECT_ROOT / "runtime"
SERVERS_DIR = RUNTIME_DIR / "servers"

RUNTIME_DIR.mkdir(exist_ok=True, parents=True)
SERVERS_DIR.mkdir(exist_ok=True, parents=True)


class MCServerService:
    def __init__(self):
        self._inited = False
        self._inited_loop = None   # 保存asyncio事件循环，给GUI跨循环读取队列使用

        # 底层对象占位
        self.scheduler = None
        self._frp_mgr = None
        self.HardwareScanner = None
        self.ServerConfigManager = None
        self.ServerProcessWatcher = None
        self.CommandTerminal = None
        self.get_all_mc_versions = None
        self.get_forge_builds_by_mcver = None
        self.install_forge_server = None
        self.refresh_forge_cache = None

    def _lazy_init(self):
        """延迟初始化，真正要用的时候才加载core，移除get_running_loop()"""
        if self._inited:
            return

        # 删掉这里 self._inited_loop = asyncio.get_running_loop()
        # 改为：后续业务函数需要loop时再获取，不要初始化阶段强制拿loop

        from core.deploy_scheduler import DeployScheduler
        from core.downloader.forge_installer import (
            get_all_mc_versions,
            get_forge_builds_by_mcver,
            install_forge_server
        )
        from core.system_optimizer.hardware_scanner import HardwareScanner
        from core.system_optimizer.server_config_manager import ServerConfigManager
        from core.server_runtime.process_watcher import ServerProcessWatcher
        from core.server_runtime.command_terminal import CommandTerminal
        from core.forge_version_api import refresh_forge_cache
        from core.downloader import get_all_mc_versions, get_forge_builds_by_mcver, install_forge_server
        from core.frp.sakura_frp import SakuraFrpManager

        self.scheduler = DeployScheduler()
        # 全局唯一实例，一次性创建
        self._frp_mgr = SakuraFrpManager()

        self.HardwareScanner = HardwareScanner
        self.ServerConfigManager = ServerConfigManager
        self.ServerProcessWatcher = ServerProcessWatcher
        self.CommandTerminal = CommandTerminal

        self.get_all_mc_versions = get_all_mc_versions
        self.get_forge_builds_by_mcver = get_forge_builds_by_mcver
        self.install_forge_server = install_forge_server
        self.refresh_forge_cache = refresh_forge_cache
        self.get_quick_game_versions = get_all_mc_versions

        self._inited = True

        # 初始化完成后，尝试捕获当前运行loop（如果此时已经存在事件循环）
        try:
            self._inited_loop = asyncio.get_running_loop()
        except RuntimeError:
            # CLI环境此时没有loop，直接跳过，不抛异常
            self._inited_loop = None

    async def start_server(self, server_dir:str, config:dict, log_callback, status_callback=None):
        self._lazy_init()
        # 把log_callback、status_callback全部传给watcher
        watcher = self.ServerProcessWatcher(
            server_dir=server_dir,
            java_path=config.get("java_path","java"),
            jvm_args=config.get("jvm_args",[]),
            rcon_port=config.get("rcon_port",25575),
            rcon_password=config.get("rcon_password","mcpassword"),
            log_callback=log_callback,
            status_callback=status_callback
        )
        await watcher.start_server()
        return watcher

    async def stop_server(self, watcher):
        self._lazy_init()
        await watcher.stop_server(safe=True)

    async def send_server_command(self, watcher, cmd_text:str):
        self._lazy_init()
        return await watcher.send_command(cmd_text)

    # =========对外API=========
    def get_project_paths(self):
        """返回路径，给cli/gui使用"""
        self._lazy_init()
        return {
            "PROJECT_ROOT": PROJECT_ROOT,
            "RUNTIME_DIR": RUNTIME_DIR,
            "SERVERS_DIR": SERVERS_DIR
        }

    def get_all_servers(self) -> Dict[str, str]:
        self._lazy_init()
        return self.scheduler.get_all_servers()

    def get_hardware_info(self):
        self._lazy_init()
        # HardwareScanner全部为静态方法，直接类调用，不要实例化
        return self.HardwareScanner.get_hardware_info()

    def suggest_memory(self, total_gb, free_gb):
        """
        内存推荐对外接口
        :param total_gb:总内存GB
        :param free_gb:可用内存GB
        :return:推荐最大内存 MB
        """
        self._lazy_init()
        hw_cls = self.HardwareScanner
        # suggest_server_memory是静态方法，直接类调用，禁止 new()实例
        return hw_cls.suggest_server_memory(total_gb, free_gb)

    def create_default_config(self, server_name: str, server_path: str, java_path: str, max_gb: int):
        self._lazy_init()
        cfg_mgr = self.ServerConfigManager()
        return cfg_mgr.create_default_config(server_name, server_path, java_path, max_gb)

    def save_config(self, server_dir: str, cfg: Dict):
        self._lazy_init()
        cfg_mgr = self.ServerConfigManager()
        cfg_mgr.save_config(server_dir, cfg)

    def load_config(self, server_dir: str) -> Optional[Dict]:
        self._lazy_init()
        cfg_mgr = self.ServerConfigManager()
        return cfg_mgr.load_config(server_dir)

    def sync_jvm_args_txt(self, server_dir: str, cfg: Dict):
        self._lazy_init()
        cfg_mgr = self.ServerConfigManager()
        cfg_mgr.sync_jvm_args_to_txt(server_dir, cfg)

    def sync_memory_bat(self, server_dir: str, cfg: Dict):
        self._lazy_init()
        cfg_mgr = self.ServerConfigManager()
        cfg_mgr.sync_memory_to_run_bat(server_dir, cfg)

    async def deploy_vanilla_server(self,
                                    server_name: str,
                                    mc_version: str,
                                    kernel: str,
                                    memory_gb: int):
        """
        原版/Paper/Fabric部署入口，对齐CLI调用，只接收4个参数
        【不支持自定义目录、自定义Java】，固定使用SERVERS_DIR
        """
        self._lazy_init()
        await self.scheduler.deploy_server(
            server_name=server_name,
            mc_version=mc_version,
            kernel=kernel,
            memory_gb=memory_gb
        )

    def get_mc_version_list(self):
        self._lazy_init()
        return self.get_all_mc_versions()

    def get_forge_builds(self, mc_ver: str):
        self._lazy_init()
        return self.get_forge_builds_by_mcver(mc_ver)

    async def install_forge(self, server_path: str, mc_ver: str, build: str, java_exe: str, force_reinstall: bool) -> Tuple[bool, str]:
        self._lazy_init()
        return await self.install_forge_server(server_path, mc_ver, build, java_exe, force_reinstall)

    async def refresh_cache(self) -> bool:
        self._lazy_init()
        return await self.refresh_forge_cache()

    def get_quick_game_version_list(self):
        self._lazy_init()
        return self.get_quick_game_versions()

    def create_server_watcher_terminal(self, server_dir: str, java_path: str, jvm_args: List[str]):
        self._lazy_init()
        watcher = self.ServerProcessWatcher(server_dir, java_path, jvm_args)
        terminal = self.CommandTerminal(watcher)
        return watcher, terminal

    # ----------------------- SakuraFrp樱花映射封装【内存缓存模式】 -----------------------
    def _lazy_get_frp_manager(self):
        self._lazy_init()
        return self._frp_mgr

    def frp_load_config(self):
        mgr = self._lazy_get_frp_manager()
        return mgr.config

    def frp_save_config(self, cfg_dict: dict):
        mgr = self._lazy_get_frp_manager()
        mgr.config = cfg_dict
        mgr.save_config()

    async def frp_start(self):
        mgr = self._lazy_get_frp_manager()
        return await mgr.start()

    async def frp_stop(self):
        mgr = self._lazy_get_frp_manager()
        await mgr.stop()

    @property
    def frp_is_running(self):
        if self._frp_mgr is None:
            return False
        return self._frp_mgr._is_running

    async def frp_auto_download(self):
        mgr = self._lazy_get_frp_manager()
        return await mgr.auto_download_frpc()

    def frp_get_cached_logs(self):
        mgr = self._lazy_get_frp_manager()
        return mgr.get_cached_logs()
