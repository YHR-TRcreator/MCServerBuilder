# -*- coding: utf-8 -*-
"""
core/server_runtime/command_terminal.py
预制指令交互菜单（分类子菜单结构）
支持：天气时间、游戏模式、玩家管理、公告、服务器管理、物品 六大分类
"""
import re
from typing import Dict
from .process_watcher import ServerProcessWatcher


class CommandTerminal:
    def __init__(self, watcher: ServerProcessWatcher):
        self.watcher = watcher
        self._current_menu = "main"

    # ==================== 菜单定义 ====================

    def _get_menu_data(self) -> Dict[int, dict]:
        menus = {
            "main": {
                1: {"name": "🌤️  天气与时间控制", "action": "sub", "target": "weather"},
                2: {"name": "🎮  游戏模式切换", "action": "sub", "target": "gamemode"},
                3: {"name": "👥  玩家管理", "action": "sub", "target": "player"},
                4: {"name": "💬  聊天与公告", "action": "sub", "target": "chat"},
                5: {"name": "💾  服务器管理", "action": "sub", "target": "server"},
                6: {"name": "🎒  物品与经验", "action": "sub", "target": "item"},
                0: {"name": "🚪  退出指令面板", "action": "exit"},
            },
            "weather": {
                1: {"name": "☀️  晴天", "cmd": "weather clear", "need_input": False},
                2: {"name": "🌧️  下雨", "cmd": "weather rain", "need_input": False},
                3: {"name": "⛈️  雷雨", "cmd": "weather thunder", "need_input": False},
                4: {"name": "🌅  设置时间-白天", "cmd": "time set day", "need_input": False},
                5: {"name": "🌙  设置时间-夜晚", "cmd": "time set night", "need_input": False},
                6: {"name": "⏸️  时间锁定", "cmd": "gamerule doDaylightCycle false", "need_input": False},
                7: {"name": "▶️  时间恢复流动", "cmd": "gamerule doDaylightCycle true", "need_input": False},
                0: {"name": "⬅️  返回上级菜单", "action": "back"},
            },
            "gamemode": {
                1: {"name": "🟢  生存模式（指定玩家）", "cmd": "gamemode survival {player}", "need_input": True, "prompt": "输入玩家名："},
                2: {"name": "🔵  创造模式（指定玩家）", "cmd": "gamemode creative {player}", "need_input": True, "prompt": "输入玩家名："},
                3: {"name": "🟡  冒险模式（指定玩家）", "cmd": "gamemode adventure {player}", "need_input": True, "prompt": "输入玩家名："},
                4: {"name": "🟣  旁观模式（指定玩家）", "cmd": "gamemode spectator {player}", "need_input": True, "prompt": "输入玩家名："},
                0: {"name": "⬅️  返回上级菜单", "action": "back"},
            },
            "player": {
                1: {"name": "⭐  添加OP管理员", "cmd": "op {player}", "need_input": True, "prompt": "输入玩家名："},
                2: {"name": "🚫  移除OP权限", "cmd": "deop {player}", "need_input": True, "prompt": "输入玩家名："},
                3: {"name": "👢  踢出玩家", "cmd": "kick {player}", "need_input": True, "prompt": "输入玩家名："},
                4: {"name": "🔨  封禁玩家", "cmd": "ban {player}", "need_input": True, "prompt": "输入玩家名："},
                5: {"name": "🔓  解封玩家", "cmd": "pardon {player}", "need_input": True, "prompt": "输入玩家名："},
                6: {"name": "📋  查看在线玩家", "cmd": "list", "need_input": False},
                7: {"name": "📍  传送玩家到某地", "cmd": "tp {player} {x} {y} {z}", "need_input": True, "prompt": "格式：玩家名 x y z（空格分隔）：", "multi": True},
                8: {"name": "↔️  玩家A传送到玩家B", "cmd": "tp {playerA} {playerB}", "need_input": True, "prompt": "格式：玩家A 玩家B（空格分隔）：", "multi": True},
                9: {"name": "✅  添加白名单", "cmd": "whitelist add {player}", "need_input": True, "prompt": "输入玩家名："},
                10: {"name": "❌  移除白名单", "cmd": "whitelist remove {player}", "need_input": True, "prompt": "输入玩家名："},
                11: {"name": "🔒  开启白名单", "cmd": "whitelist on", "need_input": False},
                12: {"name": "🔓  关闭白名单", "cmd": "whitelist off", "need_input": False},
                0: {"name": "⬅️  返回上级菜单", "action": "back"},
            },
            "chat": {
                1: {"name": "📢  全体公告", "cmd": "say {msg}", "need_input": True, "prompt": "输入公告内容："},
                2: {"name": "💤  关闭聊天反馈", "cmd": "gamerule sendCommandFeedback false", "need_input": False},
                3: {"name": "💬  开启聊天反馈", "cmd": "gamerule sendCommandFeedback true", "need_input": False},
                0: {"name": "⬅️  返回上级菜单", "action": "back"},
            },
            "server": {
                1: {"name": "💾  保存世界数据", "cmd": "save-all", "need_input": False},
                2: {"name": "⏸️  关闭自动保存", "cmd": "save-off", "need_input": False},
                3: {"name": "▶️  开启自动保存", "cmd": "save-on", "need_input": False},
                4: {"name": "👁️  管理员隐身", "cmd": "effect give @s minecraft:invisibility 1000000 1 true", "need_input": False},
                5: {"name": "🐑  清除所有掉落物", "cmd": "kill @e[type=item]", "need_input": False},
                6: {"name": "⚡  设为和平难度", "cmd": "difficulty peaceful", "need_input": False},
                7: {"name": "🟢  设为简单难度", "cmd": "difficulty easy", "need_input": False},
                8: {"name": "🟡  设为普通难度", "cmd": "difficulty normal", "need_input": False},
                9: {"name": "🔴  设为困难难度", "cmd": "difficulty hard", "need_input": False},
                10: {"name": "🏠  设置世界出生点", "cmd": "setworldspawn", "need_input": False},
                0: {"name": "⬅️  返回上级菜单", "action": "back"},
            },
            "item": {
                1: {"name": "🎁  给予玩家物品", "cmd": "give {player} {item} {count}", "need_input": True, "prompt": "格式：玩家名 物品ID 数量（空格分隔）：", "multi": True},
                2: {"name": "⭐  给予玩家经验", "cmd": "xp add {player} {amount} levels", "need_input": True, "prompt": "格式：玩家名 等级数（空格分隔）：", "multi": True},
                3: {"name": "🧪  给予玩家效果", "cmd": "effect give {player} {effect} {duration} {amplifier}", "need_input": True, "prompt": "格式：玩家名 效果ID 时长(秒) 等级（空格分隔）：", "multi": True},
                4: {"name": "🗑️  清除玩家背包", "cmd": "clear {player}", "need_input": True, "prompt": "输入玩家名："},
                0: {"name": "⬅️  返回上级菜单", "action": "back"},
            },
        }
        return menus.get(self._current_menu, menus["main"])

    # ==================== 菜单展示 ====================

    def show_menu(self):
        menu_titles = {
            "main": "========== 🎮 服务指令控制面板 ==========",
            "weather": "========== 🌤️ 天气与时间 ==========",
            "gamemode": "========== 🎮 游戏模式 ==========",
            "player": "========== 👥 玩家管理 ==========",
            "chat": "========== 💬 聊天与公告 ==========",
            "server": "========== 💾 服务器管理 ==========",
            "item": "========== 🎒 物品与经验 ==========",
        }
        title = menu_titles.get(self._current_menu, "指令面板")
        print(f"\n{title}")

        menu_data = self._get_menu_data()
        for idx in sorted(menu_data.keys()):
            if idx == 0:
                continue
            item = menu_data[idx]
            print(f"  {idx}. {item['name']}")

        if 0 in menu_data:
            print(f"  0. {menu_data[0]['name']}")
        print("=" * 42)

    # ==================== 菜单交互 ====================

    async def handle_selection(self, select_num: int) -> str:
        """
        处理菜单选择
        :return: "continue" / "exit"
        """
        menu_data = self._get_menu_data()
        if select_num not in menu_data:
            print("❌ 无效选项！")
            return "continue"

        item = menu_data[select_num]
        action = item.get("action", "cmd")

        if action == "exit":
            return "exit"

        if action == "back":
            self._current_menu = "main"
            return "continue"

        if action == "sub":
            self._current_menu = item["target"]
            return "continue"

        if action == "cmd":
            cmd_template = item["cmd"]
            need_input = item.get("need_input", False)

            if need_input:
                prompt = item.get("prompt", "请输入参数：")
                user_input = input(prompt).strip()
                if not user_input:
                    print("⚠️ 输入不能为空！")
                    return "continue"

                if item.get("multi"):
                    parts = user_input.split()
                    placeholders = re.findall(r"\{(\w+)\}", cmd_template)
                    if len(parts) < len(placeholders):
                        print(f"⚠️ 参数不足！需要 {len(placeholders)} 个参数")
                        return "continue"
                    for i, ph in enumerate(placeholders):
                        cmd_template = cmd_template.replace("{" + ph + "}", parts[i])
                else:
                    placeholders = re.findall(r"\{(\w+)\}", cmd_template)
                    if placeholders:
                        cmd_template = cmd_template.replace("{" + placeholders[0] + "}", user_input)

            await self.watcher.send_command(cmd_template)
            return "continue"

        return "continue"

    def reset_to_main(self):
        """重置到主菜单层级"""
        self._current_menu = "main"