# -*- coding: utf-8 -*-
"""
GUI主入口
运行命令：python gui/main.py
"""
import sys
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from qfluentwidgets import FluentWindow, NavigationItemPosition, setTheme, Theme, FluentIcon
from qasync import QEventLoop

from service.mc_server_service import MCServerService
from gui.pages.page_deploy import DeployPage
from gui.pages.page_instance import InstancePage
from gui.pages.page_optimizer import OptimizerPage
from gui.pages.page_frp import FrpPage
from gui.pages.page_settings import SettingsPage
from gui.pages.page_settings import load_app_settings


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.service = MCServerService()

        # 读取全局设置，应用主题
        self.app_cfg = load_app_settings()
        self._apply_theme_from_config()

        # 页面实例化
        self.page_deploy = DeployPage(service=self.service)
        self.page_deploy.setObjectName("DeployInterface")

        self.page_instance = InstancePage(service=self.service)
        self.page_instance.setObjectName("InstanceInterface")

        self.page_optimizer = OptimizerPage()
        self.page_optimizer.setObjectName("OptimizerInterface")
        self.page_optimizer.service = self.service

        self.page_frp = FrpPage()
        self.page_frp.setObjectName("FrpInterface")
        self.page_frp.service = self.service

        # 修复：传入service对象
        self.page_settings = SettingsPage(service=self.service)
        self.page_settings.setObjectName("SettingsInterface")

        self.setup_navigation()
        self.setWindowTitle("MC服务端一键搭建工具")
        self.resize(1100,720)

    def _apply_theme_from_config(self):
        """从json配置加载并设置主题"""
        mode = self.app_cfg.get("theme_mode", "AUTO")
        theme_map = {
            "LIGHT": Theme.LIGHT,
            "DARK": Theme.DARK,
            "AUTO": Theme.AUTO
        }
        setTheme(theme_map.get(mode, Theme.AUTO))

    def setup_navigation(self):
        self.addSubInterface(self.page_deploy, FluentIcon.FOLDER, "服务端部署", position=NavigationItemPosition.TOP)
        self.addSubInterface(self.page_instance, FluentIcon.LIBRARY, "实例管理", position=NavigationItemPosition.TOP)
        self.addSubInterface(self.page_optimizer, FluentIcon.SPEED_HIGH, "硬件优化", position=NavigationItemPosition.TOP)
        self.addSubInterface(self.page_frp, FluentIcon.GLOBE, "樱花映射", position=NavigationItemPosition.TOP)
        self.addSubInterface(self.page_settings, FluentIcon.SETTING, "设置", position=NavigationItemPosition.BOTTOM)


def start_gui():
    """对外导出的GUI启动函数，供根目录main.py调用"""
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    win = MainWindow()
    win.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    start_gui()
