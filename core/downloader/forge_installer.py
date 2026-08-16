# -*- coding: utf-8 -*-
"""
core/downloader/forge_installer.py
Forge服务端自动静默安装模块
特性：重复安装检测 + 断点续装 + 本地安装包缓存复用 + 自动生成&同意EULA
状态文件：服务目录下 .forge_install_status（隐藏文件，记录安装进度）
"""
import os
import asyncio
import json
from typing import List, Optional, Tuple
from common.logger import logger
from common.constants import FULL_CACHE_FILE, TEMP_DOWNLOAD_DIR
from core.downloader.base_downloader import BaseDownloader

# ========= 安装进度状态常量定义 =========
STATUS_EMPTY = "empty"              # 未开始任何操作
STATUS_DOWNLOADED = "downloaded"    # Forge安装器Jar包下载完成
STATUS_INSTALLED = "installed"      # Forge本体解压安装完成
STATUS_INITIALIZED = "initialized"  # EULA自动处理完成 = 全套安装结束


def _get_status_file_path(server_dir: str) -> str:
    """获取安装进度状态文件完整路径"""
    abs_dir = os.path.abspath(server_dir)
    return os.path.join(abs_dir, ".forge_install_status")


def read_install_progress(server_dir: str) -> str:
    """读取当前断点进度，读取失败默认返回 empty"""
    status_file = _get_status_file_path(server_dir)
    if not os.path.exists(status_file):
        return STATUS_EMPTY
    try:
        with open(status_file, "r", encoding="utf-8") as f:
            state = f.read().strip()
        valid_states = [STATUS_EMPTY, STATUS_DOWNLOADED, STATUS_INSTALLED, STATUS_INITIALIZED]
        return state if state in valid_states else STATUS_EMPTY
    except Exception as e:
        logger.warning(f"读取进度文件异常:{str(e)}")
        return STATUS_EMPTY


def write_install_progress(server_dir: str, state: str):
    """写入当前安装阶段状态"""
    abs_dir = os.path.abspath(server_dir)
    os.makedirs(abs_dir, exist_ok=True)
    status_file = _get_status_file_path(server_dir)
    try:
        with open(status_file, "w", encoding="utf-8") as f:
            f.write(state)
    except Exception as e:
        logger.warning(f"写入进度文件失败:{str(e)}")


def check_server_already_installed(server_dir: str) -> bool:
    """
    判断目标文件夹是否已经完整部署完毕
    判断标准：存在run.bat && 进度状态=initialized
    """
    abs_path = os.path.abspath(server_dir)
    run_bat = os.path.join(abs_path, "run.bat")
    progress_state = read_install_progress(server_dir)
    return os.path.exists(run_bat) and progress_state == STATUS_INITIALIZED


