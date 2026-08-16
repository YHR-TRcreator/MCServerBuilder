# -*- coding: utf-8 -*-
"""
gui/pages/page_settings.py
全局设置页面
实时切换主题无需重启，配置写入JSON持久化
【修改】移除切换CLI按钮，GUI为独立版本，不再拉起终端
"""
import json
import subprocess
import sys
import asyncio
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout
)
from PySide6.QtCore import Qt
from qfluentwidgets import (
    CardWidget, PushButton, ComboBox, BodyLabel, InfoBar, InfoBarPosition,
    Theme, setTheme
)

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
CONFIG_FOLDER = PROJECT_ROOT / "runtime" / "config"
APP_SETTING_PATH = CONFIG_FOLDER / "app_settings.json"

DEFAULT_APP_SETTINGS = {
    "theme_mode": "AUTO",
    "log_level": "INFO",
    "auto_open_log": False
}


def load_app_settings() -> dict:
    CONFIG_FOLDER.mkdir(exist_ok=True, parents=True)
    if not APP_SETTING_PATH.exists():
        return DEFAULT_APP_SETTINGS.copy()
    try:
        with open(APP_SETTING_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = DEFAULT_APP_SETTINGS.copy()
        cfg.update(data)
        return cfg
    except Exception:
        return DEFAULT_APP_SETTINGS.copy()


def save_app_settings(cfg: dict):
    CONFIG_FOLDER.mkdir(exist_ok=True, parents=True)
    with open(APP_SETTING_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)


theme_map_index = {
    0: Theme.AUTO,
    1: Theme.LIGHT,
    2: Theme.DARK
}
theme_index_str = {
    0: "AUTO",
    1: "LIGHT",
    2: "DARK"
}


class SettingsPage(QWidget):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsPage")
        self.service = service
        self.app_cfg = load_app_settings()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24,24,24,24)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        setting_card = CardWidget()
        card_layout = QVBoxLayout(setting_card)
        card_layout.setContentsMargins(20,16,20,16)
        card_layout.setSpacing(12)

        card_layout.addWidget(BodyLabel("全局设置"))

        row_theme = QHBoxLayout()
        row_theme.addWidget(BodyLabel("主题模式："), 1)
        self.combo_theme = ComboBox()
        self.combo_theme.addItems(["跟随系统", "浅色", "深色"])
        row_theme.addWidget(self.combo_theme,4)
        card_layout.addLayout(row_theme)

        row_loglevel = QHBoxLayout()
        row_loglevel.addWidget(BodyLabel("日志输出等级："),1)
        self.combo_loglevel = ComboBox()
        self.combo_loglevel.addItems(["DEBUG","INFO","WARNING","ERROR"])
        row_loglevel.addWidget(self.combo_loglevel,4)
        card_layout.addLayout(row_loglevel)

        layout.addWidget(setting_card, stretch=0)

        tool_card = CardWidget()
        tool_layout = QVBoxLayout(tool_card)
        tool_layout.setContentsMargins(20,16,20,16)
        tool_layout.setSpacing(12)
        tool_layout.addWidget(BodyLabel("工具操作"))

        btn_layout1 = QHBoxLayout()
        # 删除切换CLI按钮，保留另外两个功能按钮
        self.btn_open_runtime = PushButton("打开Runtime目录")
        self.btn_clear_cache = PushButton("清理Forge版本缓存")
        btn_layout1.addWidget(self.btn_open_runtime)
        btn_layout1.addWidget(self.btn_clear_cache)
        btn_layout1.addStretch()
        tool_layout.addLayout(btn_layout1)

        layout.addWidget(tool_card, stretch=0)

        # 回显当前配置
        rev_map_str = {"AUTO":0, "LIGHT":1, "DARK":2}
        self.combo_theme.setCurrentIndex(rev_map_str.get(self.app_cfg.get("theme_mode","AUTO"),0))
        level_list = ["DEBUG","INFO","WARNING","ERROR"]
        lv_idx = level_list.index(self.app_cfg.get("log_level","INFO"))
        self.combo_loglevel.setCurrentIndex(lv_idx)

        self.combo_theme.currentIndexChanged.connect(self._on_theme_change)
        self.combo_loglevel.currentIndexChanged.connect(self._on_log_level_change)
        self.btn_open_runtime.clicked.connect(self._open_runtime_folder)
        self.btn_clear_cache.clicked.connect(self._clear_forge_cache)

    def _on_theme_change(self, idx:int):
        """切换主题：立刻生效 + 保存JSON，**不需要重启程序**"""
        setTheme(theme_map_index[idx])
        self.app_cfg["theme_mode"] = theme_index_str[idx]
        save_app_settings(self.app_cfg)

    def _on_log_level_change(self):
        level_list = ["DEBUG","INFO","WARNING","ERROR"]
        self.app_cfg["log_level"] = level_list[self.combo_loglevel.currentIndex()]
        save_app_settings(self.app_cfg)

    def _open_runtime_folder(self):
        target = str(PROJECT_ROOT / "runtime")
        if sys.platform == "win32":
            os.startfile(target)
        else:
            subprocess.run(["xdg-open", target])

    def _clear_forge_cache(self):
        async def task():
            try:
                ok = await self.service.refresh_cache()
                if ok:
                    InfoBar.success("完成","Forge缓存已刷新",parent=self,position=InfoBarPosition.TOP).show()
            except Exception as e:
                InfoBar.error("缓存刷新失败",str(e),parent=self,position=InfoBarPosition.TOP).show()
        asyncio.create_task(task())
