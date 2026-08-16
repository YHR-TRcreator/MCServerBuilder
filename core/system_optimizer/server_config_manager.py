# -*- coding: utf-8 -*-
"""
服务配置管理器
功能：读写服务json配置、同步内存参数至Forge专用user_jvm_args.txt、修改run.bat内存
修复补充：补齐 load_all_server_configs() 用于扫描全部实例；兼容Path路径；增强异常保护
"""
import os
import json
import re
from pathlib import Path
from typing import Optional, Dict, List
from common.logger import logger

CONFIG_NAME = "server_config.json"


class ServerConfigManager:
    @staticmethod
    def create_default_config(server_name: str, server_dir: str, java_path: str, recommend_max_gb: int) -> Dict:
        """生成默认配置模板"""
        return {
            "server_name": server_name,
            "java_path": java_path,
            "min_memory_gb": max(2, recommend_max_gb // 2),
            "max_memory_gb": recommend_max_gb,
            "server_port": 25565,
            "jvm_args": "-XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 -XX:+UnlockExperimentalVMOptions -XX:+EnableJVMCI -XX:+UseJVMCICompiler"
        }

    @staticmethod
    def load_config(server_dir) -> Optional[Dict]:
        """加载配置，文件不存在返回None，兼容str / Path输入"""
        server_dir = Path(server_dir)
        cfg_path = server_dir / CONFIG_NAME
        if not cfg_path.exists():
            return None
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取配置失败 {cfg_path} : {e}")
            return None

    @staticmethod
    def save_config(server_dir, config_data: dict):
        """保存json配置，兼容str / Path输入"""
        server_dir = Path(server_dir)
        server_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = server_dir / CONFIG_NAME
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"保存配置失败 {cfg_path}: {e}")
            raise

    @staticmethod
    def load_all_server_configs(servers_root_dir) -> List[Dict]:
        """
        【新增关键函数】扫描servers根目录，读取全部服务实例配置
        mc_server_service.list_all_servers() 依赖这个方法！
        """
        servers_root_dir = Path(servers_root_dir)
        result_list = []
        if not servers_root_dir.exists():
            return result_list
        # 遍历一级子文件夹，每个子文件夹视作一个服务实例
        for sub_dir in servers_root_dir.iterdir():
            if sub_dir.is_dir():
                cfg = ServerConfigManager.load_config(sub_dir)
                if cfg is not None:
                    result_list.append(cfg)
        return result_list

    @staticmethod
    def sync_jvm_args_to_txt(server_dir, config_data: dict):
        """
        将内存参数写入user_jvm_args.txt（Forge新版启动器专用）
        文件不存在自动创建
        """
        server_dir = Path(server_dir)
        txt_path = server_dir / "user_jvm_args.txt"
        xms = config_data["min_memory_gb"] * 1024
        xmx = config_data["max_memory_gb"] * 1024
        args_text = f"-Xms{xms}M -Xmx{xmx}M {config_data['jvm_args']}"
        try:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(args_text)
        except Exception as e:
            logger.warning(f"写入user_jvm_args.txt失败: {e}")

    @staticmethod
    def sync_memory_to_run_bat(server_dir, config_data: dict):
        """
        将内存参数同步到 run.bat（修改 -Xms -Xmx）
        run.bat 不存在则跳过
        """
        server_dir = Path(server_dir)
        bat_path = server_dir / "run.bat"
        if not bat_path.exists():
            return False
        try:
            with open(bat_path, "r", encoding="utf-8") as f:
                content = f.read()
            xms = config_data["min_memory_gb"] * 1024
            xmx = config_data["max_memory_gb"] * 1024
            # 替换内存参数
            content = re.sub(r"-Xms\d+[mM]", f"-Xms{xms}M", content)
            content = re.sub(r"-Xmx\d+[mM]", f"-Xmx{xmx}M", content)
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.warning(f"修改 run.bat 内存失败: {e}")
            return False