# -*- coding: utf-8 -*-
"""
ui/cli_app.py
CLI交互主程序【迁移service版本】
职责：只负责终端输入输出，业务全部交给 service.MCServerService
禁止直接import core模块，GUI和CLI共用同一套service
已移除GUI切换功能，CLI为独立版本
"""
import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from service.mc_server_service import MCServerService


class CLIApp:
    def __init__(self):
        self.service = MCServerService()
        self.SERVERS_DIR = None

    async def run(self):
        # 事件循环已经启动，此时再调用service业务接口
        paths = self.service.get_project_paths()
        self.SERVERS_DIR = paths["SERVERS_DIR"]

        while True:
            print("\n==== MC服务端一键搭建工具 CLI模式 ====")
            print("========== 功能菜单 ==========")
            print("1. 新建Minecraft服务端")
            print("2. 查看已部署服务端列表 / 管理服务配置")
            print("3. 手动刷新Forge版本缓存")
            print("4. 启动/管理运行中服务（控制台+指令面板）")
            print("5. 🌐 内网穿透（樱花映射）")
            print("6. 退出程序")
            select = input("请输入功能序号：")

            if select == "1":
                await self._menu_deploy_server()
            elif select == "2":
                await self._menu_server_config()
            elif select == "3":
                await self._menu_refresh_cache()
            elif select == "4":
                await self._menu_server_console()
            elif select == "5":
                await self._menu_frp()
            elif select == "6":
                print("程序即将退出，再见！")
                break
            else:
                print("⚠️ 输入序号无效，请重新选择")

    # ==================== 菜单1：新建服务端 ====================
    async def _menu_deploy_server(self):
        print("\n---- 新建服务端向导 ----")
        print("内核类型选择：")
        print("1) vanilla / paper / fabric（通用原版系列）")
        print("2) forge（Forge模组端，独立安装流程）")
        type_choice = input("请输入序号(1/2)：").strip()

        if type_choice == "2":
            mc_versions = self.service.get_mc_version_list()
            if not mc_versions:
                print("⚠️ 暂无Forge版本缓存！请先执行【3.手动刷新Forge版本缓存】")
                return

            print("\n=== 可选MC版本列表 ===")
            for idx, v in enumerate(mc_versions):
                print(f"{idx+1}. {v}")
            try:
                sel_index = int(input("选择MC版本序号 > ")) - 1
                select_mc_ver = mc_versions[sel_index]
            except Exception:
                print("❌ 输入无效！")
                return

            build_list = self.service.get_forge_builds(select_mc_ver)
            if not build_list:
                print("❌ 该MC版本无可用Forge构建！")
                return
            print(f"\n=== {select_mc_ver} 可用Forge构建 ===")
            print("0.【推荐】自动选择最新构建")
            for idx, build_info in enumerate(build_list):
                b_num = build_info["version"]
                print(f"{idx+1}. Build ({b_num})")

            build_input = input("选择构建序号 > ").strip()
            if build_input == "0":
                target_build = build_list[0]["version"]
            else:
                try:
                    b_idx = int(build_input)-1
                    target_build = build_list[b_idx]["version"]
                except Exception:
                    print("❌ 输入错误！")
                    return
            server_folder = input("\n输入新服务端文件夹名称：").strip()
            server_path = str(self.SERVERS_DIR / server_folder)

            java_exe = input("输入java路径（直接回车使用系统默认java）：").strip()
            if not java_exe:
                java_exe = "java"

            confirm = input(f"\n确认安装：Forge {select_mc_ver} Build.{target_build}\n目录：{server_path}\n确认开始？(Y/N)")
            if confirm.lower() != "y":
                return

            print("\n========= Forge安装开始 ===========")
            ok, msg = await self.service.install_forge(server_path, select_mc_ver, target_build, java_exe, force_reinstall=False)
            print("\n========= Forge安装执行结束 =========\n")

            if not ok:
                if "已部署完整Forge服务端" in msg:
                    choose_force = input("检测目录已有完整服务端，是否覆盖强制重装？(Y/N)").strip().lower()
                    if choose_force == "y":
                        print("\n========= 强制重装开始 ===========")
                        ok2, msg2 = await self.service.install_forge(server_path, select_mc_ver, target_build, java_exe, force_reinstall=True)
                        print("\n" + msg2)
                        hw = self.service.get_hardware_info()
                        rec_memory_mb = self.service.suggest_memory(hw["total_memory_gb"], hw["free_memory_gb"])
                        rec_memory_gb = round(rec_memory_mb / 1024)
                        default_cfg = self.service.create_default_config(server_folder, server_path, java_exe, rec_memory_gb)
                        self.service.save_config(server_path, default_cfg)
                        self.service.sync_jvm_args_txt(server_path, default_cfg)
                        self.service.sync_memory_bat(server_path, default_cfg)
                        print("✅ 已自动生成服务配置并同步启动参数！")
                    else:
                        print("取消安装，返回主菜单")
                else:
                    print("\n" + msg)
            else:
                print("\n" + msg)
                hw = self.service.get_hardware_info()
                rec_memory_mb = self.service.suggest_memory(hw["total_memory_gb"], hw["free_memory_gb"])
                rec_memory_gb = round(rec_memory_mb / 1024)
                default_cfg = self.service.create_default_config(server_folder, server_path, java_exe, rec_memory_gb)
                self.service.save_config(server_path, default_cfg)
                self.service.sync_jvm_args_txt(server_path, default_cfg)
                self.service.sync_memory_bat(server_path, default_cfg)
                print("✅ 已自动生成服务配置并同步启动参数！")

        else:
            # vanilla/paper/fabric
            server_name = input("服务端文件夹名称：")
            version_list = self.service.get_quick_game_version_list()
            if not version_list:
                print("⚠️ 暂无版本缓存！请先执行【3.手动刷新Forge版本缓存】")
                return
            print("\n=== 支持的MC版本列表 ===")
            for v in version_list:
                print(f"- {v}")
            mc_version = input("请复制输入上方MC版本：").strip()

            print("内核类型可选: vanilla / paper / fabric")
            kernel = input("输入内核类型：")
            memory_gb_input = input("分配内存(单位GB，例: 4): ")
            try:
                memory_gb = int(memory_gb_input)
                await self.service.deploy_vanilla_server(server_name, mc_version, kernel, memory_gb)
                server_path = str(self.SERVERS_DIR / server_name)
                hw = self.service.get_hardware_info()
                rec_memory_mb = self.service.suggest_memory(hw["total_memory_gb"], hw["free_memory_gb"])
                rec_memory_gb = round(rec_memory_mb / 1024)
                final_memory = max(memory_gb, rec_memory_gb)
                default_cfg = self.service.create_default_config(server_name, server_path, "java", final_memory)
                self.service.save_config(server_path, default_cfg)
                print("✅ 已自动生成服务运行配置文件！")
            except ValueError:
                print("❌ 内存必须输入数字！")

    # ==================== 菜单2：服务配置管理 ====================
    async def _menu_server_config(self):
        server_dict = self.service.get_all_servers()
        print("\n=== 已部署服务端 ===")
        if not server_dict:
            print("暂无已部署服务端")
            return
        server_list = list(server_dict.items())
        for idx, (name, path) in enumerate(server_list):
            print(f"{idx+1}. {name} | 路径：{path}")

        try:
            sel_input = input("\n选择需要管理的服务序号（直接回车返回上级）：").strip()
            if not sel_input:
                return
            sel_idx = int(sel_input) - 1
            if sel_idx < 0 or sel_idx >= len(server_list):
                print("序号超出范围！")
                return
        except ValueError:
            print("输入非法！")
            return
        selected_name, selected_path = server_list[sel_idx]

        while True:
            print(f"\n==== 正在管理服务：{selected_name} ====")
            print("1. 查看本机硬件信息 & 获取推荐内存参数")
            print("2. 读取当前服务配置")
            print("3. 修改服务运行配置")
            print("4. 返回上级菜单")
            sub_opt = input("请选择操作：").strip()

            if sub_opt == "1":
                hw = self.service.get_hardware_info()
                rec_mem_mb = self.service.suggest_memory(hw["total_memory_gb"], hw["free_memory_gb"])
                rec_mem_gb = round(rec_mem_mb / 1024)
                print(f"\n【本机硬件信息】")
                print(f"CPU型号：{hw['cpu_name']}")
                print(f"CPU逻辑核心：{hw['cpu_threads']}")
                print(f"整机总内存：{hw['total_memory_gb']:.2f} GB")
                print(f"当前可用内存：{hw['free_memory_gb']:.2f} GB")
                print(f"\n✅ 推荐最大分配内存：{rec_mem_gb} GB（预留系统资源）")

            elif sub_opt == "2":
                cfg = self.service.load_config(selected_path)
                if cfg is None:
                    print("⚠️ 未找到配置文件，将自动生成默认配置！")
                    hw = self.service.get_hardware_info()
                    rec_mem_mb = self.service.suggest_memory(hw["total_memory_gb"], hw["free_memory_gb"])
                    rec_mem_gb = round(rec_mem_mb / 1024)
                    cfg = self.service.create_default_config(selected_name, selected_path, "java", rec_mem_gb)
                    self.service.save_config(selected_path, cfg)
                    txt_path_check = os.path.join(selected_path, "user_jvm_args.txt")
                    if os.path.exists(txt_path_check):
                        self.service.sync_jvm_args_txt(selected_path, cfg)
                    bat_path_check = os.path.join(selected_path, "run.bat")
                    if os.path.exists(bat_path_check):
                        self.service.sync_memory_bat(selected_path, cfg)
                print("\n==== 当前服务配置 ====")
                for k, v in cfg.items():
                    print(f"{k} : {v}")

            elif sub_opt == "3":
                cfg = self.service.load_config(selected_path)
                if cfg is None:
                    print("⚠️ 配置不存在，自动创建默认配置！")
                    hw = self.service.get_hardware_info()
                    rec_mem_mb = self.service.suggest_memory(hw["total_memory_gb"], hw["free_memory_gb"])
                    rec_mem_gb = round(rec_mem_mb / 1024)
                    cfg = self.service.create_default_config(selected_name, selected_path, "java", rec_mem_gb)

                print("\n直接回车=保留原值")
                new_java = input(f"Java路径[{cfg['java_path']}]：").strip() or cfg["java_path"]
                new_min_mem = input(f"最小内存GB[{cfg['min_memory_gb']}]：").strip()
                new_max_mem = input(f"最大内存GB[{cfg['max_memory_gb']}]：").strip()
                new_port = input(f"服务端口[{cfg['server_port']}]：").strip()
                new_jvm = input(f"JVM启动参数\n[{cfg['jvm_args']}]\n输入新参数：").strip() or cfg["jvm_args"]

                if new_min_mem:
                    try:
                        val = int(new_min_mem)
                        if val > 0:
                            cfg["min_memory_gb"] = val
                        else:
                            print("⚠️ 内存数值不能小于等于0，最小内存保持原值！")
                    except ValueError:
                        print("⚠️ 输入不是合法数字，最小内存保持原值！")

                if new_max_mem:
                    try:
                        val = int(new_max_mem)
                        if val > 0:
                            cfg["max_memory_gb"] = val
                        else:
                            print("⚠️ 内存数值不能小于等于0，最大内存保持原值！")
                    except ValueError:
                        print("⚠️ 输入不是合法数字，最大内存保持原值！")

                if new_port:
                    try:
                        val = int(new_port)
                        if 1 <= val <= 65535:
                            cfg["server_port"] = val
                        else:
                            print("⚠️ 端口范围必须1~65535，端口保持原值！")
                    except ValueError:
                        print("⚠️ 端口输入非法，端口保持原值！")

                cfg["java_path"] = new_java
                cfg["jvm_args"] = new_jvm

                if cfg["min_memory_gb"] > cfg["max_memory_gb"]:
                    print("⚠️ 警告：最小内存大于最大内存！自动修正最小内存")
                    cfg["min_memory_gb"] = max(2, cfg["max_memory_gb"] // 2)

                self.service.save_config(selected_path, cfg)
                sync_msg = []
                txt_path_check = os.path.join(selected_path, "user_jvm_args.txt")
                if os.path.exists(txt_path_check):
                    self.service.sync_jvm_args_txt(selected_path, cfg)
                    sync_msg.append("user_jvm_args.txt")
                bat_path_check = os.path.join(selected_path, "run.bat")
                if os.path.exists(bat_path_check):
                    self.service.sync_memory_bat(selected_path, cfg)
                    sync_msg.append("run.bat")
                if sync_msg:
                    print(f"✅ 配置保存成功！已同步更新：{'、'.join(sync_msg)}")
                else:
                    print("✅ 配置保存成功！当前目录无可同步启动文件")

            elif sub_opt == "4":
                break
            else:
                print("❌ 无效选项！")

    # ==================== 菜单3：刷新缓存 ====================
    async def _menu_refresh_cache(self):
        print("\n正在联网刷新Forge本地缓存，请稍候...")
        result = await self.service.refresh_cache()
        if result:
            print("✅ 缓存刷新完成！")
        else:
            print("❌ 缓存刷新失败")

    # ==================== 菜单4：服务运行控制台 ====================
    async def _menu_server_console(self):
        server_dict = self.service.get_all_servers()
        print("\n=== 选择需要启动/管理的服务 ===")
        if not server_dict:
            print("暂无已部署服务端，请先新建服务！")
            return
        server_list = list(server_dict.items())
        for idx, (name, path) in enumerate(server_list):
            print(f"{idx+1}. {name} | {path}")
        try:
            sel_input = input("\n选择服务序号（回车返回）：").strip()
            if not sel_input:
                return
            sel_idx = int(sel_input)-1
            selected_name, selected_path = server_list[sel_idx]
        except Exception:
            print("❌ 无效输入！")
            return

        cfg = self.service.load_config(selected_path)
        if cfg is None:
            print("❌ 当前服务缺少配置文件，请前往【2.管理服务配置】生成配置！")
            return

        xms = cfg["min_memory_gb"] * 1024
        xmx = cfg["max_memory_gb"] * 1024
        jvm_arg_list = [
            f"-Xms{xms}M",
            f"-Xmx{xmx}M",
            *cfg["jvm_args"].split(" ")
        ]
        java_bin = cfg["java_path"]

        watcher, cmd_terminal = self.service.create_server_watcher_terminal(selected_path, java_bin, jvm_arg_list)

        while True:
            print(f"\n==== [{selected_name}] 服务控制台 ====")
            print(f"当前状态：{watcher.status}")
            print("1. 启动服务")
            print("2. 打开指令面板（需要服务已启动）")
            print("3. 安全关闭服务")
            print("4. 强制终止进程")
            print("5. 返回主菜单")
            run_opt = input("请选择：").strip()

            if run_opt == "1":
                await watcher.start_server()
            elif run_opt == "2":
                if watcher.status != "running":
                    print("⚠️ 服务未运行，无法下发指令！")
                    continue
                cmd_terminal.reset_to_main()
                while True:
                    cmd_terminal.show_menu()
                    try:
                        user_input = input("选择指令序号：").strip()
                        if not user_input:
                            continue
                        cmd_sel = int(user_input)
                        result = await cmd_terminal.handle_selection(cmd_sel)
                        if result == "exit":
                            print("已退出指令面板")
                            break
                    except ValueError:
                        print("❌ 请输入数字序号！")
                    except ConnectionResetError:
                        print("⚠️ 与服务端连接断开，自动退出指令面板！")
                        break
            elif run_opt == "3":
                await watcher.stop_server(safe=True)
            elif run_opt == "4":
                await watcher.stop_server(safe=False)
            elif run_opt == "5":
                if watcher.status == "running":
                    confirm_exit = input("⚠️ 服务仍在运行，是否自动安全关闭并退出？(Y/N)").lower()
                    if confirm_exit == "y":
                        await watcher.stop_server(safe=True)
                break
            else:
                print("❌ 无效选项！")

    # ==================== 菜单5：樱花映射 ====================
    async def _menu_frp(self):
        while True:
            cfg = self.service.frp_load_config()
            is_running = self.service.frp_is_running

            print(f"\n========== 🌐 内网穿透（樱花映射） ==========")
            print(f"  当前状态：{'运行中' if is_running else '已停止'}")
            print(f"  frpc路径：{cfg.get('frpc_path') or '未配置'}")
            token_show = cfg['token'][:8] + '****' if cfg.get('token') else '未配置'
            print(f"  访问密钥：{token_show}")
            print(f"  隧道ID：{cfg.get('tunnel_id') or '未配置'}")
            print("=" * 42)
            print("  1. 配置 frpc 客户端路径")
            print("  2. 配置访问密钥（Token）")
            print("  3. 配置隧道ID")
            print("  4. 启动隧道")
            print("  5. 停止隧道")
            print("  0. 返回主菜单")
            print("=" * 42)

            opt = input("请选择：").strip()

            if opt == "1":
                path = input("请输入 frpc.exe 的完整路径：").strip()
                if path:
                    cfg["frpc_path"] = path
                    self.service.frp_save_config(cfg)
                    print("✅ 路径已保存")
                else:
                    print("⚠️ 路径不能为空")

            elif opt == "2":
                token = input("请输入访问密钥（Token）：").strip()
                if token:
                    cfg["token"] = token
                    self.service.frp_save_config(cfg)
                    print("✅ Token已保存")
                else:
                    print("⚠️ Token不能为空")

            elif opt == "3":
                tid = input("请输入隧道ID：").strip()
                if tid:
                    cfg["tunnel_id"] = tid
                    self.service.frp_save_config(cfg)
                    print("✅ 隧道ID已保存")
                else:
                    print("⚠️ 隧道ID不能为空")

            elif opt == "4":
                if self.service.frp_is_running:
                    print("⚠️ 隧道已经在运行了！")
                    continue
                ok = await self.service.frp_start()
                if ok:
                    print("✅ 隧道启动命令已发送，请稍候...")
                    await asyncio.sleep(3)
                else:
                    print("❌ 启动失败，请检查配置")

            elif opt == "5":
                if not self.service.frp_is_running:
                    print("⚠️ 隧道未在运行")
                    continue
                await self.service.frp_stop()

            elif opt == "0":
                break

            else:
                print("❌ 无效选项！")


# 程序入口
async def main():
    app = CLIApp()
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
