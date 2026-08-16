# -*- coding: utf-8 -*-
"""
gui/pages/page_frp.py
樱花映射 SakuraFrp 内网穿透GUI页面｜PySide6 QFluentWidgets
内存缓存模式，不使用asyncio跨线程队列
新增：隧道ID输入、自动下载frpc、注册跳转、底部免责声明
"""
from typing import Optional
import webbrowser
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QTextEdit
from PySide6.QtCore import Qt, QTimer
from qfluentwidgets import (CardWidget, PushButton, BodyLabel, LineEdit,
                            MessageBox)
from qasync import asyncSlot


class FrpPage(QWidget):
    def __init__(self, service=None, parent=None):
        super().__init__(parent)
        self.service = service
        self._last_log_len = 0
        self.setup_ui()
        # 定时轮询：状态 + 消费日志缓存
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(200)
        self.poll_timer.timeout.connect(self._poll_task)
        self.poll_timer.start()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)

        # =========配置卡片=========
        cfg_card = CardWidget()
        form_layout = QFormLayout(cfg_card)
        form_layout.setContentsMargins(16,16,16,16)
        form_layout.setSpacing(12)

        self.edit_frpc_path = LineEdit()
        self.edit_frpc_path.setPlaceholderText("frpc.exe完整路径")

        self.edit_token = LineEdit()
        self.edit_token.setPlaceholderText("樱花映射访问密钥Token")

        # 新增隧道ID输入框
        self.edit_tunnel_id = LineEdit()
        self.edit_tunnel_id.setPlaceholderText("隧道ID，网页后台隧道页面复制")

        self.label_running_state = BodyLabel("运行状态：未运行")

        form_layout.addRow("Frpc程序路径", self.edit_frpc_path)
        form_layout.addRow("访问密钥Token", self.edit_token)
        form_layout.addRow("隧道ID", self.edit_tunnel_id)
        form_layout.addRow("当前状态", self.label_running_state)

        btn_row = QHBoxLayout()
        self.btn_load_config = PushButton("读取保存配置")
        self.btn_save_config = PushButton("保存配置")
        self.btn_start = PushButton("启动穿透")
        self.btn_stop = PushButton("停止穿透")
        btn_row.addWidget(self.btn_load_config)
        btn_row.addWidget(self.btn_save_config)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        form_layout.addRow("", btn_row)

        main_layout.addWidget(cfg_card)

        # =========下载&注册辅助卡片【新增】=========
        helper_card = CardWidget()
        helper_layout = QVBoxLayout(helper_card)
        helper_layout.setContentsMargins(16,16,16,16)
        helper_layout.setSpacing(10)

        helper_layout.addWidget(BodyLabel("还未准备frpc客户端？"))
        self.btn_auto_download = PushButton("现在自动下载frpc.exe")
        helper_layout.addWidget(self.btn_auto_download)

        helper_layout.addWidget(BodyLabel("还没有SakuraFrp账号？"))
        self.btn_goto_register = PushButton("跳转官网注册账号")
        helper_layout.addWidget(self.btn_goto_register)
        main_layout.addWidget(helper_card)

        # =========日志输出卡片=========
        log_card = CardWidget()
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(16,16,16,16)
        log_layout.setSpacing(8)

        log_layout.addWidget(BodyLabel("运行日志"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(220)
        self.btn_clear_log = PushButton("清空日志")
        log_layout.addWidget(self.log_text)
        log_layout.addWidget(self.btn_clear_log)

        main_layout.addWidget(log_card)

        # 底部免责文字【新增】
        disclaimer_label = BodyLabel(
            "⚠️本程序仅提供客户端调用接入能力，不提供内网穿透服务；穿透服务由 SakuraFrp 平台提供，请遵守平台用户协议与国家网络相关法律法规。"
        )
        disclaimer_label.setWordWrap(True)
        disclaimer_label.setTextColor(Qt.GlobalColor.gray)
        main_layout.addWidget(disclaimer_label)

        # 绑定信号槽
        self.btn_load_config.clicked.connect(self._load_frp_config)
        self.btn_save_config.clicked.connect(self._save_frp_config)
        self.btn_start.clicked.connect(self._start_frp)
        self.btn_stop.clicked.connect(self._stop_frp)
        self.btn_clear_log.clicked.connect(self._on_clear_log)
        self.btn_auto_download.clicked.connect(self._on_auto_download)
        self.btn_goto_register.clicked.connect(self._on_open_register_page)

    def append_log(self, msg: str):
        """Qt主线程追加日志"""
        self.log_text.append(msg)

    def _poll_task(self):
        """Qt主线程定时器：刷新运行状态 + 读取内存缓存日志"""
        if not self.service:
            return

        # 1. 更新运行状态
        try:
            is_run = self.service.frp_is_running
            if is_run:
                self.label_running_state.setText("运行状态：🟢正在运行")
            else:
                self.label_running_state.setText("运行状态：🔴未运行")
        except Exception:
            pass

        # 2.读取内存缓存，对比上次行数，追加新增行
        try:
            new_logs = self.service.frp_get_cached_logs()
            old_len = self._last_log_len
            if len(new_logs) > old_len:
                for line in new_logs[old_len:]:
                    self.append_log(line)
                self._last_log_len = len(new_logs)
        except Exception:
            pass

    @asyncSlot()
    async def _load_frp_config(self):
        """读取本地sakura配置"""
        if not self.service:
            MessageBox("错误", "Service未初始化", self).exec()
            return
        try:
            cfg = self.service.frp_load_config()
            self.edit_frpc_path.setText(cfg.get("frpc_path", ""))
            self.edit_token.setText(cfg.get("token", ""))
            self.edit_tunnel_id.setText(cfg.get("tunnel_id", ""))
            self.append_log("✅已加载樱花映射配置")
        except Exception as e:
            MessageBox("读取配置失败", str(e), self).exec()

    @asyncSlot()
    async def _save_frp_config(self):
        """保存配置文件（包含隧道ID）"""
        if not self.service:
            return
        try:
            cfg_data = {
                "frpc_path": self.edit_frpc_path.text().strip(),
                "token": self.edit_token.text().strip(),
                "tunnel_id": self.edit_tunnel_id.text().strip()
            }
            self.service.frp_save_config(cfg_data)
            self.append_log("✅配置已写入文件")
            MessageBox("成功", "配置保存完成", self).exec()
        except Exception as e:
            MessageBox("保存配置失败", str(e), self).exec()

    @asyncSlot()
    async def _start_frp(self):
        """启动frp穿透进程，必须写await"""
        if not self.service:
            return
        frpc_path = self.edit_frpc_path.text().strip()
        token = self.edit_token.text().strip()
        tunnel_id = self.edit_tunnel_id.text().strip()
        if not frpc_path or not token or not tunnel_id:
            MessageBox("提示", "请填写frpc路径、Token、隧道ID全部参数", self).exec()
            return

        try:
            ok = await self.service.frp_start()
            if ok:
                self.append_log("🚀正在启动樱花映射...")
            else:
                self.append_log("❌启动返回False，请检查路径 / Token / 隧道ID")
        except Exception as e:
            self.append_log(f"❌启动异常: {str(e)}")
            MessageBox("启动失败", str(e), self).exec()

    @asyncSlot()
    async def _stop_frp(self):
        """停止frp进程，必须写await"""
        if not self.service:
            return
        try:
            await self.service.frp_stop()
            self.append_log("🛑已发送停止命令")
        except Exception as e:
            self.append_log(f"❌停止异常: {str(e)}")

    @asyncSlot()
    async def _on_auto_download(self):
        """自动下载frpc按钮"""
        self.append_log("🔽开始下载frpc客户端，请等待...")
        succ, msg = await self.service.frp_auto_download()
        cfg = self.service.frp_load_config()
        self.edit_frpc_path.setText(cfg.get("frpc_path",""))
        if succ:
            self.append_log(f"✅下载成功: {msg}")
        else:
            self.append_log(f"❌下载失败: {msg}")
            MessageBox("下载失败", msg, self).exec()

    def _on_open_register_page(self):
        """浏览器打开注册页面"""
        webbrowser.open("https://www.natfrp.com/")

    def _on_clear_log(self):
        """清空日志：同时清空GUI和底层缓存"""
        self.log_text.clear()
        self._last_log_len = 0
        if self.service:
            mgr = self.service._lazy_get_frp_manager()
            mgr.log_cache.clear()

    def closeEvent(self, event):
        """页面销毁停止定时器"""
        self.poll_timer.stop()
        super().closeEvent(event)
