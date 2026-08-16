# -*- coding: utf-8 -*-
import asyncio
import argparse
from common.file_utils import ensure_dir
from common.constants import SERVER_ROOT_DIR, LOG_DIR, CACHE_DIR, JAVA_STORAGE_DIR, TEMP_DOWNLOAD_DIR
from common.logger import init_logger

# 延迟导入，规避打包阶段循环导入风险
def get_cli_app():
    from ui.cli_app import CLIApp
    return CLIApp()

def get_gui_starter():
    from gui.main import start_gui
    return start_gui


def init_runtime_dir():
    """统一初始化全部运行目录，集中捕获权限异常"""
    dir_list = [
        SERVER_ROOT_DIR,
        CACHE_DIR,
        LOG_DIR,
        JAVA_STORAGE_DIR,
        TEMP_DOWNLOAD_DIR
    ]
    for d in dir_list:
        ensure_dir(d)


async def cli_entry():
    cli = get_cli_app()
    await cli.run()


if __name__ == "__main__":
    try:
        # 1、先创建目录
        init_runtime_dir()
        # 2、再初始化日志
        init_logger()

        parser = argparse.ArgumentParser()
        parser.add_argument("--headless", action="store_true", help="启用命令行模式")
        args = parser.parse_args()

        if args.headless:
            asyncio.run(cli_entry())
        else:
            gui_func = get_gui_starter()
            gui_func()

    except PermissionError as err:
        print(f"\n【权限致命错误】{err}\n")
        input("按下回车键关闭窗口...")
    except Exception as err:
        import traceback
        traceback.print_exc()
        input("程序启动失败，按下回车键关闭窗口...")