def load_forge_cache() -> Optional[List[dict]]:
    """加载本地Forge版本缓存"""
    if not os.path.exists(FULL_CACHE_FILE):
        logger.error("Forge缓存不存在！请先执行【手动刷新Forge版本缓存】")
        return None
    try:
        with open(FULL_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("versions", [])
    except Exception as e:
        logger.error(f"读取Forge缓存失败：{str(e)}")
        return None


def get_all_mc_versions() -> List[str]:
    """获取全部支持Forge的MC版本，新版本靠前排序"""
    cache = load_forge_cache()
    if cache is None:
        return []
    version_list = sorted([item["mcversion"] for item in cache], reverse=True)
    return version_list


def get_forge_builds_by_mcver(mc_version: str) -> List[dict]:
    """根据MC版本获取所有Forge构建列表，最新Build置顶
    build：纯数字用于排序
    version：带小数点版本号，用于下载链接
    """
    cache = load_forge_cache()
    if cache is None:
        return []
    for item in cache:
        if item["mcversion"] == mc_version:
            builds = item.get("builds", [])
            builds.sort(key=lambda x: int(x.get("build", 0)), reverse=True)
            return builds
    return []


async def install_forge_server(
    server_dir: str,
    mc_version: str,
    forge_build: str,
    java_path: str = "java",
    force_reinstall: bool = False
) -> Tuple[bool, str]:
    """
    Forge完整安装入口函数
    :param server_dir: 服务端目标文件夹
    :param mc_version: MC原版版本号,例:"1.20.1"
    :param forge_build: Forge version字段(带小数点，下载使用)
    :param java_path: java可执行文件路径
    :param force_reinstall: True=强制重装，忽略已安装检测
    :return: (执行成功布尔值, 返回提示消息)
    """
    abs_server_path = os.path.abspath(server_dir)

    # 步骤1：检测是否完整安装完成
    if check_server_already_installed(server_dir):
        if not force_reinstall:
            msg = f"目标目录【{abs_server_path}】已部署完整Forge服务端，如需安装请确认覆盖重装！"
            logger.warning(msg)
            return False, msg
        logger.info("已确认强制重装，继续执行安装流程")

    # 步骤2：读取断点进度
    current_state = read_install_progress(server_dir)
    logger.info(f"加载安装断点进度，当前阶段：{current_state}")

    installer_name = f"forge-{mc_version}-{forge_build}-installer.jar"
    jar_save_path = os.path.abspath(os.path.join(TEMP_DOWNLOAD_DIR, installer_name))
    logger.info(f"Forge安装器本地路径：{jar_save_path}")

    # 步骤3：下载阶段，仅状态为empty才执行下载
    if current_state == STATUS_EMPTY:
        skip_download = False
        if os.path.exists(jar_save_path):
            file_size = os.path.getsize(jar_save_path)
            # >1MB 判断为有效完整文件
            if file_size > 1024 * 1024:
                logger.info(f"✅本地存在完整安装包 {installer_name}，跳过下载")
                print(f"✅本地存在完整安装包 {installer_name}，跳过下载")
                skip_download = True
            else:
                logger.warning("本地存在损坏/空Jar包，进行删除并重新下载")
                os.remove(jar_save_path)

        if not skip_download:
            logger.info(f"准备下载 Forge {mc_version}-{forge_build} 安装器")
            print(f"准备下载 Forge {mc_version}-{forge_build} 安装器")
            download_success = await BaseDownloader.download_forge_installer(
                mc_ver=mc_version,
                forge_build=forge_build,
                save_path=jar_save_path
            )
            if not download_success:
                err_msg = "❌Forge安装器下载失败，终止安装流程！"
                logger.error(err_msg)
                return False, err_msg
        # 更新断点状态
        write_install_progress(server_dir, STATUS_DOWNLOADED)
        current_state = STATUS_DOWNLOADED

    # 二次校验Jar文件
    if not os.path.exists(jar_save_path):
        err_msg = f"❌安装器Jar文件丢失！路径：{jar_save_path}"
        logger.error(err_msg)
        return False, err_msg

    # 步骤4：执行Forge解压安装，低于installed状态执行
    if current_state in [STATUS_EMPTY, STATUS_DOWNLOADED]:
        os.makedirs(abs_server_path, exist_ok=True)
        install_cmd = [
            java_path,
            "-jar",
            jar_save_path,
            "--installServer",
            abs_server_path
        ]
        logger.info(f"开始执行Forge静默安装，执行命令：{' '.join(install_cmd)}")
        print(f"开始执行Forge静默安装")

        try:
            proc = await asyncio.create_subprocess_exec(
                *install_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            async def consume_log(stream, tag: str):
                while raw_line := await stream.readline():
                    text = raw_line.decode("utf-8", errors="replace").strip()
                    if text:
                        logger.info(f"[ForgeInstall|{tag}] {text}")
                        print(f"[ForgeInstall|{tag}] {text}")

            await asyncio.gather(
                consume_log(proc.stdout, "stdout"),
                consume_log(proc.stderr, "stderr")
            )

            exit_code = await proc.wait()
            if exit_code != 0:
                err_msg = f"❌Forge安装程序异常退出，进程退出码:{exit_code}"
                logger.error(err_msg)
                return False, err_msg

            write_install_progress(server_dir, STATUS_INSTALLED)
            current_state = STATUS_INSTALLED
            logger.info("🎉 Forge本体文件解压安装完成")
            print("🎉 Forge本体文件解压安装完成")
        except Exception as err:
            err_msg = f"❌执行Forge安装发生异常：{str(err)}"
            logger.error(err_msg)
            return False, err_msg

    # 步骤5：EULA初始化流程，低于initialized状态执行
    if current_state in [STATUS_EMPTY, STATUS_DOWNLOADED, STATUS_INSTALLED]:
        run_bat_path = os.path.join(abs_server_path, "run.bat")
        eula_path = os.path.join(abs_server_path, "eula.txt")

        # 基础文件自检
        if not os.path.exists(run_bat_path):
            err_msg = "❌自检失败，目录缺少run.bat，Forge安装不完整！"
            logger.error(err_msg)
            return False, err_msg
        logger.info("✅自检通过：run.bat 文件存在")
        print("✅自检通过：run.bat 文件存在")

        # 无eula则后台启动run.bat生成配置文件
        if not os.path.exists(eula_path):
            logger.info("未检测eula.txt，后台启动run.bat生成配置文件，30秒超时强制终止进程")
            print("未检测eula.txt，后台生成eula协议文件...")
            try:
                proc_init = await asyncio.create_subprocess_shell(
                    run_bat_path,
                    cwd=abs_server_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    creationflags=0x08000000  # Windows隐藏控制台窗口
                )
                try:
                    await asyncio.wait_for(proc_init.wait(), timeout=30)
                except asyncio.TimeoutError:
                    logger.info("30秒超时，自动终止初始化进程")
                    proc_init.terminate()
                    await proc_init.wait()
                    if proc_init.returncode is None:
                        proc_init.kill()
                await asyncio.sleep(1.5)
            except Exception as e:
                logger.warning(f"执行run.bat生成eula过程警告：{str(e)}")

        # 自动修改eula协议
        if os.path.exists(eula_path):
            logger.info("开始自动修改 eula.txt，同意Minecraft EULA协议")
            print("开始自动修改 eula.txt，同意Minecraft EULA协议")
            try:
                with open(eula_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                content = content.replace("eula=false", "eula=true")
                with open(eula_path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(content)
                logger.info("✅ eula.txt 修改完成 eula=true")
                print("✅ eula.txt 修改完成 eula=true")
            except Exception as e:
                err_msg = f"❌修改eula.txt失败：{str(e)}"
                logger.error(err_msg)
                return False, err_msg
        else:
            err_msg = "❌多次尝试仍然无法生成eula.txt，服务端无法启动！"
            logger.error(err_msg)
            return False, err_msg

        # 全部任务完成，写入最终状态
        write_install_progress(server_dir, STATUS_INITIALIZED)
        current_state = STATUS_INITIALIZED

    # 全部流程执行完毕
    success_msg = f"✅全套部署完成！服务端路径：{abs_server_path} | 已自动同意EULA协议"
    logger.info(success_msg)

    # =========【可选】开启下面代码会自动删除临时安装包，注释则永久缓存安装包，重复安装不用下载 =========
    # try:
    #     if os.path.exists(jar_save_path):
    #         os.remove(jar_save_path)
    #         logger.info(f"✅清理临时安装包 {installer_name}")
    # except Exception as e:
    #     logger.warning(f"临时Jar清理失败: {str(e)}")

    return True, success_msg