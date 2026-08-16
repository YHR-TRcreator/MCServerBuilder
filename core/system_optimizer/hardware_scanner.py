# -*- coding: utf-8 -*-
"""
core/system_optimizer/hardware_scanner.py
硬件检测、CPU分级、JVM内存自动优化模块
支持CPU关键词匹配 + exclude_list低功耗型号排除
无法识别CPU时，使用线程数量兜底判定档位
"""
import os
import json
import platform
import winreg
import psutil
from typing import Dict, Optional, Tuple

# 配置文件路径
CONFIG_FILE_PATH = "./runtime/cache/hardware_rank.json"


class HardwareScanner:
    @staticmethod
    def get_cpu_full_name() -> str:
        """Windows读取完整CPU型号，其他系统返回默认信息兜底"""
        cpu_name = "Unknown CPU"
        if platform.system() == "Windows":
            try:
                reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                cpu_name = winreg.QueryValueEx(reg_key, "ProcessorNameString")[0].strip()
                winreg.CloseKey(reg_key)
            except Exception:
                pass
        return cpu_name

    @staticmethod
    def get_hardware_info() -> Dict:
        """采集硬件原始信息：CPU型号、物理核心、逻辑线程、内存信息"""
        cpu_name = HardwareScanner.get_cpu_full_name()
        cpu_physical_cores = psutil.cpu_count(logical=False) or 2
        cpu_thread_count = psutil.cpu_count(logical=True)

        mem_data = psutil.virtual_memory()
        total_gb = round(mem_data.total / (1024 ** 3), 2)
        available_gb = round(mem_data.available / (1024 ** 3), 2)

        return {
            "cpu_name": cpu_name,
            "cpu_physical_cores": cpu_physical_cores,
            "cpu_threads": cpu_thread_count,
            "total_memory_gb": total_gb,
            "free_memory_gb": available_gb
        }

    @staticmethod
    def init_default_config():
        """配置文件不存在/损坏时自动生成默认hardware_rank.json"""
        default_config = {
            "rank_info": {
                "S": {
                    "rank_name": "S级｜高端旗舰处理器",
                    "description": "新一代线程撕裂者、新版霄龙EPYC、高端桌面i9/Ryzen9，单核多核性能强劲",
                    "max_server_amount": 4,
                    "single_server_max_player": 45,
                    "memory_min_mb": 4096,
                    "memory_max_mb": 8192,
                    "cpu_match_list": [
                        "Threadripper",
                        "EPYC 7642",
                        "EPYC 7742",
                        "EPYC 9654",
                        "EPYC 9754",
                        "i9-13900",
                        "i9-14900",
                        "Ryzen 9 7950X",
                        "Ryzen 9 9950X",
                        "Xeon Gold 63",
                        "Xeon Gold 64"
                    ],
                    "exclude_list": [
                        "i9-13900T",
                        "i9-14900T"
                    ]
                },
                "A": {
                    "rank_name": "A级｜中端主流处理器",
                    "description": "近代i5/i7、Ryzen5/Ryzen7，适合少量多开服务端",
                    "max_server_amount": 2,
                    "single_server_max_player": 28,
                    "memory_min_mb": 3072,
                    "memory_max_mb": 6144,
                    "cpu_match_list": [
                        "Ryzen 7 5700X",
                        "Ryzen 7 7700X",
                        "Ryzen 5 7600X",
                        "i7-12700",
                        "i7-10700",
                        "i5-13600K"
                    ],
                    "exclude_list": [
                        "i5-13600T",
                        "i7-12700T"
                    ]
                },
                "B": {
                    "rank_name": "B级｜入门家用处理器",
                    "description": "老款中端家用CPU，仅建议运行单台服务器",
                    "max_server_amount": 1,
                    "single_server_max_player": 16,
                    "memory_min_mb": 2048,
                    "memory_max_mb": 4096,
                    "cpu_match_list": [
                        "E3-1230",
                        "Ryzen 5 2600",
                        "i5-8400",
                        "i5-6500"
                    ],
                    "exclude_list": []
                },
                "C": {
                    "rank_name": "C级｜老旧平台/老式服务器CPU",
                    "description": "初代霄龙、老款至强E5、初代锐龙、老旧酷睿，单核性能偏弱（洋垃圾归类于此）",
                    "max_server_amount": 1,
                    "single_server_max_player": 8,
                    "memory_min_mb": 1536,
                    "memory_max_mb": 2048,
                    "cpu_match_list": [
                        "EPYC 7251",
                        "EPYC 7351",
                        "EPYC 7451",
                        "EPYC 7551",
                        "EPYC 7601",
                        "EPYC 7701",
                        "Xeon Gold 51",
                        "Xeon Gold 52",
                        "Xeon Gold 61",
                        "Xeon Gold 62",
                        "Xeon E5-2660 v2",
                        "Xeon X56",
                        "FX-8300"
                    ],
                    "exclude_list": []
                },
                "D": {
                    "rank_name": "D级｜极低性能老旧设备",
                    "description": "赛扬、奔腾、凌动、老旧低功耗笔记本，仅适合小型纯净单机服",
                    "max_server_amount": 1,
                    "single_server_max_player": 5,
                    "memory_min_mb": 1024,
                    "memory_max_mb": 1536,
                    "cpu_match_list": [
                        "Celeron",
                        "Pentium",
                        "Atom",
                        "i3-4130"
                    ],
                    "exclude_list": []
                }
            },
            "fallback_rule": {
                "comment": "无法识别CPU名称时，依靠逻辑线程数自动判定档位",
                "thread_ge32": "S",
                "thread_ge16": "A",
                "thread_ge8": "B",
                "thread_ge4": "C",
                "thread_lt4": "D"
            }
        }
        dir_path = os.path.dirname(CONFIG_FILE_PATH)
        os.makedirs(dir_path, exist_ok=True)
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)
        return default_config

    @staticmethod
    def load_rank_config() -> dict:
        """加载分级配置，文件丢失/损坏自动重建"""
        if not os.path.exists(CONFIG_FILE_PATH):
            return HardwareScanner.init_default_config()
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return HardwareScanner.init_default_config()

    @staticmethod
    def judge_cpu_rank(cpu_full_name: str, thread_count: int) -> Tuple[str, dict]:
        """
        CPU档位判定
        规则：从高等级S→D依次匹配，命中关键词后校验exclude_list排除项
        :return: 档位编码(S/A/B/C/D), 档位完整配置信息
        """
        cfg = HardwareScanner.load_rank_config()
        rank_info = cfg["rank_info"]
        fallback = cfg["fallback_rule"]
        cpu_name_low = cpu_full_name.lower()
        target_rank: Optional[str] = None

        rank_sequence = ["S", "A", "B", "C", "D"]
        for rank_code in rank_sequence:
            data = rank_info[rank_code]
            hit_keyword = False
            for keyword in data["cpu_match_list"]:
                if keyword.lower() in cpu_name_low:
                    hit_keyword = True
                    break
            if not hit_keyword:
                continue

            is_excluded = False
            exclude_words = data.get("exclude_list", [])
            for exclude_word in exclude_words:
                if exclude_word.lower() in cpu_name_low:
                    is_excluded = True
                    break
            if is_excluded:
                continue

            target_rank = rank_code
            break

        # 无匹配CPU型号，启用线程兜底策略
        if not target_rank:
            if thread_count >= 32:
                target_rank = fallback["thread_ge32"]
            elif thread_count >= 16:
                target_rank = fallback["thread_ge16"]
            elif thread_count >= 8:
                target_rank = fallback["thread_ge8"]
            elif thread_count >= 4:
                target_rank = fallback["thread_ge4"]
            else:
                target_rank = fallback["thread_lt4"]

        return target_rank, rank_info[target_rank]

    @staticmethod
    def suggest_server_memory(total_mem_gb: float, free_mem_gb: float) -> int:
        """
        智能推荐JVM内存(单位MB)
        限制：最多占用空闲内存70%，最低内存限制1024MB
        """
        safe_available_gb = free_mem_gb * 0.7
        if total_mem_gb <= 8:
            suggest_gb = 3
        elif total_mem_gb <= 16:
            suggest_gb = 6
        elif total_mem_gb <= 32:
            suggest_gb = 10
        else:
            suggest_gb = 12

        final_gb = min(suggest_gb, safe_available_gb)
        return max(1024, int(final_gb * 1024))

    @staticmethod
    def get_full_evaluation() -> Dict:
        """统一对外调用入口，一次性返回全部评估结果"""
        hardware_data = HardwareScanner.get_hardware_info()
        rank_code, rank_data = HardwareScanner.judge_cpu_rank(
            cpu_full_name=hardware_data["cpu_name"],
            thread_count=hardware_data["cpu_threads"]
        )
        recommend_memory = HardwareScanner.suggest_server_memory(
            total_mem_gb=hardware_data["total_memory_gb"],
            free_mem_gb=hardware_data["free_memory_gb"]
        )
        return {
            "hardware": hardware_data,
            "rank_code": rank_code,
            "rank_detail": rank_data,
            "recommend_memory_mb": recommend_memory
        }